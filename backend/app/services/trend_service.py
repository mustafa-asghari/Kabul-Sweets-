"""
AI Trend Detection Service.
Compares week-over-week sales data to detect rising/falling product trends.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import Date, case, cast, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.order import Order, OrderItem, OrderStatus

logger = get_logger("trend_service")

PAID_STATUSES = [OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.COMPLETED]
SIGNIFICANT_CHANGE_THRESHOLD = 15  # % change to flag as a trend


class TrendService:
    """Detects sales trends by comparing time periods."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect_product_trends(self, days: int = 7) -> dict:
        """
        Compare this period's sales vs. the previous period for each product.
        Returns trending up, trending down, and new products.
        """
        now = datetime.now(timezone.utc)
        current_start = now - timedelta(days=days)
        previous_start = current_start - timedelta(days=days)

        current_sales = await self._get_product_sales(current_start, now)
        previous_sales = await self._get_product_sales(previous_start, current_start)

        trending_up = []
        trending_down = []
        new_products = []
        stable = []

        all_products = set(list(current_sales.keys()) + list(previous_sales.keys()))

        for product_name in all_products:
            current = current_sales.get(product_name, {"qty": 0, "revenue": Decimal("0")})
            previous = previous_sales.get(product_name, {"qty": 0, "revenue": Decimal("0")})

            curr_qty = current["qty"]
            prev_qty = previous["qty"]

            if prev_qty == 0 and curr_qty > 0:
                new_products.append({
                    "product_name": product_name,
                    "current_quantity": curr_qty,
                    "current_revenue": str(current["revenue"]),
                    "change_type": "new",
                })
                continue

            if prev_qty == 0:
                continue

            pct_change = ((curr_qty - prev_qty) / prev_qty) * 100

            entry = {
                "product_name": product_name,
                "current_quantity": curr_qty,
                "previous_quantity": prev_qty,
                "current_revenue": str(current["revenue"]),
                "previous_revenue": str(previous["revenue"]),
                "percent_change": round(pct_change, 1),
            }

            if pct_change >= SIGNIFICANT_CHANGE_THRESHOLD:
                entry["change_type"] = "up"
                trending_up.append(entry)
            elif pct_change <= -SIGNIFICANT_CHANGE_THRESHOLD:
                entry["change_type"] = "down"
                trending_down.append(entry)
            else:
                entry["change_type"] = "stable"
                stable.append(entry)

        # Sort by magnitude of change
        trending_up.sort(key=lambda x: x["percent_change"], reverse=True)
        trending_down.sort(key=lambda x: x["percent_change"])

        return {
            "period_days": days,
            "current_period": {
                "start": current_start.isoformat(),
                "end": now.isoformat(),
            },
            "previous_period": {
                "start": previous_start.isoformat(),
                "end": current_start.isoformat(),
            },
            "trending_up": trending_up,
            "trending_down": trending_down,
            "new_products": new_products,
            "stable_count": len(stable),
            "summary": self._build_summary(trending_up, trending_down, new_products),
        }

    async def detect_revenue_trends(self) -> dict:
        """Compare this week's total revenue to last week's."""
        now = datetime.now(timezone.utc)
        this_week_start = now - timedelta(days=7)
        last_week_start = this_week_start - timedelta(days=7)

        this_week = await self._get_revenue(this_week_start, now)
        last_week = await self._get_revenue(last_week_start, this_week_start)

        if last_week["revenue"] > 0:
            revenue_change = (
                (this_week["revenue"] - last_week["revenue"]) / last_week["revenue"]
            ) * 100
        else:
            revenue_change = 100.0 if this_week["revenue"] > 0 else 0.0

        if last_week["orders"] > 0:
            order_change = (
                (this_week["orders"] - last_week["orders"]) / last_week["orders"]
            ) * 100
        else:
            order_change = 100.0 if this_week["orders"] > 0 else 0.0

        return {
            "this_week": {
                "revenue": str(this_week["revenue"]),
                "orders": this_week["orders"],
                "avg_order_value": str(this_week["avg"]),
            },
            "last_week": {
                "revenue": str(last_week["revenue"]),
                "orders": last_week["orders"],
                "avg_order_value": str(last_week["avg"]),
            },
            "revenue_change_pct": round(revenue_change, 1),
            "order_change_pct": round(order_change, 1),
            "revenue_trend": "up" if revenue_change > 5 else "down" if revenue_change < -5 else "stable",
        }

    async def _get_product_sales(
        self, start: datetime, end: datetime
    ) -> dict[str, dict]:
        """Get quantity and revenue per product in a time range."""
        result = await self.db.execute(
            select(
                OrderItem.product_name,
                func.sum(OrderItem.quantity).label("total_qty"),
                func.sum(OrderItem.line_total).label("total_revenue"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.status.in_(PAID_STATUSES),
                Order.paid_at >= start,
                Order.paid_at < end,
            )
            .group_by(OrderItem.product_name)
        )

        return {
            row.product_name: {
                "qty": row.total_qty or 0,
                "revenue": Decimal(str(row.total_revenue or 0)),
            }
            for row in result.all()
        }

    async def _get_revenue(self, start: datetime, end: datetime) -> dict:
        """Get total revenue and order count in a time range."""
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(Order.total), 0).label("revenue"),
                func.count(Order.id).label("orders"),
                func.coalesce(func.avg(Order.total), 0).label("avg"),
            ).where(
                Order.status.in_(PAID_STATUSES),
                Order.paid_at >= start,
                Order.paid_at < end,
            )
        )
        row = result.one()
        return {
            "revenue": Decimal(str(row.revenue)),
            "orders": row.orders,
            "avg": Decimal(str(row.avg)).quantize(Decimal("0.01")),
        }

    def _build_summary(
        self,
        trending_up: list[dict],
        trending_down: list[dict],
        new_products: list[dict],
    ) -> list[str]:
        """Build human-readable trend summary messages."""
        messages = []

        for item in trending_up[:3]:
            messages.append(
                f"{item['product_name']} sales up {item['percent_change']}% "
                f"({item['previous_quantity']} -> {item['current_quantity']} units)"
            )

        for item in trending_down[:3]:
            messages.append(
                f"{item['product_name']} sales down {abs(item['percent_change'])}% "
                f"({item['previous_quantity']} -> {item['current_quantity']} units)"
            )

        for item in new_products[:2]:
            messages.append(
                f"{item['product_name']} is new this period "
                f"({item['current_quantity']} units sold)"
            )

        return messages
