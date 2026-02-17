"""
Telegram background tasks for admin alerts and triage actions.
"""

from datetime import date, datetime
from decimal import Decimal

from app.celery_app import celery_app
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.telegram_service import TelegramService

settings = get_settings()
logger = get_logger("telegram_tasks")


def _as_money(value: str | int | float | Decimal | None) -> str:
    if value is None:
        return "$0.00"
    amount = Decimal(str(value))
    return f"${amount:.2f}"


def _format_date_only(value: str | date | datetime | None) -> str:
    if value is None:
        return "Not provided"
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    text = str(value).strip()
    if not text:
        return "Not provided"

    # Prefer YYYY-MM-DD for ISO-like date-time strings.
    if "T" in text:
        return text.split("T", 1)[0]
    if " " in text and len(text.split(" ", 1)[0]) == 10:
        return text.split(" ", 1)[0]
    return text


def _build_order_message(order_data: dict) -> str:
    pickup = order_data.get("pickup_date") or "Not provided"
    pickup_slot = order_data.get("pickup_time_slot") or "Anytime"
    cake_flag = "Yes" if order_data.get("cake_message") else "No"
    item_lines = []
    for item in order_data.get("items", [])[:8]:
        variant = f" ({item.get('variant_name')})" if item.get("variant_name") else ""
        item_lines.append(
            f"- {item.get('product_name', 'Item')}{variant} x{item.get('quantity', 1)}"
        )
    items_text = "\n".join(item_lines) if item_lines else "- No items listed"

    admin_link = f"{settings.ADMIN_FRONTEND_URL.rstrip('/')}/apps/orders"

    return (
        "🧁 <b>Order Pending Approval</b>\n"
        f"Order: <b>{order_data.get('order_number', 'N/A')}</b>\n"
        f"Customer: {order_data.get('customer_name', 'N/A')}\n"
        f"Phone: {order_data.get('customer_phone') or 'N/A'}\n"
        f"Total: <b>{_as_money(order_data.get('total'))}</b>\n"
        f"Pickup: {pickup}\n"
        f"Slot: {pickup_slot}\n"
        f"Cake message: {cake_flag}\n\n"
        f"<b>Items</b>\n{items_text}\n\n"
        f"<a href=\"{admin_link}\">Open admin orders</a>"
    )


def _build_order_status_update_message(order_data: dict) -> str:
    status_raw = str(order_data.get("status") or "unknown")
    status_label = status_raw.replace("_", " ").title()
    pickup = order_data.get("pickup_date") or "Not provided"
    pickup_slot = order_data.get("pickup_time_slot") or "Anytime"
    status_note = order_data.get("status_note")
    rejection_reason = order_data.get("rejection_reason")

    admin_link = f"{settings.ADMIN_FRONTEND_URL.rstrip('/')}/apps/orders"

    lines = [
        "📦 <b>Order Status Updated</b>",
        f"Order: <b>{order_data.get('order_number', 'N/A')}</b>",
        f"Status: <b>{status_label}</b>",
        f"Customer: {order_data.get('customer_name', 'N/A')}",
        f"Total: <b>{_as_money(order_data.get('total'))}</b>",
        f"Pickup: {pickup}",
        f"Slot: {pickup_slot}",
    ]
    if status_note:
        lines.append(f"Note: {status_note}")
    if rejection_reason:
        lines.append(f"Reason: {rejection_reason}")
    lines.append("")
    lines.append(f"<a href=\"{admin_link}\">Open admin orders</a>")
    return "\n".join(lines)


def _build_order_markup(order_id: str) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": f"order:approve:{order_id}"},
                {"text": "❌ Reject", "callback_data": f"order:reject:{order_id}"},
            ]
        ]
    }


def _build_custom_cake_message(cake_data: dict) -> str:
    requested_date = _format_date_only(cake_data.get("requested_date"))
    time_slot = cake_data.get("time_slot") or "Not provided"
    servings = cake_data.get("predicted_servings") or "N/A"
    predicted_price = _as_money(cake_data.get("predicted_price"))
    image_count = len(cake_data.get("reference_images") or [])

    admin_link = f"{settings.ADMIN_FRONTEND_URL.rstrip('/')}/apps/custom-cakes"

    return (
        "🎂 <b>Custom Cake Pending Review</b>\n"
        f"Request ID: <b>{cake_data.get('id', 'N/A')}</b>\n"
        f"Customer: {cake_data.get('customer_name', 'N/A')}\n"
        f"Contact: {cake_data.get('customer_email', 'N/A')}\n"
        f"Flavor: {cake_data.get('flavor', 'N/A')}\n"
        f"Size: {cake_data.get('diameter_inches', 'N/A')} inch\n"
        f"Servings: {servings}\n"
        f"Predicted price: <b>{predicted_price}</b>\n"
        f"Requested date: {requested_date}\n"
        f"Time slot: {time_slot}\n"
        f"Message on cake: {cake_data.get('cake_message') or 'None'}\n"
        f"Design notes: {cake_data.get('decoration_description') or 'None'}\n"
        f"Reference images: {image_count}\n\n"
        f"<a href=\"{admin_link}\">Open custom cakes in admin</a>"
    )


