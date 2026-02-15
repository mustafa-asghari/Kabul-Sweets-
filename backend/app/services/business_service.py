"""
Business service — Phase 13.
Discount validation, loyalty management, and scheduling capacity.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.business import (
    CakeDeposit,
    DiscountCode,
    DiscountType,
    LoyaltyAccount,
    PointsLedger,
    ScheduleCapacity,
)

logger = get_logger("business_service")


class DiscountService:
    """Handles discount code validation and application."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_discount(
        self,
        code: str,
        subtotal: Decimal,
        user_id: uuid.UUID | None = None,
        has_cake: bool = False,
        is_first_order: bool = False,
    ) -> tuple[bool, str, Decimal]:
        """
        Validate a discount code and return (valid, message, discount_amount).
        """
        result = await self.db.execute(
            select(DiscountCode).where(DiscountCode.code == code.upper().strip())
        )
        discount = result.scalar_one_or_none()

        if not discount:
            return False, "Invalid discount code", Decimal("0.00")

        valid, msg = discount.is_valid()
        if not valid:
            return False, msg, Decimal("0.00")

        if discount.applies_to_cakes_only and not has_cake:
            return False, "This discount applies to cake orders only", Decimal("0.00")

        if discount.first_order_only and not is_first_order:
            return False, "This discount is for first orders only", Decimal("0.00")

        amount = discount.calculate_discount(subtotal)
        if amount <= 0:
            min_amount = discount.min_order_amount or 0
            return False, f"Minimum order amount: ${min_amount}", Decimal("0.00")

        return True, f"Discount applied: ${amount}", amount

    async def apply_discount(self, code: str) -> bool:
        """Increment usage count for a discount code."""
        result = await self.db.execute(
            select(DiscountCode).where(DiscountCode.code == code.upper().strip())
        )
        discount = result.scalar_one_or_none()
        if discount:
            discount.times_used += 1
            return True
        return False

    async def create_discount(self, **kwargs) -> DiscountCode:
        """Create a new discount code."""
        if "code" in kwargs:
            kwargs["code"] = kwargs["code"].upper().strip()
        discount = DiscountCode(**kwargs)
        self.db.add(discount)
        await self.db.flush()
        await self.db.refresh(discount)
        logger.info("Discount created: %s", discount.code)
        return discount

    async def list_discounts(self, active_only: bool = True) -> list[DiscountCode]:
        """List discount codes."""
        query = select(DiscountCode).order_by(DiscountCode.created_at.desc())
        if active_only:
            query = query.where(DiscountCode.is_active == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())


class LoyaltyService:
    """Handles loyalty points and rewards."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_account(self, user_id: uuid.UUID) -> LoyaltyAccount:
        """Get or create a loyalty account for a user."""
        result = await self.db.execute(
            select(LoyaltyAccount).where(LoyaltyAccount.user_id == user_id)
        )
        account = result.scalar_one_or_none()

        if not account:
            account = LoyaltyAccount(user_id=user_id)
            self.db.add(account)
            await self.db.flush()
            await self.db.refresh(account)
            logger.info("Loyalty account created for user %s", user_id)

        return account

    async def earn_points(
        self,
        user_id: uuid.UUID,
        order_total: Decimal,
        order_id: uuid.UUID | None = None,
    ) -> int:
        """Award loyalty points for a purchase."""
        account = await self.get_or_create_account(user_id)
        points = account.add_points(order_total)

        # Record in ledger
        ledger = PointsLedger(
            loyalty_account_id=account.id,
            order_id=order_id,
            points_change=points,
            reason="purchase",
            balance_after=account.points_balance,
        )
        self.db.add(ledger)
        await self.db.flush()

        logger.info("User %s earned %d points (total: %d)", user_id, points, account.points_balance)
        return points

    async def redeem_points(
        self,
        user_id: uuid.UUID,
        points: int,
        order_id: uuid.UUID | None = None,
    ) -> Decimal:
        """Redeem loyalty points for a discount."""
        account = await self.get_or_create_account(user_id)
        discount = account.redeem_points(points)

        ledger = PointsLedger(
            loyalty_account_id=account.id,
            order_id=order_id,
            points_change=-points,
            reason="redemption",
            balance_after=account.points_balance,
        )
        self.db.add(ledger)
        await self.db.flush()

        logger.info("User %s redeemed %d points for $%s discount", user_id, points, discount)
        return discount

    async def get_balance(self, user_id: uuid.UUID) -> dict:
        """Get a user's loyalty summary."""
        account = await self.get_or_create_account(user_id)
        return {
            "points_balance": account.points_balance,
            "total_earned": account.total_points_earned,
            "total_redeemed": account.total_points_redeemed,
            "tier": account.tier,
            "next_tier": self._get_next_tier(account),
            "points_to_next_tier": self._points_to_next_tier(account),
        }

    def _get_next_tier(self, account: LoyaltyAccount) -> str | None:
        tiers = list(LoyaltyAccount.TIER_THRESHOLDS.keys())
        idx = tiers.index(account.tier) if account.tier in tiers else 0
        return tiers[idx + 1] if idx + 1 < len(tiers) else None

    def _points_to_next_tier(self, account: LoyaltyAccount) -> int | None:
        next_tier = self._get_next_tier(account)
        if not next_tier:
            return None
        return LoyaltyAccount.TIER_THRESHOLDS[next_tier] - account.total_points_earned


