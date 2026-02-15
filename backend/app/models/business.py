"""
Business models — Phase 13.
Scheduling capacity and deposit payments.
"""

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


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
