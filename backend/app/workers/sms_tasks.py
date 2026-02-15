"""
SMS background tasks — Phase 7: Cake Order Alert System.
Sends instant SMS to admin on cake orders via Twilio.
"""

import logging
import os
from datetime import datetime, timezone

from app.celery_app import celery_app

logger = logging.getLogger("app.workers.sms")

# Twilio config
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")
ADMIN_PHONE_NUMBER = os.getenv("ADMIN_PHONE_NUMBER", "")


def _send_sms(to_number: str, message: str) -> bool:
    """Send SMS via Twilio. Returns True on success."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.warning("Twilio not configured — SMS to %s skipped", to_number)
        logger.info("SMS preview: %s", message)
        return False

    try:
        from twilio.rest import Client

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        result = client.messages.create(
            body=message,
            from_=TWILIO_FROM_NUMBER,
            to=to_number,
        )
        logger.info("✅ SMS sent to %s (SID: %s)", to_number, result.sid)
        return True
    except Exception as e:
        logger.error("❌ SMS send failed to %s: %s", to_number, str(e))
        raise


def _format_cake_alert(order_data: dict) -> str:
    """Format a cake order alert SMS message."""
    order_num = order_data.get("order_number", "???")
    customer = order_data.get("customer_name", "Unknown")
    total = order_data.get("total", "0.00")
    pickup = order_data.get("pickup_date", "TBD")
    cake_msg = order_data.get("cake_message", "")

    # List cake items
    cake_items = []
    for item in order_data.get("items", []):
        if item.get("is_cake"):
            name = item.get("product_name", "Cake")
            variant = f" ({item.get('variant_name')})" if item.get("variant_name") else ""
            cake_items.append(f"  • {name}{variant} x{item.get('quantity', 1)}")

    items_text = "\n".join(cake_items) if cake_items else "  • Cake order"

    message = (
        f"🎂 CAKE ORDER ALERT\n"
        f"Order: {order_num}\n"
        f"Customer: {customer}\n"
        f"Total: ${total}\n"
        f"Pickup: {pickup}\n"
        f"\nCakes:\n{items_text}"
    )

    if cake_msg:
        message += f'\n\nCake Message: "{cake_msg}"'

    return message


# ── Celery Tasks ─────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="app.workers.sms_tasks.send_cake_order_alert",
)
def send_cake_order_alert(self, order_data: dict):
    """
    🎂 PHASE 7: Instant SMS alert to admin when a cake order is paid.
    No missed cake orders!
    """
    try:
        if not ADMIN_PHONE_NUMBER:
            logger.warning("ADMIN_PHONE_NUMBER not configured — cake alert skipped")
            logger.info("Cake alert for order %s", order_data.get("order_number"))
            return

        message = _format_cake_alert(order_data)
        _send_sms(ADMIN_PHONE_NUMBER, message)

        # Also publish to Redis pub/sub for real-time admin dashboard
        _publish_cake_alert(order_data)

    except Exception as exc:
        logger.error("Cake order SMS alert failed: %s", str(exc))
        self.retry(exc=exc)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.sms_tasks.send_order_ready_sms",
)
def send_order_ready_sms(self, order_data: dict):
    """SMS notification to customer when order is ready for pickup."""
    try:
        phone = order_data.get("customer_phone")
        if not phone:
            logger.info("No phone number for customer — SMS skipped")
            return

        message = (
            f"Hi {order_data.get('customer_name', '')}! "
            f"Your Kabul Sweets order {order_data.get('order_number', '')} is ready for pickup. "
            f"Please bring your order number. See you soon! 🧁"
        )
        _send_sms(phone, message)

    except Exception as exc:
        logger.error("Order ready SMS failed: %s", str(exc))
        self.retry(exc=exc)


def _publish_cake_alert(order_data: dict):
    """Publish cake order alert to Redis pub/sub for real-time admin dashboard."""
    try:
        import json
        import redis

        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        alert_data = {
            "type": "cake_order",
            "order_number": order_data.get("order_number"),
            "customer_name": order_data.get("customer_name"),
            "total": str(order_data.get("total", "0.00")),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        r.publish("admin:cake_alerts", json.dumps(alert_data))
        logger.info("🔔 Cake alert published to Redis pub/sub")
    except Exception as e:
        logger.warning("Could not publish cake alert to Redis: %s", str(e))
