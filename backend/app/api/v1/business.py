"""
Business endpoints — Phase 13.
Discount codes, loyalty program, and scheduling.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.user import User
from app.services.business_service import DiscountService, LoyaltyService, SchedulingService

router = APIRouter(tags=["Business"])


# ── Schemas ──────────────────────────────────────────────────────────────────
class DiscountValidateRequest(BaseModel):
    code: str = Field(..., max_length=50)
    subtotal: Decimal
    has_cake: bool = False
    is_first_order: bool = False


class DiscountValidateResponse(BaseModel):
    valid: bool
    message: str
    discount_amount: Decimal


class DiscountCreateRequest(BaseModel):
    code: str = Field(..., max_length=50)
    description: str | None = None
    discount_type: str = "percentage"
    discount_value: Decimal
    min_order_amount: Decimal | None = None
    max_discount_amount: Decimal | None = None
    max_uses: int | None = None
    max_uses_per_user: int = 1
    applies_to_cakes_only: bool = False
    first_order_only: bool = False
    starts_at: datetime | None = None
    expires_at: datetime | None = None


class LoyaltyBalanceResponse(BaseModel):
    points_balance: int
    total_earned: int
    total_redeemed: int
    tier: str
    next_tier: str | None
    points_to_next_tier: int | None


class RedeemPointsRequest(BaseModel):
    points: int = Field(..., gt=0)


class SlotAvailabilityResponse(BaseModel):
    time_slot: str
    available: bool
    remaining: int
    cake_remaining: int


# ── Discount Endpoints ───────────────────────────────────────────────────────
@router.post("/discounts/validate", response_model=DiscountValidateResponse)
async def validate_discount(
    data: DiscountValidateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Validate a discount code and return the discount amount."""
    service = DiscountService(db)
    valid, message, amount = await service.validate_discount(
        code=data.code,
        subtotal=data.subtotal,
        has_cake=data.has_cake,
        is_first_order=data.is_first_order,
    )
    return DiscountValidateResponse(valid=valid, message=message, discount_amount=amount)


@router.post("/admin/discounts")
async def create_discount(
    data: DiscountCreateRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Create a new discount code."""
    service = DiscountService(db)
    discount = await service.create_discount(**data.model_dump())
    return {"message": f"Discount code '{discount.code}' created", "id": str(discount.id)}


@router.get("/admin/discounts")
async def list_discounts(
    active_only: bool = Query(True),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] List all discount codes."""
    service = DiscountService(db)
    discounts = await service.list_discounts(active_only=active_only)
    return [
        {
            "id": str(d.id),
            "code": d.code,
            "description": d.description,
            "type": d.discount_type.value,
            "value": str(d.discount_value),
            "times_used": d.times_used,
            "max_uses": d.max_uses,
            "is_active": d.is_active,
            "expires_at": d.expires_at.isoformat() if d.expires_at else None,
        }
        for d in discounts
    ]


# ── Loyalty Endpoints ────────────────────────────────────────────────────────
@router.get("/loyalty/balance", response_model=LoyaltyBalanceResponse)
async def get_loyalty_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get your loyalty points balance and tier."""
    service = LoyaltyService(db)
    return await service.get_balance(current_user.id)


@router.post("/loyalty/redeem")
async def redeem_loyalty_points(
    data: RedeemPointsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Redeem loyalty points for a discount."""
    service = LoyaltyService(db)
    discount = await service.redeem_points(current_user.id, data.points)
    if discount <= 0:
        raise HTTPException(status_code=400, detail="Insufficient points")
    return {"discount_amount": str(discount), "message": f"Redeemed {data.points} points for ${discount}"}


# ── Scheduling Endpoints ────────────────────────────────────────────────────
@router.get("/schedule/available", response_model=list[SlotAvailabilityResponse])
async def get_available_slots(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
):
    """Get available pickup time slots for a date."""
    try:
        dt = datetime.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    service = SchedulingService(db)
    return await service.get_available_slots(dt)
