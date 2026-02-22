"""
Stripe payment service — handles Checkout Sessions and webhooks.
"""

import os
from decimal import Decimal
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.core.logging import get_logger

logger = get_logger("stripe_service")

# Stripe will be imported conditionally (not required for dev without Stripe)
try:
    import stripe

    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_AVAILABLE = bool(stripe.api_key)
except ImportError:
    STRIPE_AVAILABLE = False
    logger.warning("stripe package not installed — payments will be in test mode")

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "").rstrip("/")
STRIPE_SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL", "").strip()
STRIPE_CANCEL_URL = os.getenv("STRIPE_CANCEL_URL", "").strip()


def _strip_www(hostname: str) -> str:
    return hostname[4:] if hostname.startswith("www.") else hostname


def _canonical_frontend_base() -> str:
    if not FRONTEND_URL:
        return ""

    parsed = urlparse(FRONTEND_URL)
    if not parsed.scheme or not parsed.netloc:
        return FRONTEND_URL.rstrip("/")

    host = _strip_www((parsed.hostname or "").strip())
    if not host:
        return FRONTEND_URL.rstrip("/")

    netloc = f"{host}:{parsed.port}" if parsed.port else host
    return urlunparse(parsed._replace(netloc=netloc, path="", params="", query="", fragment="")).rstrip("/")


def _canonicalize_checkout_url(url: str, canonical_frontend: str) -> str:
    raw = (url or "").strip()
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return raw

    if canonical_frontend:
        frontend = urlparse(canonical_frontend)
        if frontend.scheme and frontend.netloc:
            normalized = urlunparse(parsed._replace(scheme=frontend.scheme, netloc=frontend.netloc))
            if normalized != raw:
                logger.info(
                    "Normalized Stripe redirect URL host from %s to %s",
                    parsed.netloc,
                    frontend.netloc,
                )
            return normalized

    host = _strip_www(parsed.hostname or "")
    if not host:
        return raw
    netloc = f"{host}:{parsed.port}" if parsed.port else host
    normalized = urlunparse(parsed._replace(netloc=netloc))
    if normalized != raw:
        logger.info(
            "Normalized Stripe redirect URL host from %s to %s",
            parsed.netloc,
            netloc,
        )
    return normalized


def _resolve_checkout_urls(
    success_url: str | None = None,
    cancel_url: str | None = None,
) -> tuple[str, str]:
    canonical_frontend = _canonical_frontend_base()
    resolved_success = success_url or STRIPE_SUCCESS_URL
    resolved_cancel = cancel_url or STRIPE_CANCEL_URL

    if not resolved_success and canonical_frontend:
        resolved_success = f"{canonical_frontend}/order/success?session_id={{CHECKOUT_SESSION_ID}}"
    if not resolved_cancel and canonical_frontend:
        resolved_cancel = f"{canonical_frontend}/order/cancel"

    if not resolved_success or not resolved_cancel:
        raise ValueError(
            "Stripe checkout URLs are not configured. "
            "Set STRIPE_SUCCESS_URL/STRIPE_CANCEL_URL or FRONTEND_URL."
        )

    resolved_success = _canonicalize_checkout_url(resolved_success, canonical_frontend)
    resolved_cancel = _canonicalize_checkout_url(resolved_cancel, canonical_frontend)

    return resolved_success, resolved_cancel


def _append_query_params(url: str, extra_params: dict[str, str]) -> str:
    """Append query params while preserving existing placeholders."""
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update(extra_params)
    # Keep Stripe placeholder braces unescaped so Stripe can inject session IDs.
    return urlunparse(parsed._replace(query=urlencode(query, safe="{}")))


def _replace_checkout_session_placeholder(url: str, replacement: str) -> str:
    return (
        url.replace("{CHECKOUT_SESSION_ID}", replacement)
        .replace("%7BCHECKOUT_SESSION_ID%7D", replacement)
        .replace("%7bCHECKOUT_SESSION_ID%7d", replacement)
    )


