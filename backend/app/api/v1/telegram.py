"""
Telegram bot webhook endpoints for admin workflows.
"""

import uuid
from calendar import monthrange
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
from app.models.product import Product, ProductCategory
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
PRICE_SET_FROM_TELEGRAM_NOTE = "Final price updated via Telegram bot."
DEFAULT_PENDING_LIMIT = 10
MAX_TELEGRAM_LIST_LIMIT = 20
DEFAULT_DAY_LIMIT = 20
QUICK_LIMIT_OPTIONS = (5, 10, 20)
MAX_RANGE_RESULTS = 100
CALENDAR_MIN_OFFSET = -365
CALENDAR_MAX_OFFSET = 365
INCOMING_MAX_DAYS = 30
DATE_PICKER_MIN_OFFSET = CALENDAR_MIN_OFFSET
DATE_PICKER_MAX_OFFSET = CALENDAR_MAX_OFFSET
DATE_PICKER_PAGE_SIZE = 7
ORDER_STATUS_FILTERS: dict[str, tuple[str, tuple[OrderStatus, ...]]] = {
    "p": ("Pending Approval", (OrderStatus.PENDING_APPROVAL,)),
    "d": (
        "Paid / To Make",
        (
            OrderStatus.PAID,
            OrderStatus.CONFIRMED,
            OrderStatus.PREPARING,
            OrderStatus.READY,
        ),
    ),
}
CAKE_STATUS_FILTERS: dict[str, tuple[str, tuple[CustomCakeStatus, ...]]] = {
    "p": ("Pending Approval", (CustomCakeStatus.PENDING_REVIEW,)),
    "d": (
        "Paid / To Make",
        (
            CustomCakeStatus.PAID,
            CustomCakeStatus.IN_PRODUCTION,
        ),
    ),
}
DOMAIN_LABELS = {
    "o": "Orders",
    "c": "Cake Orders",
}
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


def _price_str(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


def _cake_price_reference(cake: CustomCake) -> Decimal:
    reference = cake.final_price or cake.predicted_price
    if reference is None:
        return Decimal("50.00")
    return Decimal(str(reference))


def _cake_price_adjustment_rows(cake: CustomCake) -> list[list[dict]]:
    rows: list[list[dict]] = []
    base_price = cake.final_price or cake.predicted_price
    if base_price is not None:
        base = Decimal(str(base_price))
        minus_ten = (base * Decimal("0.90")).quantize(Decimal("0.01"))
        plus_ten = (base * Decimal("1.10")).quantize(Decimal("0.01"))
        rows.append(
            [
                {"text": "-10%", "callback_data": f"cakeprice:{cake.id}:{_price_str(minus_ten)}"},
                {"text": "Current", "callback_data": f"cakeprice:{cake.id}:{_price_str(base)}"},
                {"text": "+10%", "callback_data": f"cakeprice:{cake.id}:{_price_str(plus_ten)}"},
            ]
        )

    if cake.predicted_price is not None:
        predicted = Decimal(str(cake.predicted_price))
        rows.append(
            [
                {"text": "Use Predicted", "callback_data": f"cakeprice:{cake.id}:{_price_str(predicted)}"},
            ]
        )
    return rows


def _cake_price_editor_message(cake: CustomCake) -> str:
    suggested = _cake_price_reference(cake)
    return (
        "💵 <b>Edit Final Price</b>\n"
        f"Cake ID: <b>{cake.id}</b>\n"
        f"Predicted estimate: {_as_money(cake.predicted_price)}\n"
        f"Current final price: {_as_money(cake.final_price)}\n\n"
        "Choose a quick amount below, or set an exact amount with:\n"
        f"<code>/cakeprice {cake.id} {_price_str(suggested)}</code>\n\n"
        "After updating the amount, tap ✅ Approve."
    )


def _cake_price_editor_markup(cake: CustomCake) -> dict:
    rows = _cake_price_adjustment_rows(cake)
    rows.append(
        [
            {"text": "✅ Approve", "callback_data": f"cake:approve:{cake.id}"},
            {"text": "❌ Reject", "callback_data": f"cake:reject:{cake.id}"},
        ]
    )
    return {"inline_keyboard": rows}


def _cake_markup(cake: CustomCake) -> dict:
    rows: list[list[dict]] = [
        [
            {"text": "✅ Approve", "callback_data": f"cake:approve:{cake.id}"},
            {"text": "❌ Reject", "callback_data": f"cake:reject:{cake.id}"},
        ],
        [
            {"text": "💵 Edit Final Price", "callback_data": f"cake:editprice:{cake.id}"},
        ],
    ]
    return {"inline_keyboard": rows}


def _command_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "🧁 Products", "callback_data": "menu:products"},
                {"text": "📦 Orders", "callback_data": "menu:orders"},
            ],
            [
                {"text": "🎂 Cake Orders", "callback_data": "menu:cakes"},
            ],
        ]
    }


