"""
Order service — handles order lifecycle, validation, and inventory reservation.
"""

import random
import re
import string
import uuid
from datetime import datetime, time, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.core.config import get_settings
from app.models.order import Order, OrderItem, OrderStatus, Payment, PaymentStatus
from app.models.product import Product, ProductVariant
from app.schemas.order import OrderCreate, OrderUpdateAdmin

logger = get_logger("order_service")
settings = get_settings()

# Australian GST rate
GST_RATE = Decimal("0.10")
PICKUP_BUFFER_HOURS = 1
BUSINESS_HOURS_BY_WEEKDAY: dict[int, tuple[int, int]] = {
    0: (9, 18),  # Monday
    1: (9, 18),  # Tuesday
    2: (9, 18),  # Wednesday
    3: (9, 18),  # Thursday
    4: (9, 19),  # Friday
    5: (9, 19),  # Saturday
    6: (9, 18),  # Sunday
}
TIME_SLOT_24H_REGEX = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*$")
TIME_SLOT_12H_REGEX = re.compile(
    r"^\s*(\d{1,2}):(\d{2})\s*([aApP][mM])\s*-\s*(\d{1,2}):(\d{2})\s*([aApP][mM])\s*$"
)


def _generate_order_number() -> str:
    """Generate a unique order number like KS-20240215-A7X3."""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    rand_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"KS-{date_part}-{rand_part}"


