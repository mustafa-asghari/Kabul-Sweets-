"""
Cart API endpoints — shopping cart CRUD and abandoned cart recovery stats.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.user import User
from app.services.cart_service import CartService

router = APIRouter(prefix="/cart", tags=["Cart"])


# ── Schemas ──────────────────────────────────────────────────────────────────
class CartItemAdd(BaseModel):
    product_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    quantity: int = Field(1, ge=1, le=50)


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=0, le=50)


# ── Customer Endpoints ──────────────────────────────────────────────────────

@router.get("/")
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's active cart."""
    service = CartService(db)
    return await service.get_cart(current_user.id)


@router.post("/items", status_code=status.HTTP_201_CREATED)
async def add_item(
    data: CartItemAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add an item to the cart. Updates quantity if already exists."""
    service = CartService(db)
    return await service.add_item(
        customer_id=current_user.id,
        product_id=data.product_id,
        variant_id=data.variant_id,
        quantity=data.quantity,
    )


@router.put("/items/{item_id}")
async def update_item(
    item_id: uuid.UUID,
    data: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update cart item quantity. Set to 0 to remove."""
    service = CartService(db)
    result = await service.update_item(current_user.id, item_id, data.quantity)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/items/{item_id}")
async def remove_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an item from the cart."""
    service = CartService(db)
    result = await service.remove_item(current_user.id, item_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/")
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear all items from the cart."""
    service = CartService(db)
    return await service.clear_cart(current_user.id)


# ── Admin Endpoints ─────────────────────────────────────────────────────────

@router.get(
    "/recovery/stats",
    dependencies=[Depends(require_admin)],
)
async def get_recovery_stats(
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get cart recovery statistics."""
    service = CartService(db)
    return await service.get_recovery_stats()


@router.get(
    "/abandoned",
    dependencies=[Depends(require_admin)],
)
async def get_abandoned_carts(
    min_age_hours: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """[Admin] List currently abandoned carts."""
    service = CartService(db)
    return await service.find_abandoned_carts(min_age_hours)
