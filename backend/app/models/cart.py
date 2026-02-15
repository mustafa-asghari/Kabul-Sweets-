"""
Cart models for tracking shopping carts and abandonment recovery.
"""

import uuid
from datetime import datetime, timezone
import enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CartStatus(str, enum.Enum):
    ACTIVE = "active"
    CONVERTED = "converted"   # Turned into an order
    ABANDONED = "abandoned"   # Explicitly marked as abandoned (optional)
    RECOVERED = "recovered"   # Recovered via email link


class Cart(Base):
    """Shopping cart session."""

    __tablename__ = "carts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    status: Mapped[CartStatus] = mapped_column(
        Enum(CartStatus), default=CartStatus.ACTIVE, nullable=False, index=True
    )

    # Recovery tracking
    recovery_email_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    recovery_sms_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    converted_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False,
        index=True
    )

    def __repr__(self) -> str:
        return f"<Cart {self.id} (Customer {self.customer_id})>"


class CartItem(Base):
    """Items inside a cart."""

    __tablename__ = "cart_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<CartItem {self.product_id} x{self.quantity}>"


class CartRecoveryAttempt(Base):
    """Log of recovery messages sent."""

    __tablename__ = "cart_recovery_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # email, sms
    template: Mapped[str] = mapped_column(String(50), nullable=False)
    
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<RecoveryAttempt {self.channel} for Cart {self.cart_id}>"