def _date_tools_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "📆 Orders by Day", "callback_data": "cmd:orders_day"},
                {"text": "🎂 Cakes by Day", "callback_data": "cmd:cakes_day"},
            ],
            [
                {"text": "🗓️ Orders Date Range", "callback_data": "cmd:orders_range"},
                {"text": "🧁 Cakes Date Range", "callback_data": "cmd:cakes_range"},
            ],
            [
                {"text": "⬅️ Main Menu", "callback_data": "menu:main"},
            ],
        ]
    }


def _pending_tools_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "📦 Pending Orders", "callback_data": "cmd:pending_orders"},
                {"text": "🎂 Pending Cakes", "callback_data": "cmd:pending_cakes"},
            ],
            [
                {"text": "⬅️ Main Menu", "callback_data": "menu:main"},
            ],
        ]
    }


def _main_menu_message() -> str:
    return (
        "🤖 <b>Kabul Sweets Admin Bot</b>\n"
        "Commands:\n"
        "<code>/menu</code> products by category\n"
        "<code>/order</code> order queue (pending/paid)\n"
        "<code>/cake</code> cake queue (pending/paid)\n"
        "<code>/cakeprice &lt;cake_id&gt; &lt;amount&gt;</code> set final cake price\n\n"
        "If chat is cleared, type <code>/menu</code>."
    )


def _date_menu_message() -> str:
    return (
        "🗓️ <b>Date Tools</b>\n"
        "Pick exact dates with buttons (from date -> to date)."
    )


def _pending_menu_message() -> str:
    return (
        "✅ <b>Pending Actions</b>\n"
        "Review and approve/reject pending orders and custom cakes."
    )


def _order_filter_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "🕒 Pending", "callback_data": "flow:o:p"},
                {"text": "💵 Paid / To Make", "callback_data": "flow:o:d"},
            ],
            [
                {"text": "⬅️ Main", "callback_data": "menu:main"},
            ],
        ]
    }


def _cake_filter_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "🕒 Pending", "callback_data": "flow:c:p"},
                {"text": "💵 Paid / To Make", "callback_data": "flow:c:d"},
            ],
            [
                {"text": "⬅️ Main", "callback_data": "menu:main"},
            ],
        ]
    }


def _category_keyboard(categories: list[ProductCategory]) -> dict:
    rows: list[list[dict]] = []
    buttons = [
        {
            "text": cat.value.replace("_", " ").title(),
            "callback_data": f"pcat:{cat.value}",
        }
        for cat in categories
    ]
    for index in range(0, len(buttons), 2):
        rows.append(buttons[index:index + 2])
    rows.append([{"text": "⬅️ Main", "callback_data": "menu:main"}])
    return {"inline_keyboard": rows}


def _calendar_month_start(target: date) -> date:
    return target.replace(day=1)


def _shift_month(month_start: date, delta: int) -> date:
    month_index = (month_start.year * 12) + (month_start.month - 1) + delta
    year = month_index // 12
    month = (month_index % 12) + 1
    return date(year, month, 1)


def _format_date_token(value: date) -> str:
    return value.strftime("%Y%m%d")


def _parse_date_token(raw: str) -> date | None:
    try:
        return datetime.strptime(raw, "%Y%m%d").date()
    except ValueError:
        return None


def _format_month_token(value: date) -> str:
    return value.strftime("%Y%m")


def _parse_month_token(raw: str) -> date | None:
    try:
        parsed = datetime.strptime(raw, "%Y%m").date()
    except ValueError:
        return None
    return parsed.replace(day=1)


