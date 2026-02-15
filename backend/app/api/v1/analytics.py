"""
Analytics API endpoints.
Event tracking, revenue dashboard, best sellers, inventory insights.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsEventCreate,
    AnalyticsEventResponse,
    BestSellerResponse,
    DashboardSummary,
    InventoryTurnoverResponse,
    PopularVariantResponse,
    RevenueSummary,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ── Event Tracking (public — for frontend) ──────────────────────────────────
@router.post("/events", response_model=AnalyticsEventResponse)
async def track_event(
    data: AnalyticsEventCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = None,
):
    """
    Record an analytics event.
    Used by the frontend to track page views, add-to-cart, searches, etc.
    """
    service = AnalyticsService(db)

    # Try to get current user (optional — anonymous tracking allowed)
    user_id = None
    try:
        from app.api.deps import bearer_scheme
        creds = await bearer_scheme(request)
        if creds:
            from app.core.security import decode_token
            payload = decode_token(creds.credentials)
            if payload:
                user_id = payload.get("sub")
    except Exception:
        pass

    event = await service.record_event(
        event_type=data.event_type,
        user_id=user_id,
        session_id=data.session_id,
        resource_type=data.resource_type,
        resource_id=data.resource_id,
        properties=data.properties,
        page_url=data.page_url,
        referrer=data.referrer,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return event


# ── Admin Dashboard ──────────────────────────────────────────────────────────
@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get dashboard summary metrics."""
    service = AnalyticsService(db)
    return await service.get_dashboard_summary()


# ── Revenue ──────────────────────────────────────────────────────────────────
@router.get("/revenue/summary", response_model=RevenueSummary)
async def get_revenue_summary(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get revenue summary for a date range."""
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    service = AnalyticsService(db)
    return await service.get_revenue_summary(start_date, end_date)


@router.get("/revenue/daily")
async def get_daily_revenue(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get daily revenue breakdown for charts."""
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    service = AnalyticsService(db)
    return await service.get_daily_revenue(start_date, end_date)


# ── Best / Worst Sellers ─────────────────────────────────────────────────────
@router.get("/best-sellers", response_model=list[BestSellerResponse])
async def get_best_sellers(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get best-selling products."""
    service = AnalyticsService(db)
    return await service.get_best_sellers(days=days, limit=limit)


@router.get("/worst-sellers", response_model=list[BestSellerResponse])
async def get_worst_sellers(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get worst-selling products."""
    service = AnalyticsService(db)
    return await service.get_worst_sellers(days=days, limit=limit)


# ── Cake Analytics ───────────────────────────────────────────────────────────
@router.get("/popular-cake-sizes", response_model=list[PopularVariantResponse])
async def get_popular_cake_sizes(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get most popular cake sizes."""
    service = AnalyticsService(db)
    return await service.get_popular_cake_sizes(days=days, limit=limit)


# ── Inventory Insights ──────────────────────────────────────────────────────
@router.get("/inventory-turnover", response_model=list[InventoryTurnoverResponse])
async def get_inventory_turnover(
    days: int = Query(30, ge=1, le=365),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get inventory turnover rates and days-of-stock-remaining."""
    service = AnalyticsService(db)
    return await service.get_inventory_turnover(days=days)