def _build_custom_cake_markup(cake_id: str) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": f"cake:approve:{cake_id}"},
                {"text": "❌ Reject", "callback_data": f"cake:reject:{cake_id}"},
            ],
            [
                {"text": "💵 Edit Final Price", "callback_data": f"cake:editprice:{cake_id}"},
            ],
        ]
    }


def _build_custom_cake_cancelled_message(cake_data: dict) -> str:
    requested_date = _format_date_only(cake_data.get("requested_date"))
    time_slot = cake_data.get("time_slot") or "Not provided"
    predicted_price = _as_money(cake_data.get("predicted_price"))
    final_price = _as_money(cake_data.get("final_price"))
    image_count = len(cake_data.get("reference_images") or [])

    admin_link = f"{settings.ADMIN_FRONTEND_URL.rstrip('/')}/apps/custom-cakes"

    return (
        "🗑️ <b>Custom Cake Deleted By Customer</b>\n"
        f"Request ID: <b>{cake_data.get('id', 'N/A')}</b>\n"
        f"Customer: {cake_data.get('customer_name', 'N/A')}\n"
        f"Contact: {cake_data.get('customer_email', 'N/A')}\n"
        f"Flavor: {cake_data.get('flavor', 'N/A')}\n"
        f"Size: {cake_data.get('diameter_inches', 'N/A')} inch\n"
        f"Predicted price: {predicted_price}\n"
        f"Final price: {final_price}\n"
        f"Requested date: {requested_date}\n"
        f"Time slot: {time_slot}\n"
        f"Reason: {cake_data.get('reason') or 'Not provided'}\n"
        f"Reference images: {image_count}\n\n"
        f"<a href=\"{admin_link}\">Open custom cakes in admin</a>"
    )


def _send_reference_image_if_possible(
    telegram: TelegramService,
    chat_id: int,
    reference_images: list | None,
) -> bool:
    if not reference_images:
        return False

    first = reference_images[0]
    if not isinstance(first, str) or not first.strip():
        return False

    if first.startswith("http://") or first.startswith("https://"):
        return telegram.send_photo_url(
            chat_id,
            first,
            caption="Reference cake image",
        )

    if first.startswith("data:image/"):
        return telegram.send_photo_data_url(
            chat_id,
            first,
            caption="Reference cake image",
        )

    return False


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name="app.workers.telegram_tasks.send_admin_order_pending_alert",
)
def send_admin_order_pending_alert(self, order_data: dict):
    """Send order pending-approval alert with Telegram action buttons."""
    telegram = TelegramService()
    if not telegram.is_configured():
        logger.info("Telegram not configured — order alert skipped")
        return

    order_id = order_data.get("order_id")
    if not order_id:
        logger.warning("Order alert missing order_id, skipping")
        return

    text = _build_order_message(order_data)
    markup = _build_order_markup(str(order_id))

    for chat_id in telegram.admin_chat_ids:
        telegram.send_text(chat_id, text, reply_markup=markup)


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name="app.workers.telegram_tasks.send_admin_order_status_alert",
)
def send_admin_order_status_alert(self, order_data: dict):
    """Send status update alert when order state changes in admin tools."""
    telegram = TelegramService()
    if not telegram.is_configured():
        logger.info("Telegram not configured — order status alert skipped")
        return

    text = _build_order_status_update_message(order_data)
    for chat_id in telegram.admin_chat_ids:
        telegram.send_text(chat_id, text)


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name="app.workers.telegram_tasks.send_admin_custom_cake_pending_alert",
)
def send_admin_custom_cake_pending_alert(self, cake_data: dict):
    """Send custom cake review alert (with image preview if available)."""
    telegram = TelegramService()
    if not telegram.is_configured():
        logger.info("Telegram not configured — custom cake alert skipped")
        return

    cake_id = cake_data.get("id")
    if not cake_id:
        logger.warning("Custom cake alert missing id, skipping")
        return

    text = _build_custom_cake_message(cake_data)
    markup = _build_custom_cake_markup(str(cake_id))
    images = cake_data.get("reference_images") or []

    for chat_id in telegram.admin_chat_ids:
        telegram.send_text(chat_id, text, reply_markup=markup)
        _send_reference_image_if_possible(telegram, chat_id, images)


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name="app.workers.telegram_tasks.send_admin_custom_cake_cancelled_alert",
)
def send_admin_custom_cake_cancelled_alert(self, cake_data: dict):
    """Send admin alert when customer deletes/cancels a custom cake request."""
    telegram = TelegramService()
    if not telegram.is_configured():
        logger.info("Telegram not configured — custom cake cancel alert skipped")
        return

    cake_id = cake_data.get("id")
    if not cake_id:
        logger.warning("Custom cake cancel alert missing id, skipping")
        return

    text = _build_custom_cake_cancelled_message(cake_data)
    images = cake_data.get("reference_images") or []

    for chat_id in telegram.admin_chat_ids:
        telegram.send_text(chat_id, text)
        _send_reference_image_if_possible(telegram, chat_id, images)