class StripeService:
    """Handles Stripe Checkout Session creation and webhook verification."""

    @staticmethod
    async def create_checkout_session(
        order_id: str,
        order_number: str,
        amount: Decimal,
        currency: str = "aud",
        customer_email: str | None = None,
        authorize_only: bool = False,
        success_url: str | None = None,
        cancel_url: str | None = None,
        line_items_description: str = "Kabul Sweets Order",
    ) -> dict:
        """
        Create a Stripe Checkout Session.
        Returns checkout URL, session ID, and payment intent ID.
        """
        resolved_success_url, resolved_cancel_url = _resolve_checkout_urls(
            success_url=success_url,
            cancel_url=cancel_url,
        )

        if not STRIPE_AVAILABLE:
            logger.warning("Stripe not configured — returning test checkout session")
            return {
                "checkout_url": _replace_checkout_session_placeholder(
                    resolved_success_url,
                    f"test_session_{order_id}",
                ),
                "session_id": f"test_session_{order_id}",
                "payment_intent_id": f"test_intent_{order_id}",
            }

        payment_intent_data = {
            "capture_method": "manual" if authorize_only else "automatic",
            "metadata": {
                "order_id": order_id,
                "order_number": order_number,
            },
        }

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            customer_email=customer_email,
            line_items=[
                {
                    "price_data": {
                        "currency": currency,
                        "product_data": {
                            "name": f"Order {order_number}",
                            "description": line_items_description,
                        },
                        "unit_amount": int(amount * 100),
                    },
                    "quantity": 1,
                },
            ],
            metadata={
                "order_id": order_id,
                "order_number": order_number,
            },
            payment_intent_data=payment_intent_data,
            success_url=resolved_success_url,
            cancel_url=resolved_cancel_url,
        )

        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "payment_intent_id": session.payment_intent,
        }

    @staticmethod
    async def capture_payment_intent(payment_intent_id: str) -> dict:
        """Capture a previously authorized payment intent."""
        if not STRIPE_AVAILABLE:
            logger.warning("Stripe not configured — simulating payment capture")
            return {"id": payment_intent_id, "status": "succeeded"}

        intent = stripe.PaymentIntent.capture(payment_intent_id)
        return {"id": intent.id, "status": intent.status}

    @staticmethod
    async def cancel_payment_intent(payment_intent_id: str) -> dict:
        """Cancel an authorized payment intent."""
        if not STRIPE_AVAILABLE:
            logger.warning("Stripe not configured — simulating payment cancellation")
            return {"id": payment_intent_id, "status": "canceled"}

        intent = stripe.PaymentIntent.cancel(payment_intent_id)
        return {"id": intent.id, "status": intent.status}

    @staticmethod
    async def create_payment_link(
        custom_cake_id: str,
        description: str,
        amount: Decimal,
        currency: str = "aud",
        customer_email: str | None = None,
    ) -> dict:
        """
        Create a Stripe Checkout Session for a custom cake payment.
        Returns checkout URL so the customer can pay.
        """
        if not STRIPE_AVAILABLE:
            logger.warning("Stripe not configured — returning test payment link")
            success_url, _ = _resolve_checkout_urls()
            success_url = _append_query_params(
                success_url,
                {"payment_type": "custom_cake", "custom_cake_id": custom_cake_id},
            )
            return {
                "checkout_url": _replace_checkout_session_placeholder(
                    success_url,
                    f"test_cake_{custom_cake_id}",
                ),
                "session_id": f"test_cake_{custom_cake_id}",
            }

        success_url, cancel_url = _resolve_checkout_urls()
        success_url = _append_query_params(
            success_url,
            {"payment_type": "custom_cake", "custom_cake_id": custom_cake_id},
        )
        cancel_url = _append_query_params(
            cancel_url,
            {"payment_type": "custom_cake", "custom_cake_id": custom_cake_id},
        )

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            customer_email=customer_email,
            line_items=[
                {
                    "price_data": {
                        "currency": currency,
                        "product_data": {
                            "name": "Custom Cake",
                            "description": description,
                        },
                        "unit_amount": int(amount * 100),
                    },
                    "quantity": 1,
                },
            ],
            metadata={
                "custom_cake_id": custom_cake_id,
                "type": "custom_cake",
            },
            success_url=success_url,
            cancel_url=cancel_url,
        )

        return {
            "checkout_url": session.url,
            "session_id": session.id,
        }

    @staticmethod
    def verify_webhook_signature(payload: bytes, sig_header: str) -> dict | None:
        """
        Verify a Stripe webhook signature and return the event.
        Returns None if verification fails.
        """
        if not STRIPE_AVAILABLE:
            logger.warning("Stripe not configured — cannot verify webhook")
            return None

        if not STRIPE_WEBHOOK_SECRET:
            logger.error("STRIPE_WEBHOOK_SECRET not configured")
            return None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
            return event
        except stripe.error.SignatureVerificationError as e:
            logger.error("Webhook signature verification failed: %s", str(e))
            return None
        except Exception as e:
            logger.error("Webhook processing error: %s", str(e))
            return None

    @staticmethod
    async def retrieve_checkout_session(session_id: str) -> dict:
        """Retrieve a Checkout Session by ID."""
        if not STRIPE_AVAILABLE:
            if session_id.startswith("test_"):
                return {
                    "id": session_id,
                    "status": "complete",
                    "payment_status": "paid",
                    "metadata": {},
                }
            raise ValueError("Stripe is not configured")

        session = stripe.checkout.Session.retrieve(session_id)
        return {
            "id": session.id,
            "status": getattr(session, "status", None),
            "payment_status": getattr(session, "payment_status", None),
            "metadata": dict(getattr(session, "metadata", {}) or {}),
            "customer_email": getattr(session, "customer_email", None),
        }
