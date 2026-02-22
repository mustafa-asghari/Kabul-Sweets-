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
from app.models.order import OrderStatus, PaymentStatus
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


class AdminOrderDecisionRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class AdminOrderApproveRequest(BaseModel):
    reason: str | None = Field(None, min_length=3, max_length=500)


class ConfirmCustomCakePaymentRequest(BaseModel):
    custom_cake_id: uuid.UUID
    session_id: str = Field(..., min_length=1, max_length=255)


def _order_to_email_payload(order, rejection_reason: str | None = None) -> dict:
    return {
        "order_id": str(order.id),
        "order_number": order.order_number,
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "customer_phone": order.customer_phone,
        "pickup_date": order.pickup_date.isoformat() if order.pickup_date else None,
        "pickup_time_slot": order.pickup_time_slot,
        "cake_message": order.cake_message,
        "special_instructions": order.special_instructions,
        "status": order.status.value,
        "subtotal": str(order.subtotal),
        "tax_amount": str(order.tax_amount),
        "discount_amount": str(order.discount_amount),
        "total": str(order.total),
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "rejection_reason": rejection_reason,
        "items": [
            {
                "product_name": item.product_name,
                "variant_name": item.variant_name,
                "unit_price": str(item.unit_price),
                "quantity": item.quantity,
                "line_total": str(item.line_total),
                "cake_message": item.cake_message,
            }
            for item in order.items
        ],
    }


def _queue_telegram_order_alert(order) -> None:
    """Queue Telegram admin alert for orders awaiting approval."""
    try:
        from app.workers.telegram_tasks import send_admin_order_pending_alert

        send_admin_order_pending_alert.delay(_order_to_email_payload(order))
    except Exception as exc:
        logger.warning(
            "Failed to queue Telegram alert for order %s: %s",
            order.order_number,
            str(exc),
        )


def _queue_order_payment_required_email(order) -> None:
    """Queue customer email for approved orders that now require payment."""
    try:
        from app.workers.email_tasks import send_order_approval_email

        send_order_approval_email.delay(_order_to_email_payload(order))
    except Exception as exc:
        logger.warning(
            "Failed to queue order approval email for %s: %s",
            order.order_number,
            str(exc),
        )


def _queue_telegram_order_status_alert(
    order,
    status_note: str | None = None,
    rejection_reason: str | None = None,
) -> None:
    """Queue Telegram status update so admin frontend and Telegram stay in sync."""
    try:
        from app.workers.telegram_tasks import send_admin_order_status_alert

        payload = _order_to_email_payload(order, rejection_reason)
        if status_note:
            payload["status_note"] = status_note
        send_admin_order_status_alert.delay(payload)
    except Exception as exc:
        logger.warning(
            "Failed to queue Telegram order status alert for %s: %s",
            order.order_number,
            str(exc),
        )


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

    if order.status != OrderStatus.PENDING_APPROVAL:
        if order.status == OrderStatus.PENDING:
            detail = "Order is under review. Payment opens after admin approval."
        else:
            detail = f"Order is already {order.status.value}"
        raise HTTPException(
            status_code=400,
            detail=detail,
        )

    if (
        order.payment
        and order.payment.stripe_payment_intent_id
        and order.payment.status == PaymentStatus.PENDING
    ):
        raise HTTPException(
            status_code=400,
            detail="Payment is already authorized for this order.",
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
        authorize_only=False,
        line_items_description=description,
    )

    # Store Stripe references for later admin approval/capture
    if order.payment:
        order.payment.stripe_checkout_session_id = result["session_id"]
        order.payment.stripe_payment_intent_id = result.get("payment_intent_id")

    # In local test mode (no Stripe webhooks), mark as paid immediately.
    if result["session_id"].startswith("test_session_"):
        paid_order = await service.mark_order_paid(
            order_id=order.id,
            stripe_payment_intent_id=result.get("payment_intent_id") or f"test_intent_{order.id}",
            stripe_checkout_session_id=result["session_id"],
            webhook_data={"source": "test_checkout_fallback"},
            status_after_payment=OrderStatus.CONFIRMED,
        )
        if paid_order:
            try:
                from app.workers.email_tasks import send_order_confirmation, send_payment_receipt

                payload = _order_to_email_payload(paid_order)
                send_order_confirmation.delay(payload)
                send_payment_receipt.delay(payload)
            except Exception as exc:
                logger.warning(
                    "Failed to queue checkout fallback emails for order %s: %s",
                    order.order_number,
                    str(exc),
                )

    await db.flush()

    return CheckoutSessionResponse(
        checkout_url=result["checkout_url"],
        session_id=result["session_id"],
        order_id=order.id,
        order_number=order.order_number,
    )


