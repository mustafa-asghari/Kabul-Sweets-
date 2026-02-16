"""
Analytics service — business intelligence queries.
Revenue tracking, best sellers, inventory turnover, and dashboard data.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import Date, case, cast, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.analytics import AnalyticsEvent, DailyRevenue
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product, ProductVariant
from app.models.user import User, UserRole

logger = get_logger("analytics_service")


class AnalyticsService:
    """Handles analytics queries and aggregations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Event Tracking ───────────────────────────────────────────────────
    async def record_event(
        self,
        event_type: str,
        user_id: uuid.UUID | None = None,
        session_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        properties: dict | None = None,
        page_url: str | None = None,
        referrer: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AnalyticsEvent:
        """Record an analytics event."""
        event = AnalyticsEvent(
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            resource_type=resource_type,
            resource_id=resource_id,
            properties=properties or {},
            page_url=page_url,
            referrer=referrer,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    # ── Revenue Tracking ─────────────────────────────────────────────────
    async def get_revenue_summary(
        self,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Get revenue summary for a date range."""
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)

        result = await self.db.execute(
            select(
                func.coalesce(func.sum(Order.total), 0).label("total_revenue"),
                func.count(Order.id).label("total_orders"),
                func.coalesce(func.avg(Order.total), 0).label("average_order_value"),
                func.sum(case((Order.has_cake == True, 1), else_=0)).label("cake_orders"),
            ).where(
                Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.COMPLETED]),
                Order.paid_at >= start_dt,
                Order.paid_at <= end_dt,
            )
        )
        row = result.one()

        # Total items sold
        items_result = await self.db.execute(
            select(func.coalesce(func.sum(OrderItem.quantity), 0)).where(
                OrderItem.order_id.in_(
                    select(Order.id).where(
                        Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.COMPLETED]),
                        Order.paid_at >= start_dt,
                        Order.paid_at <= end_dt,
                    )
                )
            )
        )
        total_items = items_result.scalar() or 0

        return {
            "total_revenue": Decimal(str(row.total_revenue)),
            "total_orders": row.total_orders,
            "total_items_sold": total_items,
            "cake_orders": row.cake_orders or 0,
            "average_order_value": Decimal(str(row.average_order_value)).quantize(Decimal("0.01")),
            "period_start": start_date,
            "period_end": end_date,
        }

    async def get_daily_revenue(
        self,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """Get daily revenue breakdown for charting."""
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)

        result = await self.db.execute(
            select(
                cast(Order.paid_at, Date).label("date"),
                func.coalesce(func.sum(Order.total), 0).label("total_revenue"),
                func.count(Order.id).label("total_orders"),
                func.sum(case((Order.has_cake == True, 1), else_=0)).label("cake_orders"),
            ).where(
                Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.COMPLETED]),
                Order.paid_at >= start_dt,
                Order.paid_at <= end_dt,
            ).group_by(
                cast(Order.paid_at, Date)
            ).order_by(
                cast(Order.paid_at, Date)
            )
        )

        return [
            {
                "date": row.date,
                "total_revenue": Decimal(str(row.total_revenue)),
                "total_orders": row.total_orders,
                "cake_orders": row.cake_orders or 0,
            }
            for row in result.all()
        ]

    # ── Best / Worst Sellers ─────────────────────────────────────────────
    async def get_best_sellers(self, days: int = 30, limit: int = 10) -> list[dict]:
        """Get best-selling products by quantity in the last N days."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(
                OrderItem.product_id,
                OrderItem.product_name,
                func.sum(OrderItem.quantity).label("total_quantity_sold"),
                func.sum(OrderItem.line_total).label("total_revenue"),
            ).join(
                Order, OrderItem.order_id == Order.id
            ).where(
                Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.COMPLETED]),
                Order.created_at >= since,
            ).group_by(
                OrderItem.product_id, OrderItem.product_name
            ).order_by(
                desc("total_quantity_sold")
            ).limit(limit)
        )

        items = []
        for row in result.all():
            # Get product category
            prod = await self.db.execute(select(Product.category).where(Product.id == row.product_id))
            cat = prod.scalar() or "other"

            items.append({
                "product_id": row.product_id,
                "product_name": row.product_name,
                "category": cat.value if hasattr(cat, "value") else str(cat),
                "total_quantity_sold": row.total_quantity_sold,
                "total_revenue": Decimal(str(row.total_revenue)),
            })
        return items

    async def get_worst_sellers(self, days: int = 30, limit: int = 10) -> list[dict]:
        """Get worst-selling products (lowest quantity sold)."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(
                OrderItem.product_id,
                OrderItem.product_name,
                func.sum(OrderItem.quantity).label("total_quantity_sold"),
                func.sum(OrderItem.line_total).label("total_revenue"),
            ).join(
                Order, OrderItem.order_id == Order.id
            ).where(
                Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.COMPLETED]),
                Order.created_at >= since,
            ).group_by(
                OrderItem.product_id, OrderItem.product_name
            ).order_by(
                "total_quantity_sold"  # ascending = worst sellers first
            ).limit(limit)
        )

        items = []
        for row in result.all():
            prod = await self.db.execute(select(Product.category).where(Product.id == row.product_id))
            cat = prod.scalar() or "other"
            items.append({
                "product_id": row.product_id,
                "product_name": row.product_name,
                "category": cat.value if hasattr(cat, "value") else str(cat),
                "total_quantity_sold": row.total_quantity_sold,
                "total_revenue": Decimal(str(row.total_revenue)),
            })
        return items

    # ── Popular Cake Sizes ───────────────────────────────────────────────
    async def get_popular_cake_sizes(self, days: int = 30, limit: int = 10) -> list[dict]:
        """Track most popular cake sizes/variants."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(
                OrderItem.variant_id,
                OrderItem.variant_name,
                OrderItem.product_name,
                func.sum(OrderItem.quantity).label("total_quantity_sold"),
                func.sum(OrderItem.line_total).label("total_revenue"),
            ).join(
                Order, OrderItem.order_id == Order.id
            ).where(
                Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.COMPLETED]),
                Order.has_cake == True,
                Order.created_at >= since,
                OrderItem.variant_id.isnot(None),
            ).group_by(
                OrderItem.variant_id, OrderItem.variant_name, OrderItem.product_name
            ).order_by(
                desc("total_quantity_sold")
            ).limit(limit)
        )

        return [
            {
                "variant_id": row.variant_id,
                "variant_name": row.variant_name,
                "product_name": row.product_name,
                "total_quantity_sold": row.total_quantity_sold,
                "total_revenue": Decimal(str(row.total_revenue)),
            }
            for row in result.all()
        ]

    # ── Inventory Turnover ───────────────────────────────────────────────
    async def get_inventory_turnover(self, days: int = 30) -> list[dict]:
        """Calculate inventory turnover rate per variant."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Get sales per variant in last N days
        sales = await self.db.execute(
            select(
                OrderItem.variant_id,
                func.sum(OrderItem.quantity).label("total_sold"),
            ).join(
                Order, OrderItem.order_id == Order.id
            ).where(
                Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.COMPLETED]),
                Order.created_at >= since,
                OrderItem.variant_id.isnot(None),
            ).group_by(OrderItem.variant_id)
        )
        sales_map = {row.variant_id: row.total_sold for row in sales.all()}

        # Get all active variants
        variants = await self.db.execute(
            select(ProductVariant, Product.name.label("product_name")).join(
                Product, ProductVariant.product_id == Product.id
            ).where(ProductVariant.is_active == True)
        )

        results = []
        for row in variants.all():
            variant = row[0]
            product_name = row.product_name
            total_sold = sales_map.get(variant.id, 0)
            current_stock = variant.stock_quantity

            # Turnover rate: how many times stock was "sold through"
            if current_stock > 0:
                turnover_rate = total_sold / current_stock
                # Days of stock remaining at current sell rate
                daily_rate = total_sold / days if total_sold > 0 else 0
                days_remaining = current_stock / daily_rate if daily_rate > 0 else None
            else:
                turnover_rate = float(total_sold) if total_sold > 0 else 0
                days_remaining = 0

            results.append({
                "product_id": variant.product_id,
                "product_name": product_name,
                "variant_name": variant.name,
                "current_stock": current_stock,
                "total_sold_30d": total_sold,
                "turnover_rate": round(turnover_rate, 2),
                "days_of_stock_remaining": round(days_remaining, 1) if days_remaining is not None else None,
            })

        # Sort by turnover rate descending
        results.sort(key=lambda x: x["turnover_rate"], reverse=True)
        return results

    # ── Dashboard Summary ────────────────────────────────────────────────
    async def get_dashboard_summary(self) -> dict:
        """Get admin dashboard summary metrics."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)

        paid_statuses = [OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.COMPLETED]

        async def _revenue_since(since: datetime) -> Decimal:
            r = await self.db.execute(
                select(func.coalesce(func.sum(Order.total), 0)).where(
                    Order.status.in_(paid_statuses), Order.paid_at >= since
                )
            )
            return Decimal(str(r.scalar() or 0))

        async def _count_orders(status=None, since=None) -> int:
            q = select(func.count(Order.id))
            if status:
                q = q.where(Order.status == status)
            if since:
                q = q.where(Order.created_at >= since)
            r = await self.db.execute(q)
            return r.scalar() or 0

        # Low stock count
        low_stock = await self.db.execute(
            select(func.count(ProductVariant.id)).where(
                ProductVariant.stock_quantity <= ProductVariant.low_stock_threshold,
                ProductVariant.is_active == True,
            )
        )

        # Total customers
        customers = await self.db.execute(
            select(func.count(User.id)).where(User.role == UserRole.CUSTOMER)
        )

        return {
            "revenue_today": await _revenue_since(today_start),
            "revenue_this_week": await _revenue_since(week_start),
            "revenue_this_month": await _revenue_since(month_start),
            "orders_today": await _count_orders(since=today_start),
            "orders_pending": await _count_orders(status=OrderStatus.PENDING),
            "orders_pending_approval": await _count_orders(status=OrderStatus.PENDING_APPROVAL),
            "orders_preparing": await _count_orders(status=OrderStatus.PREPARING),
            "cake_orders_today": (await self.db.execute(
                select(func.count(Order.id)).where(
                    Order.has_cake == True, Order.created_at >= today_start
                )
            )).scalar() or 0,
            "low_stock_count": low_stock.scalar() or 0,
            "total_customers": customers.scalar() or 0,
        }

    # ── Visitor Analytics ────────────────────────────────────────────────
    async def get_visitor_analytics(self, days: int = 30) -> dict:
        """Get visitor analytics (visits over time, by location)."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Daily visits
        daily = await self.db.execute(
            select(
                cast(AnalyticsEvent.created_at, Date).label("date"),
                func.count(AnalyticsEvent.id).label("visits"),
                func.count(func.distinct(AnalyticsEvent.session_id)).label("unique_visitors"),
            ).where(
                AnalyticsEvent.created_at >= since,
                AnalyticsEvent.event_type == "page_view"
            ).group_by(
                cast(AnalyticsEvent.created_at, Date)
            ).order_by(
                cast(AnalyticsEvent.created_at, Date)
            )
        )
        
        visits_over_time = [
            {"date": row.date, "visits": row.visits, "unique_visitors": row.unique_visitors}
            for row in daily.all()
        ]

        # By Location (Simulated by IP for now as we don't have geoip setup)
        # In a real app, we'd enrichment IP to City/Country
        # Here we just return empty or dummy data if no IP enrichment
        locations = []
        
        # By Device
        devices = await self.db.execute(
             select(
                AnalyticsEvent.user_agent, 
                func.count(AnalyticsEvent.id)
            ).where(
                AnalyticsEvent.created_at >= since
            ).group_by(AnalyticsEvent.user_agent).limit(10)
        )
        # Simplified parser
        device_stats = [] # Placeholder

        return {
            "visits_over_time": visits_over_time,
            "top_locations": locations,
            "device_breakdown": device_stats
        }

    # ── Order Risk Analysis ──────────────────────────────────────────────
    async def get_order_risk_analysis(self, order_id: uuid.UUID) -> dict:
        """Get detailed risk/fraud analysis for an order."""
        order = await self.db.get(Order, order_id)
        if not order:
             return {"error": "Order not found"}
        
        # 1. Customer History
        customer_stats = {"total_spent": 0, "order_count": 0, "avg_value": 0}
        if order.customer_id:
             history = await self.db.execute(
                 select(
                     func.count(Order.id),
                     func.sum(Order.total)
                 ).where(
                     Order.customer_id == order.customer_id,
                     Order.id != order_id,
                     Order.status.in_([OrderStatus.PAID, OrderStatus.COMPLETED, OrderStatus.CONFIRMED])
                 )
             )
             cnt, total = history.one()
             customer_stats = {
                 "order_count": cnt or 0, 
                 "total_spent": float(total or 0),
                 "avg_value": float((total / cnt) if cnt else 0)
             }

        # 2. IP check (if we had it tracked on order, or link via session)
        # For now, simplistic checks
        risk_score = 0
        risk_factors = []

        if order.total > 500:
            risk_score += 20
            risk_factors.append("High value order (>$500)")
        
        if order.customer_email.endswith(".xyz"): # Example heuristic
            risk_score += 10
            risk_factors.append("Suspicious email domain")

        # 3. Velocity check
        # Check if customer placed many orders recently
        if order.customer_id:
             recent = await self.db.execute(
                 select(func.count(Order.id)).where(
                     Order.customer_id == order.customer_id,
                     Order.created_at >= datetime.now(timezone.utc) - timedelta(hours=24)
                 )
             )
             if (recent.scalar() or 0) > 3:
                 risk_score += 30
                 risk_factors.append("High order velocity (>3 in 24h)")

        return {
            "risk_score": min(risk_score, 100),
            "risk_level": "High" if risk_score > 50 else ("Medium" if risk_score > 20 else "Low"),
            "risk_factors": risk_factors,
            "customer_stats": customer_stats,
            "payment_method": order.payment.payment_method if order.payment else "Unknown",
            "billing_matches_shipping": True # Placeholder
        }
