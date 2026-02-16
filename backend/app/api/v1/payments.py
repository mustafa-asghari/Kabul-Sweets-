"""
Payment endpoints — Stripe Checkout and Webhooks.
Only Stripe can mark orders as paid (via webhook).
"""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.order import CheckoutSessionResponse
from app.schemas.user import MessageResponse
from app.services.deposit_service import DepositService
from app.services.order_service import OrderService
from app.services.stripe_service import StripeService

router = APIRouter(prefix="/payments", tags=["Payments"])
logger = get_logger("payments")


# ── Deposit Schemas ──────────────────────────────────────────────────────────
class CreateDepositRequest(BaseModel):
    deposit_percentage: int = Field(50, ge=10, le=90)


class RefundRequest(BaseModel):
    amount: Decimal | None = None  # None = full refund
    reason: str = Field(..., min_length=1, max_length=500)


# ── Create Checkout Session ──────────────────────────────────────────────────
@router.post("/{order_id}/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Stripe Checkout Session for an order.
    The customer is redirected to Stripe's hosted checkout page.
    """
    service = OrderService(db)
    order = await service.get_order(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your order")

    if order.status.value != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Order is already {order.status.value}",
        )

    # Build item description
    item_descriptions = [
        f"{item.product_name} ({item.variant_name})" if item.variant_name else item.product_name
        for item in order.items
    ]
    description = ", ".join(item_descriptions)

    # Create Stripe checkout
    result = await StripeService.create_checkout_session(
        order_id=str(order.id),
        order_number=order.order_number,
        amount=order.total,
        currency="aud",
        customer_email=order.customer_email,
        line_items_description=description,
    )

    # Store session ID
    if order.payment:
        order.payment.stripe_checkout_session_id = result["session_id"]

    await db.flush()

    return CheckoutSessionResponse(
        checkout_url=result["checkout_url"],
        session_id=result["session_id"],
        order_id=order.id,
        order_number=order.order_number,
    )


# ── Deposit Endpoints ────────────────────────────────────────────────────────

@router.post("/{order_id}/create-deposit")
async def create_deposit(
    order_id: uuid.UUID,
    data: CreateDepositRequest = CreateDepositRequest(),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Create a deposit payment split for a cake order."""
    service = DepositService(db)
    result = await service.create_deposit(order_id, data.deposit_percentage)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{order_id}/checkout-deposit")
async def checkout_deposit(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Customer pays the deposit portion (50%) via Stripe."""
    service = DepositService(db)
    result = await service.checkout_deposit(order_id, current_user.email)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{order_id}/checkout-final")
async def checkout_final(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Customer pays the remaining balance via Stripe."""
    service = DepositService(db)
    result = await service.checkout_remaining(order_id, current_user.email)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{order_id}/deposit-status")
async def get_deposit_status(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the deposit payment status for an order."""
    service = DepositService(db)
    result = await service.get_deposit_status(order_id)
    if not result:
        raise HTTPException(status_code=404, detail="No deposit found for this order")
    return result


# ── Refund Endpoint ──────────────────────────────────────────────────────────

@router.post("/admin/orders/{order_id}/refund")
async def admin_refund(
    order_id: uuid.UUID,
    data: RefundRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Initiate a full or partial refund for an order."""
    from app.models.order import Order, Payment, PaymentStatus, OrderStatus

    # Get order and payment
    from sqlalchemy import select
    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if not order.payment:
        raise HTTPException(status_code=400, detail="No payment found for this order")

    payment = order.payment
    if payment.status not in (PaymentStatus.SUCCEEDED,):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot refund a payment with status '{payment.status.value}'"
        )

    refund_amount = data.amount or payment.amount

    if refund_amount > payment.amount:
        raise HTTPException(status_code=400, detail="Refund amount exceeds payment amount")

    # Call Stripe to create refund
    try:
        from app.services.stripe_service import STRIPE_AVAILABLE
        if STRIPE_AVAILABLE:
            import stripe
            refund_params = {"amount": int(refund_amount * 100)}
            if payment.stripe_payment_intent_id:
                refund_params["payment_intent"] = payment.stripe_payment_intent_id
            else:
                raise HTTPException(
                    status_code=400,
                    detail="No Stripe payment intent found — refund manually via Stripe dashboard"
                )
            stripe_refund = stripe.Refund.create(**refund_params)
            logger.info("Stripe refund created: %s", stripe_refund.id)
        else:
            logger.warning("Stripe not configured — recording refund locally only")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Stripe refund failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Stripe refund failed: {str(e)}")

    # Update payment record
    payment.refund_amount = refund_amount
    payment.refund_reason = data.reason
    if refund_amount >= payment.amount:
        payment.status = PaymentStatus.REFUNDED
        order.status = OrderStatus.REFUNDED
    else:
        payment.status = PaymentStatus.PARTIALLY_REFUNDED

    await db.flush()

    logger.info(
        "Refund of $%s processed for order %s by admin %s",
        refund_amount, order.order_number, admin.id,
    )

    return {
        "order_id": str(order_id),
        "order_number": order.order_number,
        "refund_amount": str(refund_amount),
        "payment_status": payment.status.value,
        "order_status": order.status.value,
        "reason": data.reason,
    }


# ── Stripe Webhook ───────────────────────────────────────────────────────────
@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Stripe webhook events.
    This is the ONLY way orders transition to 'paid'.
    Verifies webhook signature for security.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    event = StripeService.verify_webhook_signature(payload, sig_header)

    if event is None:
        # In dev without Stripe, accept test payloads
        import json
        try:
            event = json.loads(payload)
            if not event.get("type"):
                raise HTTPException(status_code=400, detail="Invalid webhook payload")
            logger.warning("Processing unverified webhook (dev mode)")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    service = OrderService(db)

    if event_type == "checkout.session.completed":
        order_id = data.get("metadata", {}).get("order_id")
        payment_intent = data.get("payment_intent", "")

        if order_id:
            try:
                order = await service.mark_order_paid(
                    order_id=uuid.UUID(order_id),
                    stripe_payment_intent_id=payment_intent,
                    stripe_checkout_session_id=data.get("id"),
                    webhook_data=data,
                    payment_status=data.get("payment_status", "paid"),
                )
                if order:
                    logger.info("✅ Order %s updated via Stripe (status: %s)", order.order_number, order.status.value)
                else:
                    logger.error("Order not found for webhook: %s", order_id)
            except Exception as e:
                logger.error("Error processing payment webhook: %s", str(e))

    elif event_type == "payment_intent.payment_failed":
        order_id = data.get("metadata", {}).get("order_id")
        if order_id:
            failure_code = data.get("last_payment_error", {}).get("code")
            failure_message = data.get("last_payment_error", {}).get("message")
            await service.mark_payment_failed(
                order_id=uuid.UUID(order_id),
                failure_code=failure_code,
                failure_message=failure_message,
            )
            logger.warning("❌ Payment failed for order %s: %s", order_id, failure_message)

    elif event_type in ("charge.refunded", "charge.refund.updated"):
        from app.models.order import Order, Payment, PaymentStatus, OrderStatus
        from sqlalchemy import select

        payment_intent_id = data.get("payment_intent")
        if payment_intent_id:
            pay_result = await db.execute(
                select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
            )
            payment = pay_result.scalar_one_or_none()
            if payment:
                refund_total = data.get("amount_refunded", 0) / 100  # cents to dollars
                payment.refund_amount = Decimal(str(refund_total))
                if refund_total >= float(payment.amount):
                    payment.status = PaymentStatus.REFUNDED
                    order = await db.execute(
                        select(Order).where(Order.id == payment.order_id)
                    )
                    o = order.scalar_one_or_none()
                    if o:
                        o.status = OrderStatus.REFUNDED
                else:
                    payment.status = PaymentStatus.PARTIALLY_REFUNDED

                await db.flush()
                logger.info("Refund processed via webhook for payment_intent %s", payment_intent_id)
            else:
                logger.warning("No payment found for refund webhook: %s", payment_intent_id)

    return MessageResponse(message="Webhook received")
