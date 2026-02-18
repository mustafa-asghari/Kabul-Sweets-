"""
Product service — business logic for product and inventory management.
"""

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.product import Product, ProductCategory, ProductVariant, StockAdjustment
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    StockAdjustmentRequest,
    VariantCreate,
    VariantUpdate,
)

logger = get_logger("product_service")


def _slugify(text: str) -> str:
    """Generate a URL-safe slug from text."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug


class ProductService:
    """Handles product CRUD and inventory operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _normalize_variant_stock(product: Product | None) -> Product | None:
        """
        Heal negative stock values to zero so API responses remain valid.
        This also keeps is_in_stock aligned with stock_quantity.
        """
        if not product:
            return product

        for variant in product.variants or []:
            if variant.stock_quantity < 0:
                logger.warning(
                    "Normalizing negative stock for variant %s (%s): %s -> 0",
                    variant.id,
                    variant.name,
                    variant.stock_quantity,
                )
                variant.stock_quantity = 0
            variant.is_in_stock = variant.stock_quantity > 0

        return product

    # ── Product CRUD ─────────────────────────────────────────────────────
    async def create_product(self, data: ProductCreate) -> Product:
        """Create a product with optional variants."""
        # Generate slug if not provided
        slug = data.slug or _slugify(data.name)

        # Ensure slug is unique
        existing = await self.db.execute(select(Product).where(Product.slug == slug))
        if existing.scalar_one_or_none():
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        product = Product(
            name=data.name,
            slug=slug,
            description=data.description,
            short_description=data.short_description,
            category=ProductCategory(data.category),
            base_price=data.base_price,
            images=data.images,
            thumbnail=data.thumbnail,
            tags=data.tags,
            is_active=data.is_active,
            is_featured=data.is_featured,
            is_cake=data.is_cake,
            max_per_order=data.max_per_order,
            sort_order=data.sort_order,
        )
        self.db.add(product)
        await self.db.flush()

        # Create variants
        if data.variants:
            for v in data.variants:
                variant = ProductVariant(
                    product_id=product.id,
                    name=v.name,
                    sku=v.sku,
                    price=v.price,
                    stock_quantity=v.stock_quantity,
                    low_stock_threshold=v.low_stock_threshold,
                    serves=v.serves,
                    dimensions=v.dimensions,
                    is_active=v.is_active,
                    sort_order=v.sort_order,
                )
                self.db.add(variant)

        await self.db.flush()
        await self.db.refresh(product)
        logger.info("Product created: %s (%s)", product.name, product.slug)
        return product

    async def get_product(self, product_id: uuid.UUID) -> Product | None:
        """Get a product by ID with variants."""
        result = await self.db.execute(
            select(Product)
            .options(selectinload(Product.variants))
            .where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        return self._normalize_variant_stock(product)

    async def get_product_by_slug(self, slug: str) -> Product | None:
        """Get a product by slug."""
        result = await self.db.execute(
            select(Product)
            .options(selectinload(Product.variants))
            .where(Product.slug == slug)
        )
        product = result.scalar_one_or_none()
        return self._normalize_variant_stock(product)

    async def list_products(
        self,
        category: str | None = None,
        is_active: bool | None = True,
        is_featured: bool | None = None,
        is_cake: bool | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Product]:
        """List products with filters."""
        query = (
            select(Product)
            .options(selectinload(Product.variants))
            .offset(skip)
            .limit(limit)
            .order_by(Product.sort_order, Product.created_at.desc())
        )

        if category:
            query = query.where(Product.category == category)
        if is_active is not None:
            query = query.where(Product.is_active == is_active)
        if is_featured is not None:
            query = query.where(Product.is_featured == is_featured)
        if is_cake is not None:
            query = query.where(Product.is_cake == is_cake)
        if search:
            query = query.where(Product.name.ilike(f"%{search}%"))

        result = await self.db.execute(query)
        products = list(result.scalars().all())
        for product in products:
            self._normalize_variant_stock(product)
        return products

    async def count_products(self, is_active: bool | None = None) -> int:
        """Count products."""
        query = select(func.count(Product.id))
        if is_active is not None:
            query = query.where(Product.is_active == is_active)
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def update_product(self, product_id: uuid.UUID, data: ProductUpdate) -> Product | None:
        """Update a product."""
        product = await self.get_product(product_id)
        if not product:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            if field == "category" and value is not None:
                setattr(product, field, ProductCategory(value))
            else:
                setattr(product, field, value)

        await self.db.flush()
        await self.db.refresh(product)
        logger.info("Product updated: %s", product.name)
        return product

    async def delete_product(self, product_id: uuid.UUID) -> bool:
        """Delete a product (hard delete)."""
        product = await self.get_product(product_id)
        if not product:
            return False
        await self.db.delete(product)
        logger.info("Product deleted: %s", product.name)
        return True

    # ── Variant Management ───────────────────────────────────────────────
    async def add_variant(self, product_id: uuid.UUID, data: VariantCreate) -> ProductVariant | None:
        """Add a variant to a product."""
        product = await self.get_product(product_id)
        if not product:
            return None

        variant = ProductVariant(
            product_id=product_id,
            name=data.name,
            sku=data.sku,
            price=data.price,
            stock_quantity=data.stock_quantity,
            low_stock_threshold=data.low_stock_threshold,
            serves=data.serves,
            dimensions=data.dimensions,
            is_active=data.is_active,
            sort_order=data.sort_order,
        )
        self.db.add(variant)
        await self.db.flush()
        await self.db.refresh(variant)
        logger.info("Variant added to %s: %s", product.name, variant.name)
        return variant

    async def update_variant(self, variant_id: uuid.UUID, data: VariantUpdate) -> ProductVariant | None:
        """Update a variant."""
        result = await self.db.execute(
            select(ProductVariant).where(ProductVariant.id == variant_id)
        )
        variant = result.scalar_one_or_none()
        if not variant:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(variant, field, value)

        await self.db.flush()
        await self.db.refresh(variant)
        return variant

    async def delete_variant(self, variant_id: uuid.UUID) -> bool:
        """Delete a variant."""
        result = await self.db.execute(
            select(ProductVariant).where(ProductVariant.id == variant_id)
        )
        variant = result.scalar_one_or_none()
        if not variant:
            return False
        await self.db.delete(variant)
        return True

    # ── Inventory Management ─────────────────────────────────────────────
    async def adjust_stock(
        self,
        data: StockAdjustmentRequest,
        product_id: uuid.UUID,
        adjusted_by: uuid.UUID | None = None,
    ) -> StockAdjustment | None:
        """
        Adjust stock for a variant with full audit trail.
        Positive = add stock, Negative = remove stock.
        """
        result = await self.db.execute(
            select(ProductVariant).where(ProductVariant.id == data.variant_id)
        )
        variant = result.scalar_one_or_none()
        if not variant:
            return None

        previous_qty = variant.stock_quantity
        new_qty = max(0, previous_qty + data.quantity_change)

        # Update variant stock
        variant.stock_quantity = new_qty
        variant.is_in_stock = new_qty > 0

        # Create audit record
        adjustment = StockAdjustment(
            product_id=product_id,
            variant_id=data.variant_id,
            adjusted_by=adjusted_by,
            quantity_change=data.quantity_change,
            previous_quantity=previous_qty,
            new_quantity=new_qty,
            reason=data.reason,
            notes=data.notes,
        )
        self.db.add(adjustment)
        await self.db.flush()
        await self.db.refresh(adjustment)

        logger.info(
            "Stock adjusted for variant %s: %d → %d (%s)",
            variant.name, previous_qty, new_qty, data.reason,
        )
        return adjustment

    async def get_low_stock_products(self) -> list[ProductVariant]:
        """Get variants where stock is below threshold."""
        result = await self.db.execute(
            select(ProductVariant).where(
                ProductVariant.stock_quantity <= ProductVariant.low_stock_threshold,
                ProductVariant.is_active == True,
            )
        )
        return list(result.scalars().all())
