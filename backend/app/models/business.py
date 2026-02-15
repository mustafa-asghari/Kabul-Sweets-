"""
Business models — Phase 13.
Discount codes, loyalty system, scheduling capacity, and deposit payments.
"""

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── Discount Codes ───────────────────────────────────────────────────────────
class DiscountType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"


class DiscountCode(Base):
    """Promotional discount codes."""

    __tablename__ = "discount_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType), nullable=False
    )
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Limits
    min_order_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    max_discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    times_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_uses_per_user: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Validity
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Targeting
    applies_to_cakes_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    first_order_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<DiscountCode {self.code} ({self.discount_type.value}: {self.discount_value})>"

    def is_valid(self) -> tuple[bool, str]:
        """Check if discount code is currently valid."""
        now = datetime.now(timezone.utc)
        if not self.is_active:
            return False, "Discount code is inactive"
        if self.starts_at and now < self.starts_at:
            return False, "Discount code is not yet active"
        if self.expires_at and now > self.expires_at:
            return False, "Discount code has expired"
        if self.max_uses and self.times_used >= self.max_uses:
            return False, "Discount code usage limit reached"
        return True, ""

    def calculate_discount(self, subtotal: Decimal) -> Decimal:
        """Calculate the discount amount for a given subtotal."""
        if self.min_order_amount and subtotal < self.min_order_amount:
            return Decimal("0.00")

        if self.discount_type == DiscountType.PERCENTAGE:
            discount = (subtotal * self.discount_value / 100).quantize(Decimal("0.01"))
        else:
            discount = self.discount_value

        if self.max_discount_amount:
            discount = min(discount, self.max_discount_amount)

        return min(discount, subtotal)  # Never discount more than the total


# ── Loyalty System ───────────────────────────────────────────────────────────
class LoyaltyAccount(Base):
    """Customer loyalty account."""

    __tablename__ = "loyalty_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True,
    )
    points_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_points_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_points_redeemed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tier: Mapped[str] = mapped_column(String(20), default="bronze", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Points earn rate: $1 = 1 point
    # Redemption: 100 points = $5 discount
    POINTS_PER_DOLLAR = 1
    REDEMPTION_RATE = Decimal("0.05")  # $0.05 per point

    TIER_THRESHOLDS = {
        "bronze": 0,
        "silver": 500,
        "gold": 2000,
        "platinum": 5000,
    }

    def add_points(self, order_total: Decimal) -> int:
        """Award points for an order and update tier."""
        points = int(order_total) * self.POINTS_PER_DOLLAR
        self.points_balance += points
        self.total_points_earned += points
        self._update_tier()
        return points

    def redeem_points(self, points: int) -> Decimal:
        """Redeem points for a discount. Returns discount amount."""
        if points > self.points_balance:
            points = self.points_balance
        discount = Decimal(points) * self.REDEMPTION_RATE
        self.points_balance -= points
        self.total_points_redeemed += points
        return discount.quantize(Decimal("0.01"))

    def _update_tier(self):
        """Update tier based on total points earned."""
        for tier, threshold in sorted(
            self.TIER_THRESHOLDS.items(), key=lambda x: x[1], reverse=True
        ):
            if self.total_points_earned >= threshold:
                self.tier = tier
                break

    def __repr__(self) -> str:
        return f"<LoyaltyAccount {self.tier}: {self.points_balance} pts>"


class PointsLedger(Base):
    """Tracks all point transactions for audit."""

    __tablename__ = "points_ledger"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    loyalty_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loyalty_accounts.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    points_change: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


# ── Scheduling Capacity ─────────────────────────────────────────────────────
class ScheduleCapacity(Base):
    """Controls how many orders can be accepted per time slot."""

    __tablename__ = "schedule_capacity"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    time_slot: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "10:00-12:00"

    max_orders: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_cake_orders: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    current_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_cake_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def has_capacity(self, is_cake: bool = False) -> bool:
        """Check if this time slot has capacity."""
        if self.is_blocked:
            return False
        if self.current_orders >= self.max_orders:
            return False
        if is_cake and self.current_cake_orders >= self.max_cake_orders:
            return False
        return True

    def __repr__(self) -> str:
        return f"<ScheduleCapacity {self.date} {self.time_slot}: {self.current_orders}/{self.max_orders}>"


# ── Deposit Payments (for cakes) ─────────────────────────────────────────────
class CakeDeposit(Base):
    """Deposit payment tracking for cake orders."""

    __tablename__ = "cake_deposits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    deposit_percentage: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    # Stripe
    deposit_payment_intent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    final_payment_intent: Mapped[str | None] = mapped_column(String(255), nullable=True)

    deposit_paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    final_paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    deposit_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    final_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<CakeDeposit ${self.deposit_amount} / ${self.remaining_amount}>"
