"""
Stripe payment service — handles Checkout Sessions and webhooks.
"""

import os
from decimal import Decimal

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


class StripeService:
    """Handles Stripe Checkout Session creation and webhook verification."""

    @staticmethod
    async def create_checkout_session(
        order_id: str,
        order_number: str,
        amount: Decimal,
        currency: str = "aud",
        customer_email: str | None = None,
        success_url: str = "http://localhost:3000/order/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url: str = "http://localhost:3000/order/cancel",
        line_items_description: str = "Kabul Sweets Order",
    ) -> dict:
        """
        Create a Stripe Checkout Session.
        Returns checkout URL and session ID.
        """
        if not STRIPE_AVAILABLE:
            # Test mode — return a fake session
            logger.warning("Stripe not configured — returning test checkout session")
            return {
                "checkout_url": f"{success_url.replace('{CHECKOUT_SESSION_ID}', 'test_session_' + order_id)}",
                "session_id": f"test_session_{order_id}",
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
                        "unit_amount": int(amount * 100),  # Stripe uses cents
                    },
                    "quantity": 1,
                },
            ],
            payment_intent_data={
                "capture_method": "manual",  # Require admin approval before charging
            },
            metadata={
                "order_id": order_id,
                "order_number": order_number,
            },
            success_url=success_url,
            cancel_url=cancel_url,
        )

        return {
            "checkout_url": session.url,
            "session_id": session.id,
        }

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
            return {
                "checkout_url": f"http://localhost:3000/order/success?session_id=test_cake_{custom_cake_id}",
                "session_id": f"test_cake_{custom_cake_id}",
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
            success_url="http://localhost:3000/order/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="http://localhost:3000/order/cancel",
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
    async def capture_payment(payment_intent_id: str) -> bool:
        """Capture a previously authorized payment."""
        if not STRIPE_AVAILABLE:
            logger.info("Test mode: Captured payment %s", payment_intent_id)
            return True

        try:
            stripe.PaymentIntent.capture(payment_intent_id)
            return True
        except stripe.error.StripeError as e:
            logger.error("Failed to capture payment %s: %s", payment_intent_id, str(e))
            return False

    @staticmethod
    async def cancel_payment_intent(payment_intent_id: str) -> bool:
        """Cancel a payment intent (release authorization)."""
        if not STRIPE_AVAILABLE:
            logger.info("Test mode: Cancelled payment %s", payment_intent_id)
            return True

        try:
            stripe.PaymentIntent.cancel(payment_intent_id)
            return True
        except stripe.error.StripeError as e:
            logger.error("Failed to cancel payment %s: %s", payment_intent_id, str(e))
            return False
