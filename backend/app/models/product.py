"""
Product and ProductVariant models.
Supports multiple sizes/variants per product with independent pricing and inventory.
"""

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProductCategory(str, enum.Enum):
    """Product categories."""
    CAKE = "cake"
    PASTRY = "pastry"
    COOKIE = "cookie"
    BREAD = "bread"
    SWEET = "sweet"
    DRINK = "drink"
    OTHER = "other"


class Product(Base):
    """Product model — represents a bakery item."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[ProductCategory] = mapped_column(
        Enum(ProductCategory), default=ProductCategory.OTHER, nullable=False, index=True
    )

    # Pricing (base price — variants can override)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Images (list of S3 URLs stored as JSON)
    images: Mapped[list | None] = mapped_column(JSONB, default=list)
    thumbnail: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Product metadata
    tags: Mapped[list | None] = mapped_column(JSONB, default=list)  # e.g. halal, gluten-free
    metadata_extra: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # Flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_cake: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Ordering
    max_per_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", lazy="selectin"
    )
    stock_adjustments: Mapped[list["StockAdjustment"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Product {self.name} ({self.category.value})>"


class ProductVariant(Base):
    """Product variant — e.g. cake sizes (6 inch, 8 inch, 10 inch)."""

    __tablename__ = "product_variants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "6 inch", "Small"
    sku: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)

    # Pricing
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Inventory
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    is_in_stock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Cake-specific metadata
    serves: Mapped[int | None] = mapped_column(Integer, nullable=True)  # number of servings
    dimensions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # {diameter, height, layers}

    # Flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    product: Mapped["Product"] = relationship(back_populates="variants")

    def __repr__(self) -> str:
        return f"<ProductVariant {self.name} (${self.price})>"


class StockAdjustment(Base):
    """Tracks all inventory changes for audit & analytics."""

    __tablename__ = "stock_adjustments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    adjusted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Adjustment details
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)  # +/- amount
    previous_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    new_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "restock", "order", "spoilage"
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    # Relationships
    product: Mapped["Product"] = relationship(back_populates="stock_adjustments")

    def __repr__(self) -> str:
        return f"<StockAdjustment {self.quantity_change:+d} for product {self.product_id}>"
