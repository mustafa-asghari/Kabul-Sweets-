"""
Product management endpoints.
Public: browse products. Admin: full CRUD + inventory management.
"""

import asyncio
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, log_admin_action, require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
    StockAdjustmentRequest,
    StockAdjustmentResponse,
    VariantCreate,
    VariantResponse,
    VariantUpdate,
)
from app.schemas.user import MessageResponse
from app.services.cache_service import CacheService, CACHE_TTL
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


async def _sanitize_negative_stock(product, db: AsyncSession) -> None:
    """
    Guard API responses from legacy negative stock values.
    This keeps response validation stable and heals bad data in place.
    """
    if not product:
        return

    changed = False
    for variant in getattr(product, "variants", []) or []:
        if variant.stock_quantity < 0:
            variant.stock_quantity = 0
            changed = True
        next_in_stock = variant.stock_quantity > 0
        if variant.is_in_stock != next_in_stock:
            variant.is_in_stock = next_in_stock
            changed = True

    if changed:
        await db.flush()


# ── Public Endpoints ─────────────────────────────────────────────────────────
@router.get("/", response_model=list[ProductListResponse])
async def list_products(
    category: str | None = None,
    is_featured: bool | None = None,
    is_cake: bool | None = None,
    search: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Browse products (public). Only shows active products."""
    cache_key = CacheService._make_key(
        "product_list",
        category=category,
        is_featured=is_featured,
        is_cake=is_cake,
        search=search,
        skip=skip,
        limit=limit,
    )
    cached = await CacheService.get(cache_key)
    if cached is not None:
        return cached

    service = ProductService(db)
    products = await service.list_products(
        category=category,
        is_active=True,
        is_featured=is_featured,
        is_cake=is_cake,
        search=search,
        skip=skip,
        limit=limit,
    )
    for product in products:
        await _sanitize_negative_stock(product, db)

    serialized = [ProductListResponse.model_validate(p).model_dump(mode="json") for p in products]
    await CacheService.set(cache_key, serialized, ttl=CACHE_TTL["product_list"])
    return serialized


@router.get("/count")
async def count_products(db: AsyncSession = Depends(get_db)):
    """Get active product count."""
    service = ProductService(db)
    return {"total": await service.count_products(is_active=True)}


@router.get("/slug/{slug}", response_model=ProductResponse)
async def get_product_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a product by slug (public)."""
    service = ProductService(db)
    product = await service.get_product_by_slug(slug)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")
    await _sanitize_negative_stock(product, db)
    return product


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a product by ID (public)."""
    service = ProductService(db)
    product = await service.get_product(product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")
    await _sanitize_negative_stock(product, db)
    return product


@router.get("/low-stock/all", response_model=list[VariantResponse])
async def get_low_stock(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get all variants with low stock."""
    service = ProductService(db)
    return await service.get_low_stock_products()


async def _invalidate_and_notify(product_id: str | None = None):
    """
    1. Bust the backend Redis product cache.
    2. Tell the storefront Next.js to drop its 'products' cache tag.
    Both are fire-and-forget.
    """
    await CacheService.invalidate_product(product_id)

    storefront_url = os.getenv("STOREFRONT_URL", "").rstrip("/")
    secret = os.getenv("REVALIDATION_SECRET", "")
    if storefront_url:
        try:
            import httpx
            headers = {"Content-Type": "application/json"}
            if secret:
                headers["Authorization"] = f"Bearer {secret}"
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{storefront_url}/api/revalidate",
                    json={"tags": ["products"]},
                    headers=headers,
                )
        except Exception:
            pass  # Non-critical — storefront will revalidate on next TTL expiry


# ── Admin CRUD ───────────────────────────────────────────────────────────────
@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    data: ProductCreate,
    admin: User = Depends(log_admin_action),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Create a new product with optional variants."""
    service = ProductService(db)
    product = await service.create_product(data)
    asyncio.create_task(_invalidate_and_notify(str(product.id)))
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    admin: User = Depends(log_admin_action),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Update a product."""
    service = ProductService(db)
    product = await service.update_product(product_id, data)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    asyncio.create_task(_invalidate_and_notify(str(product_id)))
    return product


@router.delete("/{product_id}", response_model=MessageResponse)
async def delete_product(
    product_id: uuid.UUID,
    admin: User = Depends(log_admin_action),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Delete a product."""
    service = ProductService(db)
    if not await service.delete_product(product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    asyncio.create_task(_invalidate_and_notify(str(product_id)))
    return MessageResponse(message="Product deleted")


# ── Admin: All products (including inactive) ─────────────────────────────────
@router.get("/admin/all", response_model=list[ProductListResponse])
async def list_all_products_admin(
    category: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] List all products including inactive ones."""
    service = ProductService(db)
    products = await service.list_products(
        category=category,
        is_active=is_active,
        search=search,
        skip=skip,
        limit=limit,
    )
    for product in products:
        await _sanitize_negative_stock(product, db)
    return products


# ── Variant Management ──────────────────────────────────────────────────────
@router.post(
    "/{product_id}/variants",
    response_model=VariantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_variant(
    product_id: uuid.UUID,
    data: VariantCreate,
    admin: User = Depends(log_admin_action),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Add a variant to a product."""
    service = ProductService(db)
    variant = await service.add_variant(product_id, data)
    if not variant:
        raise HTTPException(status_code=404, detail="Product not found")
    return variant


@router.patch("/variants/{variant_id}", response_model=VariantResponse)
async def update_variant(
    variant_id: uuid.UUID,
    data: VariantUpdate,
    admin: User = Depends(log_admin_action),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Update a variant."""
    service = ProductService(db)
    variant = await service.update_variant(variant_id, data)
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    return variant


@router.delete("/variants/{variant_id}", response_model=MessageResponse)
async def delete_variant(
    variant_id: uuid.UUID,
    admin: User = Depends(log_admin_action),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Delete a variant."""
    service = ProductService(db)
    if not await service.delete_variant(variant_id):
        raise HTTPException(status_code=404, detail="Variant not found")
    return MessageResponse(message="Variant deleted")


# ── Inventory Management ────────────────────────────────────────────────────
@router.post(
    "/{product_id}/stock",
    response_model=StockAdjustmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def adjust_stock(
    product_id: uuid.UUID,
    data: StockAdjustmentRequest,
    admin: User = Depends(log_admin_action),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Adjust stock for a product variant."""
    service = ProductService(db)
    adjustment = await service.adjust_stock(data, product_id, adjusted_by=admin.id)
    if not adjustment:
        raise HTTPException(status_code=404, detail="Variant not found")
    return adjustment
