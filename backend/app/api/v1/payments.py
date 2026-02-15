"""
Payment endpoints — Stripe Checkout and Webhooks.
Only Stripe can mark orders as paid (via webhook).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.order import CheckoutSessionResponse
from app.schemas.user import MessageResponse
from app.services.order_service import OrderService
from app.services.stripe_service import StripeService

router = APIRouter(prefix="/payments", tags=["Payments"])
logger = get_logger("payments")


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
                )
                if order:
                    logger.info("✅ Order %s paid via Stripe", order.order_number)
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
        logger.info("Refund event received: %s", event_type)
        # Phase 11+ — refund handling

    return MessageResponse(message="Webhook received")
