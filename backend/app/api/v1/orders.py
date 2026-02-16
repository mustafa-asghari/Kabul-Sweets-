"""
Order management endpoints.
Customer: create order, view their orders. Admin: view all, update status, filter.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, log_admin_action, require_admin
from app.core.database import get_db
from app.models.user import User
from app.models.order import OrderStatus
from app.schemas.order import (
    OrderCreate,
    OrderListResponse,
    OrderResponse,
    OrderUpdateAdmin,
)
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


# ── Customer Endpoints ───────────────────────────────────────────────────────
@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_order(
    data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new order. Validates items, reserves inventory, calculates totals."""
    service = OrderService(db)
    try:
        order = await service.create_order(data, customer_id=current_user.id)
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/my-orders", response_model=list[OrderListResponse])
async def get_my_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's orders."""
    service = OrderService(db)
    return await service.get_customer_orders(current_user.id, skip=skip, limit=limit)


@router.get("/my-orders/{order_id}", response_model=OrderResponse)
async def get_my_order(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific order belonging to the current user."""
    service = OrderService(db)
    order = await service.get_order(order_id)
    if not order or order.customer_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# ── Admin Endpoints ──────────────────────────────────────────────────────────
@router.get(
    "/",
    response_model=list[OrderListResponse],
    dependencies=[Depends(require_admin)],
)
async def list_orders(
    status_filter: str | None = Query(None, alias="status"),
    has_cake: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] List all orders with filters."""
    service = OrderService(db)
    return await service.list_orders(
        status=status_filter,
        has_cake=has_cake,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/count",
    dependencies=[Depends(require_admin)],
)
async def count_orders(
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Count orders by status."""
    service = OrderService(db)
    return {"total": await service.count_orders(status=status_filter)}


@router.get(
    "/cake-orders",
    response_model=list[OrderListResponse],
    dependencies=[Depends(require_admin)],
)
async def list_cake_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] List only cake orders for quick filtering."""
    service = OrderService(db)
    return await service.list_orders(has_cake=True, skip=skip, limit=limit)


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    dependencies=[Depends(require_admin)],
)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get a specific order."""
    service = OrderService(db)
    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get(
    "/number/{order_number}",
    response_model=OrderResponse,
    dependencies=[Depends(require_admin)],
)
async def get_order_by_number(
    order_number: str,
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get an order by order number."""
    service = OrderService(db)
    order = await service.get_order_by_number(order_number)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: uuid.UUID,
    data: OrderUpdateAdmin,
    admin: User = Depends(log_admin_action),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Update order status, pickup time, or notes."""
    service = OrderService(db)
    order = await service.update_order_admin(order_id, data)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/{order_id}/approve")
async def approve_order(
    order_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Approve a pending order and capture payment."""
    service = OrderService(db)
    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail=f"Cannot approve order in status '{order.status.value}'")
    if not order.payment:
        raise HTTPException(status_code=400, detail="No payment record found")

    from app.services.stripe_service import StripeService
    if order.payment.stripe_payment_intent_id:
        await StripeService.capture_payment_intent(order.payment.stripe_payment_intent_id)

    updated = await service.mark_order_paid(
        order_id=order.id,
        stripe_payment_intent_id=order.payment.stripe_payment_intent_id or f"manual_{order.id}",
        stripe_checkout_session_id=order.payment.stripe_checkout_session_id,
        webhook_data={"approved_by_admin_id": str(admin.id)},
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"success": True, "message": "Order approved and payment captured"}


@router.post("/{order_id}/reject")
async def reject_order(
    order_id: uuid.UUID,
    reason: str | None = Query(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Reject a pending order and void payment authorization."""
    service = OrderService(db)
    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail=f"Cannot reject order in status '{order.status.value}'")

    if order.payment and order.payment.stripe_payment_intent_id:
        from app.services.stripe_service import StripeService
        await StripeService.cancel_payment_intent(order.payment.stripe_payment_intent_id)

    updated = await service.reject_order_after_authorization(order.id, reason or "Rejected by admin")
    if not updated:
        raise HTTPException(status_code=404, detail="Order not found")

    try:
        from app.workers.email_tasks import send_order_rejection_email

        send_order_rejection_email.delay(
            {
                "order_id": str(updated.id),
                "order_number": updated.order_number,
                "customer_name": updated.customer_name,
                "customer_email": updated.customer_email,
                "total": str(updated.total),
                "rejection_reason": reason or "Rejected by admin",
            }
        )
    except Exception:
        pass

    return {"success": True, "message": "Order rejected and customer notified"}


@router.get("/{order_id}/risk-analysis")
async def get_order_risk_analysis(
    order_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get fraud risk analysis for an order."""
    from app.services.analytics_service import AnalyticsService
    service = AnalyticsService(db)
    return await service.get_order_risk_analysis(order_id)
