"""
Pydantic schemas for orders, order items, and payments.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


# ── Order Item Schemas ───────────────────────────────────────────────────────
class OrderItemCreate(BaseModel):
    product_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    quantity: int = Field(1, ge=1, le=50)
    cake_message: str | None = Field(None, max_length=200)


class OrderItemResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID | None
    variant_id: uuid.UUID | None
    product_name: str
    variant_name: str | None
    unit_price: Decimal
    quantity: int
    line_total: Decimal
    cake_message: str | None

    model_config = {"from_attributes": True}


# ── Order Schemas ────────────────────────────────────────────────────────────
class OrderCreate(BaseModel):
    """Create a new order."""
    items: list[OrderItemCreate] = Field(..., min_length=1)
    customer_name: str = Field(..., min_length=1, max_length=255)
    customer_email: EmailStr
    customer_phone: str | None = Field(None, max_length=20)
    pickup_date: datetime | None = None
    pickup_time_slot: str | None = Field(None, max_length=50)
    cake_message: str | None = Field(None, max_length=200)
    special_instructions: str | None = None
    discount_code: str | None = None


class OrderUpdateAdmin(BaseModel):
    """Admin-only order update."""
    status: str | None = None
    pickup_date: datetime | None = None
    pickup_time_slot: str | None = None
    admin_notes: str | None = None


class OrderResponse(BaseModel):
    id: uuid.UUID
    order_number: str
    customer_id: uuid.UUID | None
    status: str
    customer_name: str
    customer_email: str
    customer_phone: str | None
    pickup_date: datetime | None
    pickup_time_slot: str | None
    cake_message: str | None
    has_cake: bool
    special_instructions: str | None
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total: Decimal
    discount_code: str | None
    admin_notes: str | None
    items: list[OrderItemResponse]
    payment: "PaymentResponse | None"
    created_at: datetime
    updated_at: datetime
    paid_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    """Lightweight order for list views."""
    id: uuid.UUID
    order_number: str
    customer_name: str
    status: str
    has_cake: bool
    total: Decimal
    pickup_date: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Payment Schemas ──────────────────────────────────────────────────────────
class PaymentResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    stripe_checkout_session_id: str | None
    stripe_payment_intent_id: str | None
    amount: Decimal
    currency: str
    status: str
    payment_method: str | None
    refund_amount: Decimal | None
    failure_code: str | None
    failure_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CheckoutSessionResponse(BaseModel):
    """Response with Stripe checkout URL."""
    checkout_url: str
    session_id: str
    order_id: uuid.UUID
    order_number: str


# Resolve forward reference
OrderResponse.model_rebuild()
