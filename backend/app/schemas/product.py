"""
Pydantic schemas for products and variants.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# ── Variant Schemas ──────────────────────────────────────────────────────────
class VariantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: Decimal = Field(..., ge=0)
    stock_quantity: int = Field(0, ge=0)
    low_stock_threshold: int = Field(5, ge=0)
    serves: int | None = None
    dimensions: dict | None = None
    is_active: bool = True
    sort_order: int = 0


class VariantCreate(VariantBase):
    sku: str | None = None


class VariantUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    price: Decimal | None = Field(None, ge=0)
    stock_quantity: int | None = Field(None, ge=0)
    low_stock_threshold: int | None = Field(None, ge=0)
    serves: int | None = None
    dimensions: dict | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class VariantResponse(VariantBase):
    id: uuid.UUID
    product_id: uuid.UUID
    sku: str | None
    is_in_stock: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Product Schemas ──────────────────────────────────────────────────────────
class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    short_description: str | None = Field(None, max_length=500)
    category: str = "other"
    base_price: Decimal = Field(..., ge=0)
    tags: list[str] | None = []
    is_active: bool = True
    is_featured: bool = False
    is_cake: bool = False
    max_per_order: int | None = None
    sort_order: int = 0


class ProductCreate(ProductBase):
    slug: str | None = None  # Auto-generated from name if not provided
    variants: list[VariantCreate] | None = []


class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = None
    description: str | None = None
    short_description: str | None = None
    category: str | None = None
    base_price: Decimal | None = Field(None, ge=0)
    tags: list[str] | None = None
    is_active: bool | None = None
    is_featured: bool | None = None
    is_cake: bool | None = None
    max_per_order: int | None = None
    sort_order: int | None = None


class ProductResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    short_description: str | None
    category: str
    base_price: Decimal
    images: list | None
    thumbnail: str | None
    tags: list | None
    is_active: bool
    is_featured: bool
    is_cake: bool
    max_per_order: int | None
    sort_order: int
    variants: list[VariantResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    """Lightweight product for list views."""
    id: uuid.UUID
    name: str
    slug: str
    short_description: str | None
    category: str
    base_price: Decimal
    thumbnail: str | None
    is_active: bool
    is_featured: bool
    is_cake: bool
    variants: list[VariantResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Stock Adjustment ─────────────────────────────────────────────────────────
class StockAdjustmentRequest(BaseModel):
    variant_id: uuid.UUID
    quantity_change: int  # positive = restock, negative = remove
    reason: str = Field(..., min_length=1, max_length=255)
    notes: str | None = None


class StockAdjustmentResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID | None
    quantity_change: int
    previous_quantity: int
    new_quantity: int
    reason: str
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
