"""
Trend detection background tasks.
Runs daily to compare this week's vs last week's sales and publish alerts.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.core.config import get_settings
from app.models.order import Order, OrderItem, OrderStatus

logger = logging.getLogger("app.workers.trends")
settings = get_settings()

DATABASE_URL = os.getenv("DATABASE_URL", "").replace("+asyncpg", "+psycopg")
_engine = None

PAID_STATUSES = [OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.COMPLETED]
SIGNIFICANT_CHANGE_THRESHOLD = 15  # %


def _get_sync_engine():
    global _engine
    if _engine is None and DATABASE_URL:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=3)
    return _engine


@celery_app.task(
    name="app.workers.trend_tasks.detect_trends",
    max_retries=2,
)
def detect_trends():
    """
    Compare this week's product sales vs. last week's.
    Publishes trend alerts to Redis for admin dashboard.
    """
    engine = _get_sync_engine()
    if not engine:
        logger.warning("Database not configured — skipping trend detection")
        return

    now = datetime.now(timezone.utc)
    this_week_start = now - timedelta(days=7)
    last_week_start = this_week_start - timedelta(days=7)

    with Session(engine) as session:
        # This week's sales by product
        current = session.execute(
            select(
                OrderItem.product_name,
                func.sum(OrderItem.quantity).label("qty"),
                func.sum(OrderItem.line_total).label("revenue"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.status.in_(PAID_STATUSES),
                Order.paid_at >= this_week_start,
                Order.paid_at < now,
            )
            .group_by(OrderItem.product_name)
        ).all()

        current_map = {r.product_name: {"qty": r.qty, "revenue": float(r.revenue or 0)} for r in current}

        # Last week's sales by product
        previous = session.execute(
            select(
                OrderItem.product_name,
                func.sum(OrderItem.quantity).label("qty"),
                func.sum(OrderItem.line_total).label("revenue"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.status.in_(PAID_STATUSES),
                Order.paid_at >= last_week_start,
                Order.paid_at < this_week_start,
            )
            .group_by(OrderItem.product_name)
        ).all()

        previous_map = {r.product_name: {"qty": r.qty, "revenue": float(r.revenue or 0)} for r in previous}

    # Analyze trends
    trends = []
    all_products = set(list(current_map.keys()) + list(previous_map.keys()))

    for name in all_products:
        curr = current_map.get(name, {"qty": 0, "revenue": 0})
        prev = previous_map.get(name, {"qty": 0, "revenue": 0})

        if prev["qty"] == 0:
            if curr["qty"] > 0:
                trends.append({
                    "product": name,
                    "type": "new",
                    "current_qty": curr["qty"],
                    "message": f"{name} is new this week ({curr['qty']} sold)",
                })
            continue

        pct = ((curr["qty"] - prev["qty"]) / prev["qty"]) * 100

        if abs(pct) >= SIGNIFICANT_CHANGE_THRESHOLD:
            direction = "up" if pct > 0 else "down"
            trends.append({
                "product": name,
                "type": direction,
                "percent_change": round(pct, 1),
                "current_qty": curr["qty"],
                "previous_qty": prev["qty"],
                "message": f"{name} sales {'up' if pct > 0 else 'down'} {abs(round(pct, 1))}%",
            })

    # Sort by magnitude
    trends.sort(key=lambda x: abs(x.get("percent_change", 0)), reverse=True)

    if trends:
        logger.info("Detected %d product trends:", len(trends))
        for t in trends[:5]:
            logger.info("  %s", t["message"])

        # Publish to Redis
        try:
            import redis
            r = redis.from_url(settings.REDIS_URL)
            alert_data = {
                "type": "trend_alert",
                "trends": trends[:10],
                "timestamp": now.isoformat(),
            }
            r.publish("admin:alerts", json.dumps(alert_data))
            # Also store latest trends for dashboard retrieval
            r.set("trends:latest", json.dumps(alert_data), ex=86400 * 2)
        except Exception as e:
            logger.warning("Could not publish trend alert to Redis: %s", str(e))
    else:
        logger.info("No significant product trends detected this period")
