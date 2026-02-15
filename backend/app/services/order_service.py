"""
Order service — handles order lifecycle, validation, and inventory reservation.
"""

import random
import string
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.order import Order, OrderItem, OrderStatus, Payment, PaymentStatus
from app.models.product import Product, ProductVariant
from app.schemas.order import OrderCreate, OrderUpdateAdmin

logger = get_logger("order_service")

# Australian GST rate
GST_RATE = Decimal("0.10")


def _generate_order_number() -> str:
    """Generate a unique order number like KS-20240215-A7X3."""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    rand_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"KS-{date_part}-{rand_part}"


class OrderService:
    """Handles order creation, validation, and lifecycle management."""

    def __init__(self, db: AsyncSession):
        self.db = db

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

        # Validate items and calculate pricing
        order_items = []
        subtotal = Decimal("0.00")
        has_cake = False

        for item_data in data.items:
            product, variant, unit_price = await self._validate_order_item(item_data)

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

            # Reserve inventory (reduce stock)
            if variant:
                variant.stock_quantity = max(0, variant.stock_quantity - item_data.quantity)
                variant.is_in_stock = variant.stock_quantity > 0

        # Calculate totals
        tax_amount = (subtotal * GST_RATE).quantize(Decimal("0.01"))
        total = subtotal + tax_amount

        # Create order
        order = Order(
            order_number=order_number,
            customer_id=customer_id,
            status=OrderStatus.PENDING,
            customer_name=data.customer_name,
            customer_email=data.customer_email,
            customer_phone=data.customer_phone,
            pickup_date=data.pickup_date,
            pickup_time_slot=data.pickup_time_slot,
            cake_message=data.cake_message,
            has_cake=has_cake,
            special_instructions=data.special_instructions,
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=Decimal("0.00"),
            total=total,
            discount_code=data.discount_code,
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
                raise ValueError(
                    f"'{product.name} - {variant.name}' is out of stock or insufficient quantity"
                )
            unit_price = variant.price

        return product, variant, unit_price

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
            # Restore inventory for cancelled orders
            for item in order.items:
                if item.variant_id:
                    result = await self.db.execute(
                        select(ProductVariant).where(ProductVariant.id == item.variant_id)
                    )
                    variant = result.scalar_one_or_none()
                    if variant:
                        variant.stock_quantity += item.quantity
                        variant.is_in_stock = True
            logger.info("Inventory restored for cancelled order: %s", order.order_number)

    # ── Payment Status (called by Stripe webhook) ────────────────────────
    async def mark_order_paid(
        self,
        order_id: uuid.UUID,
        stripe_payment_intent_id: str,
        stripe_checkout_session_id: str | None = None,
        webhook_data: dict | None = None,
    ) -> Order | None:
        """Mark an order as paid (called by Stripe webhook)."""
        order = await self.get_order(order_id)
        if not order:
            return None

        order.status = OrderStatus.PAID
        order.paid_at = datetime.now(timezone.utc)

        if order.payment:
            order.payment.status = PaymentStatus.SUCCEEDED
            order.payment.stripe_payment_intent_id = stripe_payment_intent_id
            order.payment.stripe_checkout_session_id = stripe_checkout_session_id
            order.payment.webhook_data = webhook_data

        await self.db.flush()
        await self.db.refresh(order)
        logger.info("Order %s marked as PAID", order.order_number)
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

        # Restore inventory on failed payment
        for item in order.items:
            if item.variant_id:
                result = await self.db.execute(
                    select(ProductVariant).where(ProductVariant.id == item.variant_id)
                )
                variant = result.scalar_one_or_none()
                if variant:
                    variant.stock_quantity += item.quantity
                    variant.is_in_stock = True

        await self.db.flush()
        logger.warning("Payment failed for order %s: %s", order.order_number, failure_message)
        return order