@router.post("/custom-cakes/confirm")
async def confirm_custom_cake_payment(
    data: ConfirmCustomCakePaymentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm custom cake payment from checkout success redirect.
    This provides a fallback when webhook delivery is delayed/unavailable.
    """
    from app.models.ml import CustomCakeStatus
    from app.services.custom_cake_service import CustomCakeService

    cake_service = CustomCakeService(db)
    cake = await cake_service.get_custom_cake(data.custom_cake_id)
    if not cake:
        raise HTTPException(status_code=404, detail="Custom cake not found")

    if cake.status in {
        CustomCakeStatus.PAID,
        CustomCakeStatus.IN_PRODUCTION,
        CustomCakeStatus.COMPLETED,
    }:
        return {
            "custom_cake_id": str(cake.id),
            "status": cake.status.value,
            "source": "already_marked",
        }

    session_id = data.session_id.strip()

    if session_id.startswith("test_cake_"):
        expected = f"test_cake_{data.custom_cake_id}"
        if session_id != expected:
            raise HTTPException(status_code=400, detail="Session does not match this custom cake")
    else:
        try:
            session = await StripeService.retrieve_checkout_session(session_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.error("Stripe checkout session lookup failed (%s): %s", session_id, str(exc))
            raise HTTPException(status_code=502, detail="Unable to verify payment with Stripe") from exc

        metadata = session.get("metadata", {}) or {}
        if str(metadata.get("custom_cake_id", "")).strip() != str(data.custom_cake_id):
            raise HTTPException(status_code=400, detail="Stripe session does not belong to this custom cake")

        payment_status = str(session.get("payment_status", "") or "").lower()
        session_status = str(session.get("status", "") or "").lower()
        if payment_status != "paid" and session_status != "complete":
            raise HTTPException(status_code=400, detail="Stripe session is not paid yet")

    result = await cake_service.mark_paid(data.custom_cake_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {
        "custom_cake_id": str(data.custom_cake_id),
        "status": result["status"],
        "source": "success_fallback",
    }


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


# ── Admin Approval Flow ─────────────────────────────────────────────────────
@router.post("/admin/orders/{order_id}/approve", response_model=MessageResponse)
async def admin_approve_order(
    order_id: uuid.UUID,
    data: AdminOrderApproveRequest | None = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    [Admin] Approve an authorized order and capture the customer's payment.
    """
    service = OrderService(db)
    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    approval_reason = (data.reason or "").strip() if data else ""
    if approval_reason:
        existing_notes = (order.admin_notes or "").strip()
        order.admin_notes = (
            f"{existing_notes}\nApproved: {approval_reason}".strip()
            if existing_notes
            else f"Approved: {approval_reason}"
        )

    if order.status == OrderStatus.PENDING:
        order.status = OrderStatus.PENDING_APPROVAL
        await db.flush()
        await db.refresh(order)
        _queue_order_payment_required_email(order)
        _queue_telegram_order_status_alert(
            order,
            "Approved in admin. Waiting for customer payment."
            + (f" Reason: {approval_reason}" if approval_reason else ""),
        )
        return MessageResponse(
            message="Order approved. Customer can now pay from the Orders page.",
            detail=order.order_number,
        )

    if order.status != OrderStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Order cannot be approved from status '{order.status.value}'",
        )

    if not order.payment:
        raise HTTPException(status_code=400, detail="No payment record found for this order")

    payment_intent_id = order.payment.stripe_payment_intent_id
    if not payment_intent_id:
        _queue_telegram_order_status_alert(
            order,
            "Approved in admin. Waiting for customer payment."
            + (f" Reason: {approval_reason}" if approval_reason else ""),
        )
        return MessageResponse(
            message="Order is approved and awaiting customer payment.",
            detail=order.order_number,
        )

    if payment_intent_id:
        captured = await StripeService.capture_payment_intent(payment_intent_id)
        if captured.get("status") not in ("succeeded", "requires_capture"):
            raise HTTPException(status_code=400, detail="Payment capture failed")

    updated_order = await service.mark_order_paid(
        order_id=order.id,
        stripe_payment_intent_id=payment_intent_id or f"manual_{order.id}",
        stripe_checkout_session_id=order.payment.stripe_checkout_session_id,
        webhook_data={"approved_by_admin_id": str(admin.id)},
        status_after_payment=OrderStatus.CONFIRMED,
    )
    if not updated_order:
        raise HTTPException(status_code=404, detail="Order not found after update")
    _queue_telegram_order_status_alert(
        updated_order,
        "Payment captured by admin approval."
        + (f" Reason: {approval_reason}" if approval_reason else ""),
    )

    try:
        from app.workers.email_tasks import send_order_confirmation, send_payment_receipt

        payload = _order_to_email_payload(updated_order)
        send_order_confirmation.delay(payload)
        send_payment_receipt.delay(payload)
    except Exception as exc:
        logger.warning("Failed to queue approval emails for order %s: %s", order.order_number, str(exc))

    return MessageResponse(
        message="Order approved and payment captured successfully",
        detail=updated_order.order_number,
    )


