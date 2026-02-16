"""
Pydantic schemas for analytics events and dashboard data.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# ── Event Tracking ───────────────────────────────────────────────────────────
class AnalyticsEventCreate(BaseModel):
    """Record an analytics event."""
    event_type: str = Field(..., max_length=100)
    resource_type: str | None = None
    resource_id: str | None = None
    properties: dict | None = {}
    page_url: str | None = None
    referrer: str | None = None
    session_id: str | None = None


class AnalyticsEventResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    user_id: uuid.UUID | None
    resource_type: str | None
    resource_id: str | None
    properties: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Dashboard Data ───────────────────────────────────────────────────────────
class RevenueSummary(BaseModel):
    """Revenue summary for a time period."""
    total_revenue: Decimal
    total_orders: int
    total_items_sold: int
    cake_orders: int
    average_order_value: Decimal
    period_start: date
    period_end: date


class DailyRevenueResponse(BaseModel):
    date: date
    total_revenue: Decimal
    total_orders: int
    total_items_sold: int
    cake_orders: int
    average_order_value: Decimal
    category_breakdown: dict | None

    model_config = {"from_attributes": True}


class BestSellerResponse(BaseModel):
    """Best/worst selling product."""
    product_id: uuid.UUID
    product_name: str
    category: str
    total_quantity_sold: int
    total_revenue: Decimal


class PopularVariantResponse(BaseModel):
    """Popular cake size / product variant."""
    variant_id: uuid.UUID
    variant_name: str
    product_name: str
    total_quantity_sold: int
    total_revenue: Decimal


class InventoryTurnoverResponse(BaseModel):
    """Inventory turnover metric."""
    product_id: uuid.UUID
    product_name: str
    variant_name: str
    current_stock: int
    total_sold_30d: int
    turnover_rate: float  # times sold out in 30 days
    days_of_stock_remaining: float | None


class DashboardSummary(BaseModel):
    """Admin dashboard summary."""
    revenue_today: Decimal
    revenue_this_week: Decimal
    revenue_this_month: Decimal
    orders_today: int
    orders_pending: int
    orders_preparing: int
    cake_orders_today: int
    low_stock_count: int
    total_customers: int


class WeeklyOrderStatusMixResponse(BaseModel):
    """Weekly order status mix for operations chart."""
    week_start: date
    week_end: date
    passed_orders: int
    rejected_orders: int
    pending_orders: int
    total_orders: int