def _calendar_picker_keyboard(
    *,
    domain: str,
    status_code: str,
    stage: str,
    month_start: date,
    start_date: date | None = None,
) -> dict:
    year = month_start.year
    month = month_start.month
    first_weekday, days_in_month = monthrange(year, month)  # Monday=0
    month_label = month_start.strftime("%B %Y")

    header_row = [{"text": month_label, "callback_data": "noop"}]
    weekday_row = [
        {"text": day, "callback_data": "noop"}
        for day in ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
    ]

    rows: list[list[dict]] = [header_row, weekday_row]
    week: list[dict] = []

    for _ in range(first_weekday):
        week.append({"text": " ", "callback_data": "noop"})

    for day in range(1, days_in_month + 1):
        current = date(year, month, day)
        disabled = stage == "e" and start_date is not None and current < start_date
        if disabled:
            button = {"text": "·", "callback_data": "noop"}
        elif stage == "s":
            button = {
                "text": str(day),
                "callback_data": f"cals:{domain}:{status_code}:{_format_date_token(current)}",
            }
        else:
            button = {
                "text": str(day),
                "callback_data": (
                    f"cale:{domain}:{status_code}:"
                    f"{_format_date_token(start_date or current)}:{_format_date_token(current)}"
                ),
            }
        week.append(button)
        if len(week) == 7:
            rows.append(week)
            week = []

    if week:
        while len(week) < 7:
            week.append({"text": " ", "callback_data": "noop"})
        rows.append(week)

    month_token = _format_month_token(month_start)
    if stage == "s":
        prev_cb = f"caln:{domain}:{status_code}:s:{month_token}:prev"
        next_cb = f"caln:{domain}:{status_code}:s:{month_token}:next"
    else:
        start_token = _format_date_token(start_date or month_start)
        prev_cb = f"caln:{domain}:{status_code}:e:{month_token}:{start_token}:prev"
        next_cb = f"caln:{domain}:{status_code}:e:{month_token}:{start_token}:next"

    rows.append(
        [
            {"text": "⬅️", "callback_data": prev_cb},
            {"text": "➡️", "callback_data": next_cb},
        ]
    )

    back_callback = "menu:orders" if domain == "o" else "menu:cakes"
    rows.append([{"text": "⬅️ Back", "callback_data": back_callback}])
    return {"inline_keyboard": rows}


def _date_range_to_utc(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    tz = _business_timezone()
    start_local = datetime.combine(start_date, time.min, tzinfo=tz)
    end_local = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=tz)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def _is_date_in_calendar_window(value: date) -> bool:
    delta_days = (value - _today_local_date()).days
    return CALENDAR_MIN_OFFSET <= delta_days <= CALENDAR_MAX_OFFSET


def _domain_status_label(domain: str, status_code: str) -> str:
    if domain == "o":
        return ORDER_STATUS_FILTERS.get(status_code, ("Orders", tuple()))[0]
    return CAKE_STATUS_FILTERS.get(status_code, ("Cake Orders", tuple()))[0]


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


def _day_status_keyboard(day_prefix: str, back_callback: str = "menu:date") -> dict:
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
    rows.append([{"text": "⬅️ Back", "callback_data": back_callback}])
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
        "<b>Use only these commands:</b>\n"
        "<code>/menu</code> products category -> products list\n"
        "<code>/order</code> pending/paid -> date picker\n"
        "<code>/cake</code> pending/paid -> date picker\n"
        "<code>/cakeprice &lt;cake_id&gt; &lt;amount&gt;</code> set final cake price\n"
        "<code>/help</code> show this message"
    )


def _bot_params_message() -> str:
    return (
        "📘 <b>Flow</b>\n\n"
        "1. Use <code>/order</code> or <code>/cake</code>\n"
        "2. Choose <b>Pending</b> or <b>Paid</b>\n"
        "3. Pick start date then end date from calendar\n"
        "4. Bot shows clean list for that range"
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
        f"Predicted price (estimate): {_as_money(cake.predicted_price)}\n"
        f"Final approved price: {_as_money(cake.final_price)}\n"
        f"Requested date: {requested_date}\n"
        f"Time slot: {cake.time_slot or 'Not provided'}\n"
        f"Cake message: {cake.cake_message or 'None'}\n"
        f"Design notes: {cake.decoration_description or 'None'}\n"
        f"Images: {len(cake.reference_images or [])}\n\n"
        f"<a href=\"{admin_link}\">Open custom cakes in admin</a>"
    )


def _local_date_text(dt: datetime | None) -> str:
    if dt is None:
        return "N/A"
    return dt.astimezone(_business_timezone()).date().isoformat()


def _order_compact_line(order: Order) -> str:
    pickup_date = _local_date_text(order.pickup_date)
    pickup_slot = order.pickup_time_slot or "Anytime"
    return (
        f"- <b>{order.order_number}</b> | {pickup_date} {pickup_slot} | "
        f"{_as_money(order.total)} | {order.status.value}"
    )


def _cake_compact_line(cake: CustomCake, customer_name: str) -> str:
    requested_date = _local_date_text(cake.requested_date)
    time_slot = cake.time_slot or "Anytime"
    return (
        f"- <b>{customer_name}</b> | {requested_date} {time_slot} | "
        f"{cake.diameter_inches}\" | {_as_money(cake.final_price or cake.predicted_price)} | {cake.status.value}"
    )


