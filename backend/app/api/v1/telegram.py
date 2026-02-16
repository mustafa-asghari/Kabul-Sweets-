"""
Telegram bot webhook endpoints for admin workflows.
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.ml import CustomCake, CustomCakeStatus
from app.models.order import Order, OrderStatus
from app.models.user import User, UserRole
from app.services.custom_cake_service import CustomCakeService
from app.services.order_service import OrderService
from app.services.stripe_service import StripeService
from app.services.telegram_service import TelegramService

router = APIRouter(prefix="/telegram", tags=["Telegram"])
settings = get_settings()
logger = get_logger("telegram_webhook")

ORDER_REJECT_REASON = "Rejected from Telegram by admin."
CAKE_REJECT_REASON = "Rejected from Telegram by admin."
APPROVED_FROM_TELEGRAM_NOTE = "Approved via Telegram bot."
MAX_TELEGRAM_LIST_LIMIT = 20
DEFAULT_PENDING_LIMIT = 10
DEFAULT_DAY_LIMIT = 20
QUICK_LIMIT_OPTIONS = (5, 10, 20)
MAX_RANGE_RESULTS = 100
INCOMING_MAX_DAYS = 30
DATE_PICKER_MIN_OFFSET = -180
DATE_PICKER_MAX_OFFSET = 180
DATE_PICKER_PAGE_SIZE = 7
CAKE_STATUS_PARAM_MAP: dict[str, CustomCakeStatus | None] = {
    "all": None,
    "pending_review": CustomCakeStatus.PENDING_REVIEW,
    "approved_awaiting_payment": CustomCakeStatus.APPROVED_AWAITING_PAYMENT,
    "paid": CustomCakeStatus.PAID,
    "in_production": CustomCakeStatus.IN_PRODUCTION,
    "completed": CustomCakeStatus.COMPLETED,
    "rejected": CustomCakeStatus.REJECTED,
    "cancelled": CustomCakeStatus.CANCELLED,
}
CAKE_STATUS_OPTIONS: tuple[tuple[str, str], ...] = (
    ("All", "all"),
    ("Pending Review", "pending_review"),
    ("Approved Awaiting Payment", "approved_awaiting_payment"),
    ("Paid", "paid"),
    ("In Production", "in_production"),
    ("Completed", "completed"),
    ("Rejected", "rejected"),
    ("Cancelled", "cancelled"),
)


def _as_money(value: Decimal | int | float | str | None) -> str:
    if value is None:
        return "$0.00"
    amount = Decimal(str(value))
    return f"${amount:.2f}"


def _extract_command(text: str) -> str:
    raw = text.strip().split(" ", 1)[0]
    return raw.split("@", 1)[0].lower()


def _is_authorized_chat(chat_id: int | None) -> bool:
    if chat_id is None:
        return False
    return chat_id in settings.TELEGRAM_ADMIN_CHAT_IDS


def _order_markup(order_id: uuid.UUID) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": f"order:approve:{order_id}"},
                {"text": "❌ Reject", "callback_data": f"order:reject:{order_id}"},
            ]
        ]
    }


def _cake_markup(cake_id: uuid.UUID) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": f"cake:approve:{cake_id}"},
                {"text": "❌ Reject", "callback_data": f"cake:reject:{cake_id}"},
            ]
        ]
    }


def _command_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "📦 Pending Orders", "callback_data": "cmd:pending_orders"},
                {"text": "🎂 Pending Cakes", "callback_data": "cmd:pending_cakes"},
            ],
            [
                {"text": "📥 Incoming 7 Days", "callback_data": "cmd:incoming7"},
                {"text": "📦🎂 Incoming 30 Days", "callback_data": "cmd:incoming30"},
            ],
            [
                {"text": "📆 Orders by Day", "callback_data": "cmd:orders_day"},
                {"text": "🎂 Cakes by Day", "callback_data": "cmd:cakes_day"},
            ],
            [
                {"text": "🗓️ Orders Date Range", "callback_data": "cmd:orders_range"},
                {"text": "🧁 Cakes Date Range", "callback_data": "cmd:cakes_range"},
            ],
            [
                {"text": "📘 Parameters", "callback_data": "cmd:params"},
            ],
        ]
    }


def _limit_option_keyboard(action_prefix: str, back_callback: str | None = None) -> dict:
    rows: list[list[dict]] = [
        [
            {
                "text": str(limit),
                "callback_data": f"{action_prefix}:{limit}",
            }
            for limit in QUICK_LIMIT_OPTIONS
        ]
    ]
    if back_callback:
        rows.append([{"text": "⬅️ Back", "callback_data": back_callback}])
    return {"inline_keyboard": rows}


def _day_status_keyboard(day_prefix: str) -> dict:
    status_action = "tds" if day_prefix == "td" else "tms"
    buttons = [
        {
            "text": label,
            "callback_data": f"{status_action}:{status_key}",
        }
        for label, status_key in CAKE_STATUS_OPTIONS
    ]
    rows: list[list[dict]] = []
    for index in range(0, len(buttons), 2):
        rows.append(buttons[index:index + 2])
    rows.append([{"text": "⬅️ Back", "callback_data": "cmd:help"}])
    return {"inline_keyboard": rows}


def _day_limit_keyboard(day_prefix: str, status_key: str) -> dict:
    back_callback = "cmd:today" if day_prefix == "td" else "cmd:tomorrow"
    rows: list[list[dict]] = [
        [
            {
                "text": str(limit),
                "callback_data": f"{day_prefix}:{status_key}:{limit}",
            }
            for limit in QUICK_LIMIT_OPTIONS
        ],
        [{"text": "⬅️ Back to status", "callback_data": back_callback}],
    ]
    return {"inline_keyboard": rows}


def _status_label(status_key: str) -> str:
    for label, key in CAKE_STATUS_OPTIONS:
        if key == status_key:
            return label
    return status_key


def _today_local_date() -> date:
    return datetime.now(_business_timezone()).date()


def _date_for_offset(offset: int) -> date:
    return _today_local_date() + timedelta(days=offset)


def _offset_to_utc_range(offset: int) -> tuple[datetime, datetime, date]:
    tz = _business_timezone()
    target_date = _date_for_offset(offset)
    start_local = datetime.combine(target_date, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc), target_date


def _offset_span_to_utc_range(start_offset: int, end_offset: int) -> tuple[datetime, datetime, date, date]:
    tz = _business_timezone()
    start_date = _date_for_offset(start_offset)
    end_date = _date_for_offset(end_offset)
    start_local = datetime.combine(start_date, time.min, tzinfo=tz)
    end_local = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=tz)
    return (
        start_local.astimezone(timezone.utc),
        end_local.astimezone(timezone.utc),
        start_date,
        end_date,
    )


def _parse_picker_value(raw: str, *, min_value: int, max_value: int) -> int | None:
    try:
        value = int(raw)
    except ValueError:
        return None
    if value < min_value or value > max_value:
        return None
    return value


def _picker_page_for_offset(
    *,
    offset: int = 0,
    min_offset: int = DATE_PICKER_MIN_OFFSET,
    max_offset: int = DATE_PICKER_MAX_OFFSET,
) -> int:
    total = max_offset - min_offset + 1
    max_page = max((total - 1) // DATE_PICKER_PAGE_SIZE, 0)
    page = (offset - min_offset) // DATE_PICKER_PAGE_SIZE
    return max(0, min(page, max_page))


def _date_picker_keyboard(
    *,
    select_prefix: str,
    page_prefix: str,
    page: int,
    min_offset: int = DATE_PICKER_MIN_OFFSET,
    max_offset: int = DATE_PICKER_MAX_OFFSET,
    back_callback: str = "cmd:help",
) -> dict:
    total = max_offset - min_offset + 1
    max_page = max((total - 1) // DATE_PICKER_PAGE_SIZE, 0)
    safe_page = max(0, min(page, max_page))
    start_offset = min_offset + (safe_page * DATE_PICKER_PAGE_SIZE)
    end_offset = min(start_offset + DATE_PICKER_PAGE_SIZE - 1, max_offset)

    rows: list[list[dict]] = []
    day_buttons: list[dict] = []
    for offset in range(start_offset, end_offset + 1):
        label = _date_for_offset(offset).strftime("%a %d %b")
        day_buttons.append(
            {"text": label, "callback_data": f"{select_prefix}:{offset}"}
        )

    for index in range(0, len(day_buttons), 2):
        rows.append(day_buttons[index:index + 2])

    nav_row: list[dict] = []
    if safe_page > 0:
        nav_row.append(
            {"text": "⬅️ Prev", "callback_data": f"{page_prefix}:{safe_page - 1}"}
        )
    if safe_page < max_page:
        nav_row.append(
            {"text": "Next ➡️", "callback_data": f"{page_prefix}:{safe_page + 1}"}
        )
    if nav_row:
        rows.append(nav_row)

    rows.append([{"text": "⬅️ Back", "callback_data": back_callback}])
    return {"inline_keyboard": rows}


def _range_end_picker_keyboard(
    *,
    select_prefix: str,
    page_prefix: str,
    start_offset: int,
    page: int,
    back_callback: str,
) -> dict:
    min_offset = start_offset
    max_offset = DATE_PICKER_MAX_OFFSET
    total = max_offset - min_offset + 1
    max_page = max((total - 1) // DATE_PICKER_PAGE_SIZE, 0)
    safe_page = max(0, min(page, max_page))
    from_offset = min_offset + (safe_page * DATE_PICKER_PAGE_SIZE)
    to_offset = min(from_offset + DATE_PICKER_PAGE_SIZE - 1, max_offset)

    rows: list[list[dict]] = []
    end_buttons: list[dict] = []
    for end_offset in range(from_offset, to_offset + 1):
        label = _date_for_offset(end_offset).strftime("%a %d %b")
        end_buttons.append(
            {
                "text": label,
                "callback_data": f"{select_prefix}:{start_offset}:{end_offset}",
            }
        )

    for index in range(0, len(end_buttons), 2):
        rows.append(end_buttons[index:index + 2])

    nav_row: list[dict] = []
    if safe_page > 0:
        nav_row.append(
            {
                "text": "⬅️ Prev",
                "callback_data": f"{page_prefix}:{start_offset}:{safe_page - 1}",
            }
        )
    if safe_page < max_page:
        nav_row.append(
            {
                "text": "Next ➡️",
                "callback_data": f"{page_prefix}:{start_offset}:{safe_page + 1}",
            }
        )
    if nav_row:
        rows.append(nav_row)

    rows.append([{"text": "⬅️ Back to start date", "callback_data": back_callback}])
    return {"inline_keyboard": rows}


def _bot_help_message() -> str:
    return (
        "🤖 <b>Kabul Sweets Admin Bot</b>\n"
        "New orders and custom cake requests are sent automatically.\n"
        "Use buttons below for date pickers and quick ranges.\n\n"
        "<b>Commands</b>\n"
        "/pending_orders [limit]\n"
        "/pending_cakes [limit]\n"
        "/today [status] [limit]\n"
        "/tomorrow [status] [limit]\n"
        "/incoming7\n"
        "/incoming30\n"
        "/orders_day\n"
        "/cakes_day\n"
        "/orders_range\n"
        "/cakes_range\n"
        "/params\n"
        "/help\n"
    )


def _bot_params_message() -> str:
    allowed_statuses = ", ".join(CAKE_STATUS_PARAM_MAP.keys())
    return (
        "📘 <b>Allowed Parameters</b>\n\n"
        "You can tap buttons for all parameters.\n\n"
        "<b>/pending_orders [limit]</b>\n"
        f"- <code>limit</code>: 1-{MAX_TELEGRAM_LIST_LIMIT}, default {DEFAULT_PENDING_LIMIT}\n\n"
        "<b>/pending_cakes [limit]</b>\n"
        f"- <code>limit</code>: 1-{MAX_TELEGRAM_LIST_LIMIT}, default {DEFAULT_PENDING_LIMIT}\n\n"
        "<b>/today [status] [limit]</b>\n"
        "<b>/tomorrow [status] [limit]</b>\n"
        f"- <code>status</code>: {allowed_statuses}\n"
        f"- <code>limit</code>: 1-{MAX_TELEGRAM_LIST_LIMIT}, default {DEFAULT_DAY_LIMIT}\n\n"
        "<b>Examples</b>\n"
        "<code>/pending_orders 5</code>\n"
        "<code>/pending_cakes 3</code>\n"
        "<code>/today pending_review 10</code>\n"
        "<code>/tomorrow all 20</code>\n"
        "<code>/incoming7</code>\n"
        "<code>/orders_day</code>\n"
        "<code>/orders_range</code>"
    )


def _parse_limit_arg(raw: str | None, default: int) -> tuple[int | None, str | None]:
    if raw is None:
        return default, None

    try:
        value = int(raw)
    except ValueError:
        return None, "Limit must be a number."

    if value < 1 or value > MAX_TELEGRAM_LIST_LIMIT:
        return (
            None,
            f"Limit must be between 1 and {MAX_TELEGRAM_LIST_LIMIT}.",
        )
    return value, None


def _parse_day_command_args(
    args: list[str],
) -> tuple[CustomCakeStatus | None, int, str | None]:
    status_filter: CustomCakeStatus | None = None
    limit = DEFAULT_DAY_LIMIT

    if not args:
        return status_filter, limit, None

    if len(args) == 1:
        token = args[0].lower()
        if token in CAKE_STATUS_PARAM_MAP:
            status_filter = CAKE_STATUS_PARAM_MAP[token]
            return status_filter, limit, None

        parsed_limit, err = _parse_limit_arg(token, DEFAULT_DAY_LIMIT)
        if err:
            return None, DEFAULT_DAY_LIMIT, (
                f"Invalid parameter. Use /params for help.\n{err}"
            )
        return status_filter, parsed_limit or DEFAULT_DAY_LIMIT, None

    if len(args) == 2:
        status_token = args[0].lower()
        if status_token not in CAKE_STATUS_PARAM_MAP:
            allowed_statuses = ", ".join(CAKE_STATUS_PARAM_MAP.keys())
            return (
                None,
                DEFAULT_DAY_LIMIT,
                f"Invalid status. Allowed: {allowed_statuses}",
            )

        parsed_limit, err = _parse_limit_arg(args[1], DEFAULT_DAY_LIMIT)
        if err:
            return None, DEFAULT_DAY_LIMIT, err

        status_filter = CAKE_STATUS_PARAM_MAP[status_token]
        return status_filter, parsed_limit or DEFAULT_DAY_LIMIT, None

    return None, DEFAULT_DAY_LIMIT, "Too many parameters. Use /params for help."


def _order_message(order) -> str:
    item_lines = []
    for item in order.items[:8]:
        variant = f" ({item.variant_name})" if item.variant_name else ""
        item_lines.append(f"- {item.product_name}{variant} x{item.quantity}")
    if not item_lines:
        item_lines.append("- No items listed")

    pickup = order.pickup_date.isoformat() if order.pickup_date else "Not provided"
    slot = order.pickup_time_slot or "Anytime"
    admin_link = f"{settings.ADMIN_FRONTEND_URL.rstrip('/')}/apps/orders"

    return (
        "🧁 <b>Order</b>\n"
        f"Order: <b>{order.order_number}</b>\n"
        f"Customer: {order.customer_name}\n"
        f"Phone: {order.customer_phone or 'N/A'}\n"
        f"Total: <b>{_as_money(order.total)}</b>\n"
        f"Pickup: {pickup}\n"
        f"Slot: {slot}\n"
        f"Status: {order.status.value}\n\n"
        f"<b>Items</b>\n" + "\n".join(item_lines) + "\n\n"
        f"<a href=\"{admin_link}\">Open admin orders</a>"
    )


def _cake_message(cake: CustomCake, customer_name: str, customer_email: str) -> str:
    requested_date = cake.requested_date.isoformat() if cake.requested_date else "Not provided"
    admin_link = f"{settings.ADMIN_FRONTEND_URL.rstrip('/')}/apps/custom-cakes"

    return (
        "🎂 <b>Custom Cake</b>\n"
        f"ID: <b>{cake.id}</b>\n"
        f"Customer: {customer_name}\n"
        f"Contact: {customer_email}\n"
        f"Status: {cake.status.value}\n"
        f"Flavor: {cake.flavor}\n"
        f"Size: {cake.diameter_inches} inch\n"
        f"Servings: {cake.predicted_servings or 'N/A'}\n"
        f"Predicted price: {_as_money(cake.predicted_price)}\n"
        f"Final price: {_as_money(cake.final_price)}\n"
        f"Requested date: {requested_date}\n"
        f"Time slot: {cake.time_slot or 'Not provided'}\n"
        f"Cake message: {cake.cake_message or 'None'}\n"
        f"Design notes: {cake.decoration_description or 'None'}\n"
        f"Images: {len(cake.reference_images or [])}\n\n"
        f"<a href=\"{admin_link}\">Open custom cakes in admin</a>"
    )


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


def _business_timezone():
    try:
        return ZoneInfo(settings.BUSINESS_TIMEZONE)
    except ZoneInfoNotFoundError:
        return timezone.utc


def _date_range_utc(day_offset: int) -> tuple[datetime, datetime, datetime.date]:
    tz = _business_timezone()
    today = datetime.now(tz).date()
    target_date = today + timedelta(days=day_offset)
    start_local = datetime.combine(target_date, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc), target_date


async def _handle_orders_in_range_command(
    telegram: TelegramService,
    chat_id: int,
    db: AsyncSession,
    *,
    start_utc: datetime,
    end_utc: datetime,
    start_date: date,
    end_date: date,
):
    result = await db.execute(
        select(Order)
        .where(
            Order.pickup_date.is_not(None),
            Order.pickup_date >= start_utc,
            Order.pickup_date < end_utc,
            Order.status != OrderStatus.DRAFT,
        )
        .order_by(Order.pickup_date.asc(), Order.created_at.asc())
        .limit(MAX_RANGE_RESULTS)
    )
    orders = list(result.scalars().all())

    if not orders:
        await _send_text(
            telegram,
            chat_id,
            f"No orders scheduled between {start_date.isoformat()} and {end_date.isoformat()}.",
        )
        return

    truncated = len(orders) >= MAX_RANGE_RESULTS
    header = (
        f"📦 Orders from {start_date.isoformat()} to {end_date.isoformat()}: {len(orders)}"
        + (" (showing first 100)" if truncated else "")
    )
    await _send_text(telegram, chat_id, header)

    for order in orders:
        markup = _order_markup(order.id) if order.status == OrderStatus.PENDING_APPROVAL else None
        await _send_text(telegram, chat_id, _order_message(order), markup)


async def _handle_cakes_in_range_command(
    telegram: TelegramService,
    chat_id: int,
    db: AsyncSession,
    *,
    start_utc: datetime,
    end_utc: datetime,
    start_date: date,
    end_date: date,
):
    result = await db.execute(
        select(CustomCake)
        .where(
            CustomCake.requested_date.is_not(None),
            CustomCake.requested_date >= start_utc,
            CustomCake.requested_date < end_utc,
        )
        .order_by(CustomCake.requested_date.asc(), CustomCake.created_at.asc())
        .limit(MAX_RANGE_RESULTS)
    )
    cakes = list(result.scalars().all())

    if not cakes:
        await _send_text(
            telegram,
            chat_id,
            f"No custom cakes scheduled between {start_date.isoformat()} and {end_date.isoformat()}.",
        )
        return

    customer_map = await _load_customer_map(db, {cake.customer_id for cake in cakes})
    truncated = len(cakes) >= MAX_RANGE_RESULTS
    header = (
        f"🎂 Cakes from {start_date.isoformat()} to {end_date.isoformat()}: {len(cakes)}"
        + (" (showing first 100)" if truncated else "")
    )
    await _send_text(telegram, chat_id, header)

    for cake in cakes:
        customer_name, customer_email = customer_map.get(
            cake.customer_id,
            ("Unknown customer", "Unknown email"),
        )
        markup = _cake_markup(cake.id) if cake.status == CustomCakeStatus.PENDING_REVIEW else None
        await _send_text(
            telegram,
            chat_id,
            _cake_message(cake, customer_name, customer_email),
            markup,
        )
        await _send_first_reference_image(telegram, chat_id, cake.reference_images)


async def _handle_incoming_window_command(
    telegram: TelegramService,
    chat_id: int,
    db: AsyncSession,
    *,
    days: int,
):
    if days < 1:
        days = 1
    end_offset = min(days - 1, INCOMING_MAX_DAYS - 1)
    start_utc, end_utc, start_date, end_date = _offset_span_to_utc_range(0, end_offset)
    await _send_text(
        telegram,
        chat_id,
        f"📥 Incoming window: {start_date.isoformat()} to {end_date.isoformat()}",
    )
    await _handle_orders_in_range_command(
        telegram,
        chat_id,
        db,
        start_utc=start_utc,
        end_utc=end_utc,
        start_date=start_date,
        end_date=end_date,
    )
    await _handle_cakes_in_range_command(
        telegram,
        chat_id,
        db,
        start_utc=start_utc,
        end_utc=end_utc,
        start_date=start_date,
        end_date=end_date,
    )


async def _send_text(
    telegram: TelegramService,
    chat_id: int,
    text: str,
    reply_markup: dict | None = None,
):
    await run_in_threadpool(
        telegram.send_text,
        chat_id,
        text,
        reply_markup=reply_markup,
    )


async def _answer_callback(telegram: TelegramService, callback_id: str, text: str):
    await run_in_threadpool(telegram.answer_callback_query, callback_id, text[:180])


async def _clear_buttons(telegram: TelegramService, chat_id: int, message_id: int):
    await run_in_threadpool(telegram.edit_message_reply_markup, chat_id, message_id, None)


async def _send_first_reference_image(
    telegram: TelegramService,
    chat_id: int,
    reference_images: list | None,
):
    if not reference_images:
        return
    first = reference_images[0]
    if not isinstance(first, str) or not first.strip():
        return

    if first.startswith("http://") or first.startswith("https://"):
        await run_in_threadpool(
            telegram.send_photo_url,
            chat_id,
            first,
            caption="Reference cake image",
        )
        return

    if first.startswith("data:image/"):
        await run_in_threadpool(
            telegram.send_photo_data_url,
            chat_id,
            first,
            caption="Reference cake image",
        )


async def _resolve_acting_admin(db: AsyncSession) -> User:
    query = select(User).where(
        User.is_active.is_(True),
        User.role.in_([UserRole.ADMIN, UserRole.STAFF]),
    ).order_by(User.created_at.asc())

    if settings.TELEGRAM_ACTING_ADMIN_EMAIL:
        query = select(User).where(
            User.is_active.is_(True),
            User.email == settings.TELEGRAM_ACTING_ADMIN_EMAIL,
            User.role.in_([UserRole.ADMIN, UserRole.STAFF]),
        )

    result = await db.execute(query)
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No active admin/staff user available for Telegram actions",
        )
    return admin


async def _load_customer_map(
    db: AsyncSession,
    customer_ids: set[uuid.UUID],
) -> dict[uuid.UUID, tuple[str, str]]:
    if not customer_ids:
        return {}

    result = await db.execute(
        select(User.id, User.full_name, User.email).where(User.id.in_(customer_ids))
    )
    return {
        row.id: (row.full_name, row.email)
        for row in result.all()
    }


async def _handle_pending_orders_command(
    telegram: TelegramService,
    chat_id: int,
    db: AsyncSession,
    *,
    limit: int = DEFAULT_PENDING_LIMIT,
):
    service = OrderService(db)
    orders = await service.list_orders(
        status=OrderStatus.PENDING_APPROVAL.value,
        limit=limit,
    )

    if not orders:
        await _send_text(telegram, chat_id, "No pending approval orders right now.")
        return

    await _send_text(
        telegram,
        chat_id,
        f"Found {len(orders)} pending approval order(s).",
    )
    for order in orders:
        await _send_text(telegram, chat_id, _order_message(order), _order_markup(order.id))


async def _handle_pending_cakes_command(
    telegram: TelegramService,
    chat_id: int,
    db: AsyncSession,
    *,
    limit: int = DEFAULT_PENDING_LIMIT,
):
    service = CustomCakeService(db)
    cakes = await service.list_custom_cakes(
        status=CustomCakeStatus.PENDING_REVIEW,
        limit=limit,
    )

    if not cakes:
        await _send_text(telegram, chat_id, "No custom cakes pending review right now.")
        return

    customer_map = await _load_customer_map(db, {cake.customer_id for cake in cakes})
    await _send_text(telegram, chat_id, f"Found {len(cakes)} custom cake(s) pending review.")

    for cake in cakes:
        customer_name, customer_email = customer_map.get(
            cake.customer_id,
            ("Unknown customer", "Unknown email"),
        )
        await _send_text(
            telegram,
            chat_id,
            _cake_message(cake, customer_name, customer_email),
            _cake_markup(cake.id),
        )
        await _send_first_reference_image(telegram, chat_id, cake.reference_images)


async def _handle_cakes_by_day_command(
    telegram: TelegramService,
    chat_id: int,
    db: AsyncSession,
    *,
    day_offset: int,
    status_filter: CustomCakeStatus | None = None,
    limit: int = DEFAULT_DAY_LIMIT,
):
    start_utc, end_utc, target_date = _date_range_utc(day_offset)
    query = select(CustomCake).where(
        CustomCake.requested_date.is_not(None),
        CustomCake.requested_date >= start_utc,
        CustomCake.requested_date < end_utc,
    )
    if status_filter is not None:
        query = query.where(CustomCake.status == status_filter)
    query = query.order_by(CustomCake.requested_date.asc(), CustomCake.created_at.asc()).limit(limit)

    result = await db.execute(query)
    cakes = list(result.scalars().all())

    if not cakes:
        await _send_text(
            telegram,
            chat_id,
            f"No custom cakes scheduled for {target_date.isoformat()}.",
        )
        return

    customer_map = await _load_customer_map(db, {cake.customer_id for cake in cakes})
    label = "today" if day_offset == 0 else "tomorrow"
    await _send_text(
        telegram,
        chat_id,
        f"Cakes for {label} ({target_date.isoformat()}): {len(cakes)}",
    )

    for cake in cakes:
        customer_name, customer_email = customer_map.get(
            cake.customer_id,
            ("Unknown customer", "Unknown email"),
        )
        markup = _cake_markup(cake.id) if cake.status == CustomCakeStatus.PENDING_REVIEW else None
        await _send_text(
            telegram,
            chat_id,
            _cake_message(cake, customer_name, customer_email),
            markup,
        )
        await _send_first_reference_image(telegram, chat_id, cake.reference_images)


async def _queue_order_emails_after_approval(order):
    try:
        from app.workers.email_tasks import send_order_confirmation, send_payment_receipt

        payload = _order_to_email_payload(order)
        send_order_confirmation.delay(payload)
        send_payment_receipt.delay(payload)
    except Exception as exc:
        logger.warning("Failed to queue order approval emails: %s", str(exc))


async def _queue_order_email_after_rejection(order, reason: str):
    try:
        from app.workers.email_tasks import send_order_rejection_email

        send_order_rejection_email.delay(_order_to_email_payload(order, reason))
    except Exception as exc:
        logger.warning("Failed to queue order rejection email: %s", str(exc))


async def _approve_order_via_telegram(
    order_id: uuid.UUID,
    acting_admin: User,
    db: AsyncSession,
):
    service = OrderService(db)
    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.PENDING_APPROVAL:
        return order, f"Order is already {order.status.value}."

    if not order.payment:
        raise HTTPException(status_code=400, detail="Order has no payment record")

    payment_intent_id = order.payment.stripe_payment_intent_id
    if payment_intent_id:
        captured = await StripeService.capture_payment_intent(payment_intent_id)
        if captured.get("status") not in ("succeeded", "requires_capture"):
            raise HTTPException(status_code=400, detail="Payment capture failed")

    updated = await service.mark_order_paid(
        order_id=order.id,
        stripe_payment_intent_id=payment_intent_id or f"manual_{order.id}",
        stripe_checkout_session_id=order.payment.stripe_checkout_session_id,
        webhook_data={
            "approved_by_admin_id": str(acting_admin.id),
            "approved_via": "telegram_bot",
        },
        status_after_payment=OrderStatus.CONFIRMED,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Order not found after update")

    await _queue_order_emails_after_approval(updated)
    return updated, f"Order {updated.order_number} approved."


async def _reject_order_via_telegram(
    order_id: uuid.UUID,
    acting_admin: User,
    db: AsyncSession,
):
    service = OrderService(db)
    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.PENDING_APPROVAL:
        return order, f"Order is already {order.status.value}."

    if order.payment and order.payment.stripe_payment_intent_id:
        await StripeService.cancel_payment_intent(order.payment.stripe_payment_intent_id)

    updated = await service.reject_order_after_authorization(order.id, ORDER_REJECT_REASON)
    if not updated:
        raise HTTPException(status_code=404, detail="Order not found after rejection")

    await _queue_order_email_after_rejection(updated, ORDER_REJECT_REASON)
    return updated, f"Order {updated.order_number} rejected."


async def _approve_custom_cake_via_telegram(
    cake_id: uuid.UUID,
    acting_admin: User,
    db: AsyncSession,
) -> str:
    service = CustomCakeService(db)
    cake = await service.get_custom_cake(cake_id)
    if not cake:
        raise HTTPException(status_code=404, detail="Custom cake not found")

    if cake.status != CustomCakeStatus.PENDING_REVIEW:
        return f"Custom cake already in status '{cake.status.value}'."

    final_price = cake.final_price or cake.predicted_price
    if final_price is None:
        raise HTTPException(
            status_code=400,
            detail="No predicted/final price found. Approve from admin website with a price.",
        )

    result = await service.admin_approve(
        cake_id=cake_id,
        admin_id=acting_admin.id,
        final_price=Decimal(str(final_price)),
        admin_notes=APPROVED_FROM_TELEGRAM_NOTE,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return f"Custom cake {cake_id} approved."


async def _reject_custom_cake_via_telegram(
    cake_id: uuid.UUID,
    acting_admin: User,
    db: AsyncSession,
) -> str:
    service = CustomCakeService(db)
    cake = await service.get_custom_cake(cake_id)
    if not cake:
        raise HTTPException(status_code=404, detail="Custom cake not found")

    if cake.status != CustomCakeStatus.PENDING_REVIEW:
        return f"Custom cake already in status '{cake.status.value}'."

    result = await service.admin_reject(
        cake_id=cake_id,
        admin_id=acting_admin.id,
        rejection_reason=CAKE_REJECT_REASON,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return f"Custom cake {cake_id} rejected."


@router.post("/webhook/{secret}")
async def telegram_webhook(
    secret: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Telegram webhook receiver for admin commands and callbacks.
    """
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram bot is not configured",
        )
    if secret != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret")

    update = await request.json()
    telegram = TelegramService()

    callback = update.get("callback_query")
    if callback:
        callback_id = callback.get("id")
        data = callback.get("data", "")
        message = callback.get("message", {}) or {}
        chat_id = (message.get("chat", {}) or {}).get("id")
        message_id = message.get("message_id")

        if not _is_authorized_chat(chat_id):
            if callback_id:
                await _answer_callback(telegram, callback_id, "Unauthorized chat")
            return {"ok": True}

        if not callback_id:
            return {"ok": True}

        try:
            parts = data.split(":")
            if len(parts) == 2 and parts[0] == "cmd":
                action = parts[1]
                if action == "help":
                    await _send_text(
                        telegram,
                        int(chat_id),
                        _bot_help_message(),
                        _command_keyboard(),
                    )
                elif action == "params":
                    await _send_text(
                        telegram,
                        int(chat_id),
                        _bot_params_message(),
                        _command_keyboard(),
                    )
                elif action == "pending_orders":
                    await _send_text(
                        telegram,
                        int(chat_id),
                        "Select a limit for pending orders:",
                        _limit_option_keyboard("po", "cmd:help"),
                    )
                elif action == "pending_cakes":
                    await _send_text(
                        telegram,
                        int(chat_id),
                        "Select a limit for pending custom cakes:",
                        _limit_option_keyboard("pc", "cmd:help"),
                    )
                elif action == "today":
                    await _send_text(
                        telegram,
                        int(chat_id),
                        "Select a status for today's cakes:",
                        _day_status_keyboard("td"),
                    )
                elif action == "tomorrow":
                    await _send_text(
                        telegram,
                        int(chat_id),
                        "Select a status for tomorrow's cakes:",
                        _day_status_keyboard("tm"),
                    )
                elif action == "incoming7":
                    await _handle_incoming_window_command(
                        telegram,
                        int(chat_id),
                        db,
                        days=7,
                    )
                elif action == "incoming30":
                    await _handle_incoming_window_command(
                        telegram,
                        int(chat_id),
                        db,
                        days=30,
                    )
                elif action == "orders_day":
                    await _send_text(
                        telegram,
                        int(chat_id),
                        "Select a pickup day for orders:",
                        _date_picker_keyboard(
                            select_prefix="od",
                            page_prefix="odp",
                            page=_picker_page_for_offset(offset=0),
                            back_callback="cmd:help",
                        ),
                    )
                elif action == "cakes_day":
                    await _send_text(
                        telegram,
                        int(chat_id),
                        "Select a requested day for custom cakes:",
                        _date_picker_keyboard(
                            select_prefix="cd",
                            page_prefix="cdp",
                            page=_picker_page_for_offset(offset=0),
                            back_callback="cmd:help",
                        ),
                    )
                elif action == "orders_range":
                    await _send_text(
                        telegram,
                        int(chat_id),
                        "Select START date for orders range:",
                        _date_picker_keyboard(
                            select_prefix="ors",
                            page_prefix="orsp",
                            page=_picker_page_for_offset(offset=0),
                            back_callback="cmd:help",
                        ),
                    )
                elif action == "cakes_range":
                    await _send_text(
                        telegram,
                        int(chat_id),
                        "Select START date for cakes range:",
                        _date_picker_keyboard(
                            select_prefix="crs",
                            page_prefix="crsp",
                            page=_picker_page_for_offset(offset=0),
                            back_callback="cmd:help",
                        ),
                    )
                else:
                    await _answer_callback(telegram, callback_id, "Unsupported command action")
                    return {"ok": True}

                await _answer_callback(telegram, callback_id, "Done")
                return {"ok": True}

            if len(parts) == 2 and parts[0] in {"odp", "cdp", "orsp", "crsp"}:
                page = _parse_picker_value(parts[1], min_value=0, max_value=99)
                if page is None:
                    await _answer_callback(telegram, callback_id, "Invalid page")
                    return {"ok": True}

                if parts[0] == "odp":
                    text, markup = (
                        "Select a pickup day for orders:",
                        _date_picker_keyboard(
                            select_prefix="od",
                            page_prefix="odp",
                            page=page,
                            back_callback="cmd:help",
                        ),
                    )
                elif parts[0] == "cdp":
                    text, markup = (
                        "Select a requested day for custom cakes:",
                        _date_picker_keyboard(
                            select_prefix="cd",
                            page_prefix="cdp",
                            page=page,
                            back_callback="cmd:help",
                        ),
                    )
                elif parts[0] == "orsp":
                    text, markup = (
                        "Select START date for orders range:",
                        _date_picker_keyboard(
                            select_prefix="ors",
                            page_prefix="orsp",
                            page=page,
                            back_callback="cmd:help",
                        ),
                    )
                else:
                    text, markup = (
                        "Select START date for cakes range:",
                        _date_picker_keyboard(
                            select_prefix="crs",
                            page_prefix="crsp",
                            page=page,
                            back_callback="cmd:help",
                        ),
                    )

                await _send_text(telegram, int(chat_id), text, markup)
                await _answer_callback(telegram, callback_id, "Done")
                return {"ok": True}

            if len(parts) == 2 and parts[0] in {"od", "cd"}:
                offset = _parse_picker_value(
                    parts[1],
                    min_value=DATE_PICKER_MIN_OFFSET,
                    max_value=DATE_PICKER_MAX_OFFSET,
                )
                if offset is None:
                    await _answer_callback(telegram, callback_id, "Invalid date")
                    return {"ok": True}

                start_utc, end_utc, target_date = _offset_to_utc_range(offset)
                if parts[0] == "od":
                    await _handle_orders_in_range_command(
                        telegram,
                        int(chat_id),
                        db,
                        start_utc=start_utc,
                        end_utc=end_utc,
                        start_date=target_date,
                        end_date=target_date,
                    )
                else:
                    await _handle_cakes_in_range_command(
                        telegram,
                        int(chat_id),
                        db,
                        start_utc=start_utc,
                        end_utc=end_utc,
                        start_date=target_date,
                        end_date=target_date,
                    )

                await _answer_callback(telegram, callback_id, "Done")
                return {"ok": True}

            if len(parts) == 2 and parts[0] in {"ors", "crs"}:
                start_offset = _parse_picker_value(
                    parts[1],
                    min_value=DATE_PICKER_MIN_OFFSET,
                    max_value=DATE_PICKER_MAX_OFFSET,
                )
                if start_offset is None:
                    await _answer_callback(telegram, callback_id, "Invalid start date")
                    return {"ok": True}

                if parts[0] == "ors":
                    label = f"Select END date for orders (from {_date_for_offset(start_offset).isoformat()}):"
                    markup = _range_end_picker_keyboard(
                        select_prefix="ore",
                        page_prefix="orep",
                        start_offset=start_offset,
                        page=0,
                        back_callback="cmd:orders_range",
                    )
                else:
                    label = f"Select END date for cakes (from {_date_for_offset(start_offset).isoformat()}):"
                    markup = _range_end_picker_keyboard(
                        select_prefix="cre",
                        page_prefix="crep",
                        start_offset=start_offset,
                        page=0,
                        back_callback="cmd:cakes_range",
                    )

                await _send_text(telegram, int(chat_id), label, markup)
                await _answer_callback(telegram, callback_id, "Done")
                return {"ok": True}

            if len(parts) == 3 and parts[0] in {"orep", "crep"}:
                start_offset = _parse_picker_value(
                    parts[1],
                    min_value=DATE_PICKER_MIN_OFFSET,
                    max_value=DATE_PICKER_MAX_OFFSET,
                )
                page = _parse_picker_value(parts[2], min_value=0, max_value=99)
                if start_offset is None or page is None:
                    await _answer_callback(telegram, callback_id, "Invalid page")
                    return {"ok": True}

                if parts[0] == "orep":
                    label = f"Select END date for orders (from {_date_for_offset(start_offset).isoformat()}):"
                    markup = _range_end_picker_keyboard(
                        select_prefix="ore",
                        page_prefix="orep",
                        start_offset=start_offset,
                        page=page,
                        back_callback="cmd:orders_range",
                    )
                else:
                    label = f"Select END date for cakes (from {_date_for_offset(start_offset).isoformat()}):"
                    markup = _range_end_picker_keyboard(
                        select_prefix="cre",
                        page_prefix="crep",
                        start_offset=start_offset,
                        page=page,
                        back_callback="cmd:cakes_range",
                    )

                await _send_text(telegram, int(chat_id), label, markup)
                await _answer_callback(telegram, callback_id, "Done")
                return {"ok": True}

            if len(parts) == 3 and parts[0] in {"ore", "cre"}:
                start_offset = _parse_picker_value(
                    parts[1],
                    min_value=DATE_PICKER_MIN_OFFSET,
                    max_value=DATE_PICKER_MAX_OFFSET,
                )
                end_offset = _parse_picker_value(
                    parts[2],
                    min_value=DATE_PICKER_MIN_OFFSET,
                    max_value=DATE_PICKER_MAX_OFFSET,
                )
                if start_offset is None or end_offset is None or end_offset < start_offset:
                    await _answer_callback(telegram, callback_id, "Invalid date range")
                    return {"ok": True}

                start_utc, end_utc, start_date, end_date = _offset_span_to_utc_range(
                    start_offset,
                    end_offset,
                )
                if parts[0] == "ore":
                    await _handle_orders_in_range_command(
                        telegram,
                        int(chat_id),
                        db,
                        start_utc=start_utc,
                        end_utc=end_utc,
                        start_date=start_date,
                        end_date=end_date,
                    )
                else:
                    await _handle_cakes_in_range_command(
                        telegram,
                        int(chat_id),
                        db,
                        start_utc=start_utc,
                        end_utc=end_utc,
                        start_date=start_date,
                        end_date=end_date,
                    )

                await _answer_callback(telegram, callback_id, "Done")
                return {"ok": True}

            if len(parts) == 2 and parts[0] in {"po", "pc"}:
                limit, err = _parse_limit_arg(parts[1], DEFAULT_PENDING_LIMIT)
                if err:
                    await _answer_callback(telegram, callback_id, err)
                    return {"ok": True}

                if parts[0] == "po":
                    await _handle_pending_orders_command(
                        telegram,
                        int(chat_id),
                        db,
                        limit=limit or DEFAULT_PENDING_LIMIT,
                    )
                else:
                    await _handle_pending_cakes_command(
                        telegram,
                        int(chat_id),
                        db,
                        limit=limit or DEFAULT_PENDING_LIMIT,
                    )

                await _answer_callback(telegram, callback_id, "Done")
                return {"ok": True}

            if len(parts) == 2 and parts[0] in {"tds", "tms"}:
                status_key = parts[1].lower()
                if status_key not in CAKE_STATUS_PARAM_MAP:
                    await _answer_callback(telegram, callback_id, "Invalid status")
                    return {"ok": True}

                day_prefix = "td" if parts[0] == "tds" else "tm"
                day_label = "today" if day_prefix == "td" else "tomorrow"
                await _send_text(
                    telegram,
                    int(chat_id),
                    f"Select a limit for {day_label} ({_status_label(status_key)}):",
                    _day_limit_keyboard(day_prefix, status_key),
                )
                await _answer_callback(telegram, callback_id, "Done")
                return {"ok": True}

            if len(parts) == 3 and parts[0] in {"td", "tm"}:
                day_prefix = parts[0]
                status_key = parts[1].lower()
                if status_key not in CAKE_STATUS_PARAM_MAP:
                    await _answer_callback(telegram, callback_id, "Invalid status")
                    return {"ok": True}

                limit, err = _parse_limit_arg(parts[2], DEFAULT_DAY_LIMIT)
                if err:
                    await _answer_callback(telegram, callback_id, err)
                    return {"ok": True}

                await _handle_cakes_by_day_command(
                    telegram,
                    int(chat_id),
                    db,
                    day_offset=0 if day_prefix == "td" else 1,
                    status_filter=CAKE_STATUS_PARAM_MAP[status_key],
                    limit=limit or DEFAULT_DAY_LIMIT,
                )
                await _answer_callback(telegram, callback_id, "Done")
                return {"ok": True}

            if len(parts) != 3:
                await _answer_callback(telegram, callback_id, "Unsupported action payload")
                return {"ok": True}

            domain, action, raw_id = parts
            target_id = uuid.UUID(raw_id)
            acting_admin = await _resolve_acting_admin(db)

            if domain == "order" and action == "approve":
                _, result_message = await _approve_order_via_telegram(target_id, acting_admin, db)
            elif domain == "order" and action == "reject":
                _, result_message = await _reject_order_via_telegram(target_id, acting_admin, db)
            elif domain == "cake" and action == "approve":
                result_message = await _approve_custom_cake_via_telegram(target_id, acting_admin, db)
            elif domain == "cake" and action == "reject":
                result_message = await _reject_custom_cake_via_telegram(target_id, acting_admin, db)
            else:
                await _answer_callback(telegram, callback_id, "Unsupported action")
                return {"ok": True}

            await _answer_callback(telegram, callback_id, "Done")
            if isinstance(chat_id, int):
                await _send_text(telegram, chat_id, f"✅ {result_message}")
                if isinstance(message_id, int):
                    await _clear_buttons(telegram, chat_id, message_id)
        except ValueError:
            await _answer_callback(telegram, callback_id, "Invalid target identifier")
        except HTTPException as exc:
            await _answer_callback(telegram, callback_id, f"Failed: {exc.detail}")
            if isinstance(chat_id, int):
                await _send_text(telegram, chat_id, f"⚠️ {exc.detail}")
        except Exception as exc:
            logger.exception("Telegram callback processing failed: %s", str(exc))
            await _answer_callback(telegram, callback_id, "Unexpected error")
            if isinstance(chat_id, int):
                await _send_text(telegram, chat_id, "⚠️ Failed to process this action.")

        return {"ok": True}

    message = update.get("message")
    if not message:
        return {"ok": True}

    chat = message.get("chat", {}) or {}
    chat_id = chat.get("id")
    if not _is_authorized_chat(chat_id):
        return {"ok": True}

    text = (message.get("text", "") or "").strip()
    if not text.startswith("/"):
        return {"ok": True}

    tokens = text.split()
    command = _extract_command(tokens[0]) if tokens else ""
    args = tokens[1:]
    if command in ("/start", "/help"):
        await _send_text(
            telegram,
            int(chat_id),
            _bot_help_message(),
            _command_keyboard(),
        )
        return {"ok": True}

    if command == "/params":
        await _send_text(
            telegram,
            int(chat_id),
            _bot_params_message(),
            _command_keyboard(),
        )
        return {"ok": True}

    if command == "/incoming7":
        await _handle_incoming_window_command(
            telegram,
            int(chat_id),
            db,
            days=7,
        )
        return {"ok": True}

    if command == "/incoming30":
        await _handle_incoming_window_command(
            telegram,
            int(chat_id),
            db,
            days=30,
        )
        return {"ok": True}

    if command == "/orders_day":
        await _send_text(
            telegram,
            int(chat_id),
            "Select a pickup day for orders:",
            _date_picker_keyboard(
                select_prefix="od",
                page_prefix="odp",
                page=_picker_page_for_offset(offset=0),
                back_callback="cmd:help",
            ),
        )
        return {"ok": True}

    if command == "/cakes_day":
        await _send_text(
            telegram,
            int(chat_id),
            "Select a requested day for custom cakes:",
            _date_picker_keyboard(
                select_prefix="cd",
                page_prefix="cdp",
                page=_picker_page_for_offset(offset=0),
                back_callback="cmd:help",
            ),
        )
        return {"ok": True}

    if command == "/orders_range":
        await _send_text(
            telegram,
            int(chat_id),
            "Select START date for orders range:",
            _date_picker_keyboard(
                select_prefix="ors",
                page_prefix="orsp",
                page=_picker_page_for_offset(offset=0),
                back_callback="cmd:help",
            ),
        )
        return {"ok": True}

    if command == "/cakes_range":
        await _send_text(
            telegram,
            int(chat_id),
            "Select START date for cakes range:",
            _date_picker_keyboard(
                select_prefix="crs",
                page_prefix="crsp",
                page=_picker_page_for_offset(offset=0),
                back_callback="cmd:help",
            ),
        )
        return {"ok": True}

    if command == "/pending_orders":
        if len(args) > 1:
            await _send_text(telegram, int(chat_id), "Too many parameters. Use /params.")
            return {"ok": True}

        limit, err = _parse_limit_arg(args[0] if args else None, DEFAULT_PENDING_LIMIT)
        if err:
            await _send_text(telegram, int(chat_id), err)
            return {"ok": True}

        await _handle_pending_orders_command(
            telegram,
            int(chat_id),
            db,
            limit=limit or DEFAULT_PENDING_LIMIT,
        )
        return {"ok": True}

    if command == "/pending_cakes":
        if len(args) > 1:
            await _send_text(telegram, int(chat_id), "Too many parameters. Use /params.")
            return {"ok": True}

        limit, err = _parse_limit_arg(args[0] if args else None, DEFAULT_PENDING_LIMIT)
        if err:
            await _send_text(telegram, int(chat_id), err)
            return {"ok": True}

        await _handle_pending_cakes_command(
            telegram,
            int(chat_id),
            db,
            limit=limit or DEFAULT_PENDING_LIMIT,
        )
        return {"ok": True}

    if command == "/today":
        status_filter, limit, err = _parse_day_command_args(args)
        if err:
            await _send_text(telegram, int(chat_id), err)
            return {"ok": True}

        await _handle_cakes_by_day_command(
            telegram,
            int(chat_id),
            db,
            day_offset=0,
            status_filter=status_filter,
            limit=limit,
        )
        return {"ok": True}

    if command == "/tomorrow":
        status_filter, limit, err = _parse_day_command_args(args)
        if err:
            await _send_text(telegram, int(chat_id), err)
            return {"ok": True}

        await _handle_cakes_by_day_command(
            telegram,
            int(chat_id),
            db,
            day_offset=1,
            status_filter=status_filter,
            limit=limit,
        )
        return {"ok": True}

    await _send_text(
        telegram,
        int(chat_id),
        "Unknown command. Use /help to see available commands.",
    )
    return {"ok": True}