class SchedulingService:
    """Manages order scheduling capacity."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_availability(
        self,
        date: datetime,
        time_slot: str,
        is_cake: bool = False,
    ) -> tuple[bool, str]:
        """Check if a time slot has capacity."""
        result = await self.db.execute(
            select(ScheduleCapacity).where(
                ScheduleCapacity.date == date,
                ScheduleCapacity.time_slot == time_slot,
            )
        )
        capacity = result.scalar_one_or_none()

        if not capacity:
            # No capacity record = available (create default)
            return True, "Available"

        if not capacity.has_capacity(is_cake):
            if capacity.is_blocked:
                return False, "This time slot is not available"
            return False, "This time slot is fully booked"

        return True, f"{capacity.max_orders - capacity.current_orders} slots remaining"

    async def reserve_slot(
        self,
        date: datetime,
        time_slot: str,
        is_cake: bool = False,
    ) -> bool:
        """Reserve a slot for an order."""
        result = await self.db.execute(
            select(ScheduleCapacity).where(
                ScheduleCapacity.date == date,
                ScheduleCapacity.time_slot == time_slot,
            )
        )
        capacity = result.scalar_one_or_none()

        if not capacity:
            capacity = ScheduleCapacity(
                date=date,
                time_slot=time_slot,
            )
            self.db.add(capacity)

        if not capacity.has_capacity(is_cake):
            return False

        capacity.current_orders += 1
        if is_cake:
            capacity.current_cake_orders += 1

        await self.db.flush()
        return True

    async def get_available_slots(self, date: datetime) -> list[dict]:
        """Get all available time slots for a date."""
        DEFAULT_SLOTS = [
            "09:00-10:00", "10:00-11:00", "11:00-12:00",
            "12:00-13:00", "13:00-14:00", "14:00-15:00",
            "15:00-16:00", "16:00-17:00",
        ]

        result = await self.db.execute(
            select(ScheduleCapacity).where(ScheduleCapacity.date == date)
        )
        existing = {cap.time_slot: cap for cap in result.scalars().all()}

        slots = []
        for slot in DEFAULT_SLOTS:
            if slot in existing:
                cap = existing[slot]
                slots.append({
                    "time_slot": slot,
                    "available": cap.has_capacity(),
                    "remaining": max(0, cap.max_orders - cap.current_orders),
                    "cake_remaining": max(0, cap.max_cake_orders - cap.current_cake_orders),
                })
            else:
                slots.append({
                    "time_slot": slot,
                    "available": True,
                    "remaining": 10,
                    "cake_remaining": 5,
                })

        return slots