async def _send_compact_list(
    telegram: TelegramService,
    chat_id: int,
    *,
    title: str,
    lines: list[str],
    empty_text: str,
    admin_link: str,
    admin_link_label: str,
):
    if not lines:
        await _send_text(telegram, chat_id, empty_text)
        return

    max_lines = 30
    visible = lines[:max_lines]
    text = f"{title}\n" + "\n".join(visible)
    if len(lines) > max_lines:
        text += f"\n...and {len(lines) - max_lines} more."
    text += f"\n\n<a href=\"{admin_link}\">{admin_link_label}</a>"
    await _send_text(telegram, chat_id, text)


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
    statuses: tuple[OrderStatus, ...] | None = None,
    header_label: str = "Orders",
):
    query = (
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
    if statuses:
        query = query.where(Order.status.in_(statuses))

    result = await db.execute(query)
    orders = list(result.scalars().all())

    title = (
        f"📦 <b>{header_label}</b> | "
        f"{start_date.isoformat()} to {end_date.isoformat()} | {len(orders)} total"
    )
    lines = [_order_compact_line(order) for order in orders]
    await _send_compact_list(
        telegram,
        chat_id,
        title=title,
        lines=lines,
        empty_text=f"No orders scheduled between {start_date.isoformat()} and {end_date.isoformat()}.",
        admin_link=f"{settings.ADMIN_FRONTEND_URL.rstrip('/')}/apps/orders",
        admin_link_label="Open admin orders",
    )


async def _handle_cakes_in_range_command(
    telegram: TelegramService,
    chat_id: int,
    db: AsyncSession,
    *,
    start_utc: datetime,
    end_utc: datetime,
    start_date: date,
    end_date: date,
    statuses: tuple[CustomCakeStatus, ...] | None = None,
    header_label: str = "Cake Orders",
):
    query = (
        select(CustomCake)
        .where(
            CustomCake.requested_date.is_not(None),
            CustomCake.requested_date >= start_utc,
            CustomCake.requested_date < end_utc,
        )
        .order_by(CustomCake.requested_date.asc(), CustomCake.created_at.asc())
        .limit(MAX_RANGE_RESULTS)
    )
    if statuses:
        query = query.where(CustomCake.status.in_(statuses))

    result = await db.execute(query)
    cakes = list(result.scalars().all())

    customer_map = await _load_customer_map(db, {cake.customer_id for cake in cakes})
    title = (
        f"🎂 <b>{header_label}</b> | "
        f"{start_date.isoformat()} to {end_date.isoformat()} | {len(cakes)} total"
    )
    lines = [
        _cake_compact_line(
            cake,
            customer_map.get(cake.customer_id, ("Unknown customer", ""))[0],
        )
        for cake in cakes
    ]
    await _send_compact_list(
        telegram,
        chat_id,
        title=title,
        lines=lines,
        empty_text=f"No custom cakes scheduled between {start_date.isoformat()} and {end_date.isoformat()}.",
        admin_link=f"{settings.ADMIN_FRONTEND_URL.rstrip('/')}/apps/custom-cakes",
        admin_link_label="Open custom cakes in admin",
    )


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


async def _upsert_menu_message(
    telegram: TelegramService,
    chat_id: int,
    text: str,
    reply_markup: dict,
    *,
    message_id: int | None = None,
):
    if message_id is not None:
        edited = await run_in_threadpool(
            telegram.edit_message_text,
            chat_id,
            message_id,
            text,
            reply_markup=reply_markup,
        )
        if edited:
            return

    await _send_text(
        telegram,
        chat_id,
        text,
        reply_markup=reply_markup,
    )


async def _answer_callback(telegram: TelegramService, callback_id: str, text: str):
    safe_text = (text or "").strip()[:180]
    ok = await run_in_threadpool(telegram.answer_callback_query, callback_id, safe_text)
    if ok:
        return

    # Retry with empty text in case Telegram rejects the message body.
    if safe_text:
        await run_in_threadpool(telegram.answer_callback_query, callback_id, "")


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
    if settings.TELEGRAM_ACTING_ADMIN_EMAIL:
        preferred_result = await db.execute(
            select(User)
            .where(
                User.is_active.is_(True),
                User.email == settings.TELEGRAM_ACTING_ADMIN_EMAIL,
                User.role.in_([UserRole.ADMIN, UserRole.STAFF]),
            )
            .limit(1)
        )
        preferred_admin = preferred_result.scalars().first()
        if preferred_admin:
            return preferred_admin
        logger.warning(
            "TELEGRAM_ACTING_ADMIN_EMAIL '%s' not found or inactive; using fallback admin.",
            settings.TELEGRAM_ACTING_ADMIN_EMAIL,
        )

    result = await db.execute(
        select(User)
        .where(
            User.is_active.is_(True),
            User.role.in_([UserRole.ADMIN, UserRole.STAFF]),
        )
        .order_by(User.created_at.asc(), User.id.asc())
        .limit(1)
    )
    admin = result.scalars().first()
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


async def _show_product_categories(
    telegram: TelegramService,
    chat_id: int,
    db: AsyncSession,
    *,
    message_id: int | None = None,
):
    result = await db.execute(
        select(Product.category)
        .where(Product.is_active.is_(True))
        .distinct()
        .order_by(Product.category.asc())
    )
    categories = [row[0] for row in result.all() if isinstance(row[0], ProductCategory)]

    if not categories:
        await _upsert_menu_message(
            telegram,
            chat_id,
            "No active product categories found.",
            _command_keyboard(),
            message_id=message_id,
        )
        return

    await _upsert_menu_message(
        telegram,
        chat_id,
        "🧁 <b>Product Categories</b>\nChoose a category to view products.",
        _category_keyboard(categories),
        message_id=message_id,
    )


async def _show_products_for_category(
    telegram: TelegramService,
    chat_id: int,
    db: AsyncSession,
    *,
    category_value: str,
):
    try:
        category = ProductCategory(category_value)
    except ValueError:
        await _send_text(telegram, chat_id, "Invalid category.")
        return

    result = await db.execute(
        select(Product)
        .where(
            Product.is_active.is_(True),
            Product.category == category,
        )
        .order_by(Product.sort_order.asc(), Product.name.asc())
        .limit(MAX_RANGE_RESULTS)
    )
    products = list(result.scalars().all())
    lines = [
        f"- <b>{product.name}</b> | {_as_money(product.base_price)}"
        for product in products
    ]
    await _send_compact_list(
        telegram,
        chat_id,
        title=f"🧁 <b>{category.value.replace('_', ' ').title()}</b> | {len(products)} product(s)",
        lines=lines,
        empty_text=f"No active products in {category.value} category.",
        admin_link=f"{settings.ADMIN_FRONTEND_URL.rstrip('/')}/apps/products",
        admin_link_label="Open products in admin",
    )
    await _send_text(
        telegram,
        chat_id,
        "Pick another category:",
        {"inline_keyboard": [[{"text": "⬅️ Categories", "callback_data": "menu:products"}]]},
    )


async def _show_order_filters(
    telegram: TelegramService,
    chat_id: int,
    *,
    message_id: int | None = None,
):
    await _upsert_menu_message(
        telegram,
        chat_id,
        "📦 <b>Orders</b>\nChoose pending or paid, then pick date range.",
        _order_filter_keyboard(),
        message_id=message_id,
    )


async def _show_cake_filters(
    telegram: TelegramService,
    chat_id: int,
    *,
    message_id: int | None = None,
):
    await _upsert_menu_message(
        telegram,
        chat_id,
        "🎂 <b>Cake Orders</b>\nChoose pending or paid, then pick date range.",
        _cake_filter_keyboard(),
        message_id=message_id,
    )


async def _show_start_calendar(
    telegram: TelegramService,
    chat_id: int,
    *,
    domain: str,
    status_code: str,
    message_id: int | None = None,
):
    if domain == "o":
        status_label = ORDER_STATUS_FILTERS.get(status_code, ("Orders", tuple()))[0]
    else:
        status_label = CAKE_STATUS_FILTERS.get(status_code, ("Cake Orders", tuple()))[0]
    month_start = _calendar_month_start(_today_local_date())
    await _upsert_menu_message(
        telegram,
        chat_id,
        f"🗓️ <b>{DOMAIN_LABELS.get(domain, 'Items')} - {status_label}</b>\nSelect <b>start date</b>.",
        _calendar_picker_keyboard(
            domain=domain,
            status_code=status_code,
            stage="s",
            month_start=month_start,
        ),
        message_id=message_id,
    )


async def _run_status_range(
    telegram: TelegramService,
    chat_id: int,
    db: AsyncSession,
    *,
    domain: str,
    status_code: str,
    start_date: date,
    end_date: date,
):
    start_utc, end_utc = _date_range_to_utc(start_date, end_date)

    if domain == "o":
        status_meta = ORDER_STATUS_FILTERS.get(status_code)
        if not status_meta:
            await _send_text(telegram, chat_id, "Invalid order status.")
            return
        label, statuses = status_meta
        await _handle_orders_in_range_command(
            telegram,
            chat_id,
            db,
            start_utc=start_utc,
            end_utc=end_utc,
            start_date=start_date,
            end_date=end_date,
            statuses=statuses,
            header_label=f"Orders - {label}",
        )
        await _send_text(
            telegram,
            chat_id,
            "Select another order filter:",
            _order_filter_keyboard(),
        )
        return

    status_meta = CAKE_STATUS_FILTERS.get(status_code)
    if not status_meta:
        await _send_text(telegram, chat_id, "Invalid cake status.")
        return
    label, statuses = status_meta
    await _handle_cakes_in_range_command(
        telegram,
        chat_id,
        db,
        start_utc=start_utc,
        end_utc=end_utc,
        start_date=start_date,
        end_date=end_date,
        statuses=statuses,
        header_label=f"Cake Orders - {label}",
    )
    await _send_text(
        telegram,
        chat_id,
        "Select another cake filter:",
        _cake_filter_keyboard(),
    )


async def _handle_pending_orders_command(
    telegram: TelegramService,
    chat_id: int,
    db: AsyncSession,
    *,
    limit: int = DEFAULT_PENDING_LIMIT,
):
    service = OrderService(db)
    pending_review = await service.list_orders(
        status=OrderStatus.PENDING.value,
        limit=limit,
    )
    pending_payment = await service.list_orders(
        status=OrderStatus.PENDING_APPROVAL.value,
        limit=limit,
    )
    orders = sorted(
        [*pending_review, *pending_payment],
        key=lambda order: order.created_at,
        reverse=True,
    )[:limit]

    if not orders:
        await _send_text(telegram, chat_id, "No pending orders right now.")
        return

    await _send_text(
        telegram,
        chat_id,
        f"Found {len(orders)} pending order(s).",
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
            _cake_markup(cake),
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
        markup = _cake_markup(cake) if cake.status == CustomCakeStatus.PENDING_REVIEW else None
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


async def _queue_order_payment_required_email(order):
    try:
        from app.workers.email_tasks import send_order_approval_email

        send_order_approval_email.delay(_order_to_email_payload(order))
    except Exception as exc:
        logger.warning("Failed to queue order payment-required email: %s", str(exc))


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

    if order.status == OrderStatus.PENDING:
        order.status = OrderStatus.PENDING_APPROVAL
        await db.flush()
        await db.refresh(order)
        await _queue_order_payment_required_email(order)
        return order, f"Order {order.order_number} approved and awaiting customer payment."

    if order.status != OrderStatus.PENDING_APPROVAL:
        return order, f"Order is already {order.status.value}."

    if not order.payment:
        raise HTTPException(status_code=400, detail="Order has no payment record")

    payment_intent_id = order.payment.stripe_payment_intent_id
    if not payment_intent_id:
        return order, f"Order {order.order_number} is awaiting customer payment."

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

    if order.status not in (OrderStatus.PENDING, OrderStatus.PENDING_APPROVAL):
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
    approved_price = result.get("final_price")
    predicted_price = result.get("predicted_price")
    return (
        f"Custom cake {cake_id} approved at {_as_money(approved_price)} "
        f"(predicted: {_as_money(predicted_price)}). Customer has been notified."
    )


async def _set_custom_cake_price_via_telegram(
    cake_id: uuid.UUID,
    acting_admin: User,
    final_price: Decimal,
    db: AsyncSession,
) -> str:
    if final_price <= 0:
        raise HTTPException(status_code=400, detail="Final price must be greater than 0.")

    service = CustomCakeService(db)
    result = await service.set_final_price(
        cake_id=cake_id,
        admin_id=acting_admin.id,
        final_price=final_price,
        admin_note=PRICE_SET_FROM_TELEGRAM_NOTE,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    predicted = result.get("predicted_price")
    final_value = result.get("final_price")
    if predicted is not None and final_value is not None:
        return (
            f"Final price set to {_as_money(final_value)} "
            f"(predicted estimate: {_as_money(predicted)}). "
            "Now click Approve to notify customer."
        )
    return f"Final price set to {_as_money(final_value)}. Now click Approve."


async def _open_cake_price_editor_via_telegram(
    telegram: TelegramService,
    chat_id: int,
    cake_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    service = CustomCakeService(db)
    cake = await service.get_custom_cake(cake_id)
    if not cake:
        raise HTTPException(status_code=404, detail="Custom cake not found")

    await _send_text(
        telegram,
        chat_id,
        _cake_price_editor_message(cake),
        _cake_price_editor_markup(cake),
    )


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
    await run_in_threadpool(telegram.ensure_default_commands)

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
            if data == "noop":
                await _answer_callback(telegram, callback_id, "")
                return {"ok": True}

            parts = data.split(":")
            editable_message_id = message_id if isinstance(message_id, int) else None

            if len(parts) == 2 and parts[0] == "menu":
                action = parts[1]
                if action == "main":
                    await _upsert_menu_message(
                        telegram,
                        int(chat_id),
                        _main_menu_message(),
                        _command_keyboard(),
                        message_id=editable_message_id,
                    )
                elif action == "products":
                    await _show_product_categories(
                        telegram,
                        int(chat_id),
                        db,
                        message_id=editable_message_id,
                    )
                elif action == "orders":
                    await _show_order_filters(
                        telegram,
                        int(chat_id),
                        message_id=editable_message_id,
                    )
                elif action == "cakes":
                    await _show_cake_filters(
                        telegram,
                        int(chat_id),
                        message_id=editable_message_id,
                    )
                else:
                    await _answer_callback(telegram, callback_id, "Unsupported menu action")
                    return {"ok": True}

                await _answer_callback(telegram, callback_id, "Done")
                return {"ok": True}

            if len(parts) == 2 and parts[0] == "cakepricehelp":
                cake_id = uuid.UUID(parts[1])
                await _open_cake_price_editor_via_telegram(
                    telegram,
                    int(chat_id),
                    cake_id,
                    db,
                )
                await _answer_callback(telegram, callback_id, "Edit final price")
                return {"ok": True}

            if len(parts) == 2 and parts[0] == "pcat":
                await _show_products_for_category(
                    telegram,
                    int(chat_id),
                    db,
                    category_value=parts[1],
                )
                await _answer_callback(telegram, callback_id, "Done")
                return {"ok": True}

            if len(parts) == 3 and parts[0] == "flow":
                domain = parts[1]
                status_code = parts[2]
                if domain == "o" and status_code not in ORDER_STATUS_FILTERS:
                    await _answer_callback(telegram, callback_id, "Invalid order status")
                    return {"ok": True}
                if domain == "c" and status_code not in CAKE_STATUS_FILTERS:
                    await _answer_callback(telegram, callback_id, "Invalid cake status")
                    return {"ok": True}
                if domain not in {"o", "c"}:
                    await _answer_callback(telegram, callback_id, "Invalid flow")
                    return {"ok": True}

                await _show_start_calendar(
                    telegram,
                    int(chat_id),
                    domain=domain,
                    status_code=status_code,
                    message_id=editable_message_id,
                )
                await _answer_callback(telegram, callback_id, "Done")
                return {"ok": True}

            if parts and parts[0] == "caln":
                if len(parts) not in {6, 7}:
                    await _answer_callback(telegram, callback_id, "Invalid calendar action")
                    return {"ok": True}

                _, domain, status_code, stage, month_token, *rest = parts
                month_start = _parse_month_token(month_token)
                if month_start is None:
                    await _answer_callback(telegram, callback_id, "Invalid month")
                    return {"ok": True}

                if stage == "s":
                    direction = rest[0]
                    start_date = None
                elif stage == "e" and len(rest) == 2:
                    start_date = _parse_date_token(rest[0])
                    direction = rest[1]
                    if start_date is None:
                        await _answer_callback(telegram, callback_id, "Invalid date")
                        return {"ok": True}
                else:
                    await _answer_callback(telegram, callback_id, "Invalid calendar stage")
                    return {"ok": True}

                if direction not in {"prev", "next"}:
                    await _answer_callback(telegram, callback_id, "Invalid direction")
                    return {"ok": True}

                delta = -1 if direction == "prev" else 1
                next_month = _shift_month(month_start, delta)
                if not _is_date_in_calendar_window(next_month):
                    await _answer_callback(telegram, callback_id, "Date out of range")
                    return {"ok": True}

                status_label = _domain_status_label(domain, status_code)
                stage_label = "start date" if stage == "s" else "end date"
                await _upsert_menu_message(
                    telegram,
                    int(chat_id),
                    f"🗓️ <b>{DOMAIN_LABELS.get(domain, 'Items')} - {status_label}</b>\nSelect <b>{stage_label}</b>.",
                    _calendar_picker_keyboard(
                        domain=domain,
                        status_code=status_code,
                        stage=stage,
                        month_start=next_month,
                        start_date=start_date,
                    ),
                    message_id=editable_message_id,
                )
                await _answer_callback(telegram, callback_id, "Done")
                return {"ok": True}

            if len(parts) == 4 and parts[0] == "cals":
                _, domain, status_code, start_token = parts
                start_date = _parse_date_token(start_token)
                if start_date is None:
                    await _answer_callback(telegram, callback_id, "Invalid start date")
                    return {"ok": True}
                if not _is_date_in_calendar_window(start_date):
                    await _answer_callback(telegram, callback_id, "Date out of range")
                    return {"ok": True}

                status_label = _domain_status_label(domain, status_code)
                await _upsert_menu_message(
                    telegram,
                    int(chat_id),
                    (
                        f"🗓️ <b>{DOMAIN_LABELS.get(domain, 'Items')} - {status_label}</b>\n"
                        f"Start: <b>{start_date.isoformat()}</b>\n"
                        "Select <b>end date</b>."
                    ),
                    _calendar_picker_keyboard(
                        domain=domain,
                        status_code=status_code,
                        stage="e",
                        month_start=_calendar_month_start(start_date),
                        start_date=start_date,
                    ),
                    message_id=editable_message_id,
                )
                await _answer_callback(telegram, callback_id, "Done")
                return {"ok": True}

            if len(parts) == 5 and parts[0] == "cale":
                _, domain, status_code, start_token, end_token = parts
                start_date = _parse_date_token(start_token)
                end_date = _parse_date_token(end_token)
                if start_date is None or end_date is None:
                    await _answer_callback(telegram, callback_id, "Invalid date range")
                    return {"ok": True}
                if end_date < start_date:
                    await _answer_callback(telegram, callback_id, "End date must be after start date")
                    return {"ok": True}
                if not _is_date_in_calendar_window(start_date) or not _is_date_in_calendar_window(end_date):
                    await _answer_callback(telegram, callback_id, "Date out of range")
                    return {"ok": True}

                await _run_status_range(
                    telegram,
                    int(chat_id),
                    db,
                    domain=domain,
                    status_code=status_code,
                    start_date=start_date,
                    end_date=end_date,
                )
                await _answer_callback(telegram, callback_id, "Done")
                return {"ok": True}

            if len(parts) == 3 and parts[0] == "cakeprice":
                _, raw_id, raw_price = parts
                target_id = uuid.UUID(raw_id)
                try:
                    final_price = Decimal(raw_price)
                except ArithmeticError:
                    await _answer_callback(telegram, callback_id, "Invalid price value")
                    return {"ok": True}
                await _answer_callback(telegram, callback_id, "Processing...")
                acting_admin = await _resolve_acting_admin(db)
                result_message = await _set_custom_cake_price_via_telegram(
                    target_id,
                    acting_admin,
                    final_price,
                    db,
                )
                if isinstance(chat_id, int):
                    cake = await CustomCakeService(db).get_custom_cake(target_id)
                    await _send_text(
                        telegram,
                        chat_id,
                        f"💵 {result_message}",
                        _cake_markup(cake) if cake else None,
                    )
                return {"ok": True}

            if len(parts) == 3 and parts[0] == "cake" and parts[1] == "editprice":
                target_id = uuid.UUID(parts[2])
                await _open_cake_price_editor_via_telegram(
                    telegram,
                    int(chat_id),
                    target_id,
                    db,
                )
                await _answer_callback(telegram, callback_id, "Edit final price")
                return {"ok": True}

            if len(parts) == 3:
                domain, action, raw_id = parts
                target_id = uuid.UUID(raw_id)
                is_supported_action = (
                    (domain == "order" and action in {"approve", "reject"})
                    or (domain == "cake" and action in {"approve", "reject"})
                )
                if not is_supported_action:
                    await _answer_callback(telegram, callback_id, "Unsupported action")
                    return {"ok": True}
                await _answer_callback(telegram, callback_id, "Processing...")
                acting_admin = await _resolve_acting_admin(db)

                if domain == "order" and action == "approve":
                    _, result_message = await _approve_order_via_telegram(target_id, acting_admin, db)
                elif domain == "order" and action == "reject":
                    _, result_message = await _reject_order_via_telegram(target_id, acting_admin, db)
                elif domain == "cake" and action == "approve":
                    result_message = await _approve_custom_cake_via_telegram(target_id, acting_admin, db)
                elif domain == "cake" and action == "reject":
                    result_message = await _reject_custom_cake_via_telegram(target_id, acting_admin, db)
                if isinstance(chat_id, int):
                    await _send_text(telegram, chat_id, f"✅ {result_message}")
                    if isinstance(message_id, int):
                        await _clear_buttons(telegram, chat_id, message_id)
                return {"ok": True}

            await _answer_callback(telegram, callback_id, "Unsupported action")
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
    if command in ("/start", "/help"):
        await _send_text(telegram, int(chat_id), _main_menu_message(), _command_keyboard())
        return {"ok": True}

    if command == "/menu":
        await _show_product_categories(telegram, int(chat_id), db)
        return {"ok": True}

    if command == "/order":
        await _show_order_filters(telegram, int(chat_id))
        return {"ok": True}

    if command == "/cake":
        await _show_cake_filters(telegram, int(chat_id))
        return {"ok": True}

    if command == "/cakeprice":
        if len(tokens) != 3:
            await _send_text(
                telegram,
                int(chat_id),
                "Usage: <code>/cakeprice &lt;custom_cake_id&gt; &lt;amount&gt;</code>",
            )
            return {"ok": True}

        try:
            cake_id = uuid.UUID(tokens[1])
            final_price = Decimal(tokens[2])
            acting_admin = await _resolve_acting_admin(db)
            result_message = await _set_custom_cake_price_via_telegram(
                cake_id,
                acting_admin,
                final_price,
                db,
            )
            cake = await CustomCakeService(db).get_custom_cake(cake_id)
            await _send_text(
                telegram,
                int(chat_id),
                f"💵 {result_message}",
                _cake_markup(cake) if cake else None,
            )
        except (ValueError, ArithmeticError):
            await _send_text(
                telegram,
                int(chat_id),
                "Invalid values. Use: <code>/cakeprice &lt;custom_cake_id&gt; &lt;amount&gt;</code>",
            )
        except HTTPException as exc:
            await _send_text(telegram, int(chat_id), f"⚠️ {exc.detail}")
        return {"ok": True}

    await _send_text(telegram, int(chat_id), "Use /menu, /order, /cake, or /cakeprice.")
    return {"ok": True}
