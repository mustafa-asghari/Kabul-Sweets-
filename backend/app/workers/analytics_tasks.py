"""
Analytics background tasks — periodic aggregation jobs.
Daily revenue roll-up and low-stock alerts.
"""

import logging
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import Date, case, cast, create_engine, func, select
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.core.config import get_settings
from app.models.analytics import DailyRevenue
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import ProductVariant

logger = logging.getLogger("app.workers.analytics")
settings = get_settings()

# Sync DB URL for Celery (Celery doesn't use async)
DATABASE_URL = os.getenv("DATABASE_URL", "").replace("+asyncpg", "+psycopg")
_engine = None


def _get_sync_engine():
    global _engine
    if _engine is None and DATABASE_URL:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=3)
    return _engine


@celery_app.task(
    name="app.workers.analytics_tasks.aggregate_daily_revenue",
    max_retries=2,
)
def aggregate_daily_revenue():
    """
    Aggregate yesterday's revenue into the daily_revenue table.
    Runs daily via Celery Beat.
    """
    engine = _get_sync_engine()
    if not engine:
        logger.warning("Database not configured — skipping revenue aggregation")
        return

    yesterday = date.today() - timedelta(days=1)
    start = datetime.combine(yesterday, datetime.min.time()).replace(tzinfo=timezone.utc)
    end = datetime.combine(yesterday, datetime.max.time()).replace(tzinfo=timezone.utc)

    paid_statuses = [OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.COMPLETED]

    with Session(engine) as session:
        # Check if already aggregated
        existing = session.execute(
            select(DailyRevenue).where(DailyRevenue.date == yesterday)
        ).scalar_one_or_none()

        if existing:
            logger.info("Daily revenue for %s already aggregated", yesterday)
            return

        # Aggregate order data
        result = session.execute(
            select(
                func.coalesce(func.sum(Order.total), 0).label("total_revenue"),
                func.count(Order.id).label("total_orders"),
                func.coalesce(func.avg(Order.total), 0).label("avg_order_value"),
                func.sum(case((Order.has_cake == True, 1), else_=0)).label("cake_orders"),
            ).where(
                Order.status.in_(paid_statuses),
                Order.paid_at >= start,
                Order.paid_at <= end,
            )
        ).one()

        # Count items sold
        items_count = session.execute(
            select(func.coalesce(func.sum(OrderItem.quantity), 0)).where(
                OrderItem.order_id.in_(
                    select(Order.id).where(
                        Order.status.in_(paid_statuses),
                        Order.paid_at >= start,
                        Order.paid_at <= end,
                    )
                )
            )
        ).scalar() or 0

        # Create daily revenue record
        daily = DailyRevenue(
            date=yesterday,
            total_revenue=float(result.total_revenue),
            total_orders=result.total_orders,
            total_items_sold=items_count,
            cake_orders=result.cake_orders or 0,
            average_order_value=float(result.avg_order_value),
        )
        session.add(daily)
        session.commit()

        logger.info(
            "✅ Daily revenue aggregated for %s: $%.2f (%d orders)",
            yesterday, float(result.total_revenue), result.total_orders,
        )


@celery_app.task(
    name="app.workers.analytics_tasks.check_low_stock_alerts",
    max_retries=1,
)
def check_low_stock_alerts():
    """
    Check for low stock items and publish alerts.
    Runs hourly via Celery Beat.
    """
    engine = _get_sync_engine()
    if not engine:
        logger.warning("Database not configured — skipping low stock check")
        return

    with Session(engine) as session:
        low_stock = session.execute(
            select(ProductVariant).where(
                ProductVariant.stock_quantity <= ProductVariant.low_stock_threshold,
                ProductVariant.is_active == True,
            )
        ).scalars().all()

        if not low_stock:
            logger.info("✅ No low stock items")
            return

        logger.warning("⚠️ %d items with low stock:", len(low_stock))
        for v in low_stock:
            logger.warning(
                "  - %s: %d remaining (threshold: %d)",
                v.name, v.stock_quantity, v.low_stock_threshold,
            )

        # Publish to Redis for admin dashboard notification
        try:
            import json
            import redis

            r = redis.from_url(settings.REDIS_URL)
            alert_data = {
                "type": "low_stock",
                "count": len(low_stock),
                "items": [
                    {"name": v.name, "stock": v.stock_quantity, "threshold": v.low_stock_threshold}
                    for v in low_stock[:10]
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            r.publish("admin:alerts", json.dumps(alert_data))
        except Exception as e:
            logger.warning("Could not publish low stock alert to Redis: %s", str(e))