class OrderService:
    """Handles order creation, validation, and lifecycle management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _business_timezone():
        tz_name = (settings.BUSINESS_TIMEZONE or "Australia/Sydney").strip()
        try:
            return ZoneInfo(tz_name)
        except Exception:
            logger.warning("Invalid BUSINESS_TIMEZONE '%s'. Falling back to UTC.", tz_name)
            return timezone.utc

    @staticmethod
    def _to_24h(hour_12: int, am_pm: str) -> int:
        suffix = am_pm.lower()
        hour = hour_12 % 12
        if suffix == "pm":
            hour += 12
        return hour

    @classmethod
    def _parse_pickup_slot_hours(cls, time_slot: str) -> tuple[int, int]:
        slot = (time_slot or "").strip()
        if not slot:
            raise ValueError("Pickup time slot cannot be empty.")

        m24 = TIME_SLOT_24H_REGEX.match(slot)
        if m24:
            start_hour = int(m24.group(1))
            start_minute = int(m24.group(2))
            end_hour = int(m24.group(3))
            end_minute = int(m24.group(4))
        else:
            m12 = TIME_SLOT_12H_REGEX.match(slot)
            if not m12:
                raise ValueError("Pickup time slot must be in format HH:00-HH:00.")
            start_hour = cls._to_24h(int(m12.group(1)), m12.group(3))
            start_minute = int(m12.group(2))
            end_hour = cls._to_24h(int(m12.group(4)), m12.group(6))
            end_minute = int(m12.group(5))

        if not (0 <= start_hour <= 23 and 0 <= end_hour <= 24):
            raise ValueError("Pickup time slot hour is invalid.")
        if start_minute != 0 or end_minute != 0:
            raise ValueError("Pickup time slot must start/end exactly on the hour.")
        if end_hour - start_hour != 1:
            raise ValueError("Pickup time slot must be exactly 1 hour.")

        return start_hour, end_hour

    def _validate_pickup_schedule(
        self,
        pickup_date: datetime | None,
        pickup_time_slot: str | None,
    ) -> tuple[datetime, str]:
        if not pickup_date:
            raise ValueError("Pickup date is required.")
        if not (pickup_time_slot or "").strip():
            raise ValueError("Pickup time slot is required.")

        tz = self._business_timezone()
        now_local = datetime.now(tz)
        pickup_local = (
            pickup_date.replace(tzinfo=tz)
            if pickup_date.tzinfo is None
            else pickup_date.astimezone(tz)
        )
        pickup_day = pickup_local.date()
        today_local = now_local.date()

        if pickup_day < today_local:
            raise ValueError("Pickup date cannot be in the past.")

        normalized_pickup_date_local = datetime.combine(
            pickup_day,
            time(hour=12, minute=0),
            tzinfo=tz,
        )
        normalized_pickup_date_utc = normalized_pickup_date_local.astimezone(timezone.utc)

        normalized_input_slot = pickup_time_slot.strip()
        start_hour, end_hour = self._parse_pickup_slot_hours(normalized_input_slot)
        open_hour, close_hour = BUSINESS_HOURS_BY_WEEKDAY.get(
            pickup_day.weekday(),
            BUSINESS_HOURS_BY_WEEKDAY[0],
        )

        earliest_pickup_hour = open_hour + PICKUP_BUFFER_HOURS
        if pickup_day == today_local:
            next_whole_hour = now_local.hour
            if now_local.minute > 0 or now_local.second > 0 or now_local.microsecond > 0:
                next_whole_hour += 1
            earliest_pickup_hour = max(earliest_pickup_hour, next_whole_hour)

        if start_hour < (open_hour + PICKUP_BUFFER_HOURS):
            raise ValueError(
                f"Pickup starts at {open_hour + PICKUP_BUFFER_HOURS:02d}:00 for this day."
            )
        if start_hour < earliest_pickup_hour:
            raise ValueError("Pickup time slot is in the past. Please choose a future slot.")
        if end_hour > close_hour:
            raise ValueError(
                f"Pickup time must be within business hours and end by {close_hour:02d}:00."
            )

        normalized_slot = f"{start_hour:02d}:00-{end_hour:02d}:00"
        return normalized_pickup_date_utc, normalized_slot

    async def _restore_inventory_for_order(self, order: Order) -> None:
        """Put reserved variant stock back when an unpaid order is cancelled/deleted."""
        for item in order.items:
            if not item.variant_id:
                continue

            result = await self.db.execute(
                select(ProductVariant).where(ProductVariant.id == item.variant_id)
            )
            variant = result.scalar_one_or_none()
            if variant:
                variant.stock_quantity += item.quantity
                variant.is_in_stock = True

    # ── Order Creation ───────────────────────────────────────────────────
    async def create_order(
        self,
        data: OrderCreate,
        customer_id: uuid.UUID | None = None,
    ) -> Order:
        """
        Create a new order with validation and inventory reservation.
        """
        # Generate unique order number
        order_number = _generate_order_number()
        while await self._order_number_exists(order_number):
            order_number = _generate_order_number()

        pickup_date, pickup_time_slot = self._validate_pickup_schedule(
            data.pickup_date,
            data.pickup_time_slot,
        )

        # Validate items and calculate pricing
        order_items = []
        subtotal = Decimal("0.00")
        has_cake = False
        inventory_warnings: list[str] = []

        for item_data in data.items:
            product, variant, unit_price, inventory_warning = await self._validate_order_item(
                item_data
            )

            if product.is_cake:
                has_cake = True

            line_total = unit_price * item_data.quantity

            order_item = OrderItem(
                product_id=product.id,
                variant_id=variant.id if variant else None,
                product_name=product.name,
                variant_name=variant.name if variant else None,
                unit_price=unit_price,
                quantity=item_data.quantity,
                line_total=line_total,
                cake_message=item_data.cake_message,
            )
            order_items.append(order_item)
            subtotal += line_total

            if inventory_warning:
                inventory_warnings.append(inventory_warning)

            # Reserve inventory while keeping stock non-negative.
            # Any shortage is captured in admin notes for manual review.
            if variant:
                variant.stock_quantity = max(0, variant.stock_quantity - item_data.quantity)
                variant.is_in_stock = variant.stock_quantity > 0

        # Calculate totals.
        # Prices are GST-inclusive (Australian standard), so extract the GST
        # component already embedded in the price rather than adding it on top.
        # tax_amount = subtotal - (subtotal / 1.10)  →  the GST portion included.
        # total = subtotal  →  unchanged, no extra charge added.
        tax_amount = (subtotal - (subtotal / (Decimal("1") + GST_RATE))).quantize(Decimal("0.01"))
        total = subtotal

        # Create order
        admin_notes = None
        if inventory_warnings:
            admin_notes = "Inventory check required before approval:\n" + "\n".join(
                f"- {warning}" for warning in inventory_warnings
            )

        order = Order(
            order_number=order_number,
            customer_id=customer_id,
            status=OrderStatus.PENDING,
            customer_name=data.customer_name,
            customer_email=data.customer_email,
            customer_phone=data.customer_phone,
            pickup_date=pickup_date,
            pickup_time_slot=pickup_time_slot,
            cake_message=data.cake_message,
            has_cake=has_cake,
            special_instructions=data.special_instructions,
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=Decimal("0.00"),
            total=total,
            discount_code=data.discount_code,
            admin_notes=admin_notes,
        )
        self.db.add(order)
        await self.db.flush()

        # Attach items
        for item in order_items:
            item.order_id = order.id
            self.db.add(item)

        # Create payment record (pending)
        payment = Payment(
            order_id=order.id,
            amount=total,
            currency="aud",
            status=PaymentStatus.PENDING,
        )
        self.db.add(payment)

        await self.db.flush()
        await self.db.refresh(order)

        logger.info("Order created: %s (total: $%s)", order_number, total)
        return order

    async def _validate_order_item(self, item_data) -> tuple:
        """Validate a single order item: check product exists, is active, and in stock."""
        result = await self.db.execute(
            select(Product)
            .options(selectinload(Product.variants))
            .where(Product.id == item_data.product_id)
        )
        product = result.scalar_one_or_none()

        if not product or not product.is_active:
            raise ValueError(f"Product not found or inactive: {item_data.product_id}")

        # Check max per order
        if product.max_per_order and item_data.quantity > product.max_per_order:
            raise ValueError(
                f"Maximum {product.max_per_order} of '{product.name}' per order"
            )

        variant = None
        unit_price = product.base_price
        inventory_warning: str | None = None

        if item_data.variant_id:
            result = await self.db.execute(
                select(ProductVariant).where(
                    ProductVariant.id == item_data.variant_id,
                    ProductVariant.product_id == product.id,
                )
            )
            variant = result.scalar_one_or_none()
            if not variant or not variant.is_active:
                raise ValueError(f"Variant not found or inactive: {item_data.variant_id}")

            if not variant.is_in_stock or variant.stock_quantity < item_data.quantity:
                inventory_warning = (
                    f"{product.name} - {variant.name}: requested {item_data.quantity}, "
                    f"available {max(variant.stock_quantity, 0)}"
                )
            unit_price = variant.price

        return product, variant, unit_price, inventory_warning

    async def _order_number_exists(self, order_number: str) -> bool:
        result = await self.db.execute(
            select(Order).where(Order.order_number == order_number)
        )
        return result.scalar_one_or_none() is not None

    # ── Order Retrieval ──────────────────────────────────────────────────
    async def get_order(self, order_id: uuid.UUID) -> Order | None:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.payment))
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_order_by_number(self, order_number: str) -> Order | None:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.payment))
            .where(Order.order_number == order_number)
        )
        return result.scalar_one_or_none()

    async def get_customer_orders(
        self,
        customer_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Order]:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.payment))
            .where(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_orders(
        self,
        status: str | None = None,
        has_cake: bool | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Order]:
        """List orders with filters (admin)."""
        query = (
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.payment))
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        if status:
            query = query.where(Order.status == status)
        if has_cake is not None:
            query = query.where(Order.has_cake == has_cake)
        if date_from:
            query = query.where(Order.created_at >= date_from)
        if date_to:
            query = query.where(Order.created_at <= date_to)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_orders(self, status: str | None = None) -> int:
        query = select(func.count(Order.id))
        if status:
            query = query.where(Order.status == status)
        result = await self.db.execute(query)
        return result.scalar() or 0

    # ── Order Status Management ──────────────────────────────────────────
    async def update_order_admin(
        self,
        order_id: uuid.UUID,
        data: OrderUpdateAdmin,
    ) -> Order | None:
        """Admin update to an order (status, pickup, notes)."""
        order = await self.get_order(order_id)
        if not order:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        if "pickup_date" in update_fields or "pickup_time_slot" in update_fields:
            next_pickup_date = update_fields.get("pickup_date", order.pickup_date)
            next_pickup_slot = update_fields.get("pickup_time_slot", order.pickup_time_slot)
            validated_date, validated_slot = self._validate_pickup_schedule(
                next_pickup_date,
                next_pickup_slot,
            )
            update_fields["pickup_date"] = validated_date
            update_fields["pickup_time_slot"] = validated_slot

        for field, value in update_fields.items():
            if field == "status" and value is not None:
                new_status = OrderStatus(value)
                await self._handle_status_transition(order, new_status)
                order.status = new_status
            else:
                setattr(order, field, value)

        await self.db.flush()
        await self.db.refresh(order)
        logger.info("Order %s updated: %s", order.order_number, update_fields)
        return order

    async def _handle_status_transition(self, order: Order, new_status: OrderStatus):
        """Handle side effects of status transitions."""
        if new_status == OrderStatus.COMPLETED:
            order.completed_at = datetime.now(timezone.utc)
        elif new_status == OrderStatus.CANCELLED:
            await self._restore_inventory_for_order(order)
            logger.info("Inventory restored for cancelled order: %s", order.order_number)

    async def reject_order_after_authorization(
        self,
        order_id: uuid.UUID,
        reason: str,
    ) -> Order | None:
        """Reject an order after authorization and restore stock."""
        order = await self.get_order(order_id)
        if not order:
            return None

        if order.status not in (OrderStatus.PENDING_APPROVAL, OrderStatus.PENDING):
            return order

        await self._handle_status_transition(order, OrderStatus.CANCELLED)
        order.status = OrderStatus.CANCELLED
        existing_notes = order.admin_notes or ""
        order.admin_notes = (
            f"{existing_notes}\nRejected: {reason}".strip()
            if existing_notes
            else f"Rejected: {reason}"
        )

        if order.payment:
            order.payment.status = PaymentStatus.FAILED
            order.payment.failure_message = reason

        await self.db.flush()
        await self.db.refresh(order)
        logger.info("Order %s rejected by admin: %s", order.order_number, reason)
        return order

    async def mark_order_pending_approval(
        self,
        order_id: uuid.UUID,
        stripe_payment_intent_id: str | None = None,
        stripe_checkout_session_id: str | None = None,
        webhook_data: dict | None = None,
    ) -> Order | None:
        """Mark order as authorized and waiting for admin approval."""
        order = await self.get_order(order_id)
        if not order:
            return None

        order.status = OrderStatus.PENDING_APPROVAL
        if order.payment:
            order.payment.status = PaymentStatus.PENDING
            if stripe_payment_intent_id:
                order.payment.stripe_payment_intent_id = stripe_payment_intent_id
            if stripe_checkout_session_id:
                order.payment.stripe_checkout_session_id = stripe_checkout_session_id
            order.payment.webhook_data = webhook_data

        await self.db.flush()
        await self.db.refresh(order)
        logger.info("Order %s set to pending approval", order.order_number)
        return order

    # ── Payment Status (called by Stripe webhook or admin capture) ──────
    async def mark_order_paid(
        self,
        order_id: uuid.UUID,
        stripe_payment_intent_id: str,
        stripe_checkout_session_id: str | None = None,
        webhook_data: dict | None = None,
        status_after_payment: OrderStatus = OrderStatus.CONFIRMED,
    ) -> Order | None:
        """Mark an order as paid after successful capture."""
        order = await self.get_order(order_id)
        if not order:
            return None

        order.status = status_after_payment
        order.paid_at = datetime.now(timezone.utc)

        if order.payment:
            order.payment.stripe_payment_intent_id = stripe_payment_intent_id
            order.payment.stripe_checkout_session_id = stripe_checkout_session_id
            order.payment.webhook_data = webhook_data
            order.payment.status = PaymentStatus.SUCCEEDED

        await self.db.flush()
        await self.db.refresh(order)
        logger.info("Order %s marked paid with status %s", order.order_number, order.status.value)
        return order

    async def mark_payment_failed(
        self,
        order_id: uuid.UUID,
        failure_code: str | None = None,
        failure_message: str | None = None,
    ) -> Order | None:
        """Mark a payment as failed."""
        order = await self.get_order(order_id)
        if not order:
            return None

        if order.payment:
            order.payment.status = PaymentStatus.FAILED
            order.payment.failure_code = failure_code
            order.payment.failure_message = failure_message

        await self._restore_inventory_for_order(order)

        await self.db.flush()
        logger.warning("Payment failed for order %s: %s", order.order_number, failure_message)
        return order

    async def delete_customer_unpaid_order(
        self,
        order_id: uuid.UUID,
        customer_id: uuid.UUID,
    ) -> dict:
        """Hard-delete a customer order before admin approval and release reserved inventory."""
        order = await self.get_order(order_id)
        if not order or order.customer_id != customer_id:
            return {"error": "Order not found", "status_code": 404}

        deletable_statuses = {OrderStatus.PENDING}
        if order.status not in deletable_statuses:
            return {"error": "Orders cannot be deleted after admin approval.", "status_code": 400}

        if order.payment and order.payment.status == PaymentStatus.SUCCEEDED:
            return {"error": "Paid orders cannot be deleted.", "status_code": 400}

        payment_intent_id = order.payment.stripe_payment_intent_id if order.payment else None
        if payment_intent_id and order.payment and order.payment.status == PaymentStatus.PENDING:
            try:
                from app.services.stripe_service import StripeService

                await StripeService.cancel_payment_intent(payment_intent_id)
            except Exception as exc:
                logger.warning(
                    "Failed to cancel payment intent while deleting %s: %s",
                    order.order_number,
                    str(exc),
                )

        await self._restore_inventory_for_order(order)
        order_number = order.order_number

        await self.db.delete(order)
        await self.db.flush()

        logger.info("Customer %s deleted unpaid order %s", customer_id, order_number)
        return {
            "order_id": str(order_id),
            "order_number": order_number,
            "deleted": True,
        }
