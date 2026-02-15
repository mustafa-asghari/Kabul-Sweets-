"""
Analytics event model.
Tracks user actions, page views, conversions, and business metrics.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, Numeric, String, Text, Date
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnalyticsEvent(Base):
    """Tracks user/system events for analytics."""

    __tablename__ = "analytics_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # e.g. "page_view", "add_to_cart", "purchase", "search"
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    session_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )

    # Event data
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # product, order, etc.
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    properties: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # Context
    page_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        nullable=False, index=True,
    )

    def __repr__(self) -> str:
        return f"<AnalyticsEvent {self.event_type} at {self.created_at}>"


class DailyRevenue(Base):
    """Pre-aggregated daily revenue for fast dashboard queries."""

    __tablename__ = "daily_revenue"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    date: Mapped[datetime] = mapped_column(
        Date, unique=True, nullable=False, index=True
    )
    total_revenue: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    total_orders: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_items_sold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    cake_orders: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    average_order_value: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )

    # Breakdown by category
    category_breakdown: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<DailyRevenue {self.date}: ${self.total_revenue}>"