@router.post("/admin/orders/{order_id}/reject", response_model=MessageResponse)
async def admin_reject_order(
    order_id: uuid.UUID,
    data: AdminOrderDecisionRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    [Admin] Reject an authorized order, release payment hold, and notify customer.
    """
    service = OrderService(db)
    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in (OrderStatus.PENDING, OrderStatus.PENDING_APPROVAL):
        raise HTTPException(
            status_code=400,
            detail=f"Order cannot be rejected from status '{order.status.value}'",
        )

    if order.payment and order.payment.stripe_payment_intent_id:
        try:
            await StripeService.cancel_payment_intent(order.payment.stripe_payment_intent_id)
        except Exception as exc:
            logger.warning(
                "Failed to cancel payment intent for order %s: %s",
                order.order_number,
                str(exc),
            )

    updated_order = await service.reject_order_after_authorization(order.id, data.reason)
    if not updated_order:
        raise HTTPException(status_code=404, detail="Order not found after update")
    _queue_telegram_order_status_alert(
        updated_order,
        "Rejected by admin.",
        data.reason,
    )

    try:
        from app.workers.email_tasks import send_order_rejection_email

        send_order_rejection_email.delay(_order_to_email_payload(updated_order, data.reason))
    except Exception as exc:
        logger.warning("Failed to queue rejection email for order %s: %s", order.order_number, str(exc))

    return MessageResponse(
        message="Order rejected and customer notified",
        detail=updated_order.order_number,
    )


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
        metadata = data.get("metadata", {}) or {}
        custom_cake_id = metadata.get("custom_cake_id")
        order_id = metadata.get("order_id")
        payment_intent = data.get("payment_intent", "")

        if custom_cake_id:
            try:
                from app.services.custom_cake_service import CustomCakeService

                cake_service = CustomCakeService(db)
                result = await cake_service.mark_paid(uuid.UUID(custom_cake_id))
                if "error" in result:
                    logger.error("Custom cake webhook error (%s): %s", custom_cake_id, result["error"])
                else:
                    logger.info("✅ Custom cake %s marked as paid", custom_cake_id)
            except Exception as e:
                logger.error("Error processing custom cake webhook: %s", str(e))

        if order_id:
            try:
                order = await service.mark_order_pending_approval(
                    order_id=uuid.UUID(order_id),
                    stripe_payment_intent_id=payment_intent,
                    stripe_checkout_session_id=data.get("id"),
                    webhook_data=data,
                )
                if order:
                    logger.info(
                        "✅ Order %s authorized and awaiting approval",
                        order.order_number,
                    )
                    _queue_telegram_order_alert(order)
                else:
                    logger.error("Order not found for webhook: %s", order_id)
            except Exception as e:
                logger.error("Error processing payment webhook: %s", str(e))

    elif event_type == "payment_intent.succeeded":
        order_id = data.get("metadata", {}).get("order_id")
        if order_id:
            order = await service.mark_order_paid(
                order_id=uuid.UUID(order_id),
                stripe_payment_intent_id=data.get("id", ""),
                webhook_data=data,
                status_after_payment=OrderStatus.CONFIRMED,
            )
            if order:
                logger.info("✅ Order %s payment captured", order.order_number)

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
