"""
Cart and abandoned cart recovery service.
Tracks customer carts, detects abandonment, queues recovery emails/SMS.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, update, delete as sql_delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.cart import Cart, CartItem, CartRecoveryAttempt, CartStatus

logger = get_logger("cart_service")

# Recovery timing rules
RECOVERY_DELAYS = [
    {"delay_hours": 1, "channel": "email", "template": "gentle_reminder"},
    {"delay_hours": 24, "channel": "email", "template": "urgency"},
    {"delay_hours": 72, "channel": "sms", "template": "last_chance"},
]


class CartService:
    """Manages shopping carts and abandoned cart recovery."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Cart CRUD ────────────────────────────────────────────────────────────

    async def get_or_create_cart(self, customer_id: uuid.UUID) -> Cart:
        """Get active cart or create a new one."""
        result = await self.db.execute(
            select(Cart).where(
                Cart.customer_id == customer_id,
                Cart.status == CartStatus.ACTIVE,
            )
        )
        cart = result.scalar_one_or_none()

        if not cart:
            cart = Cart(customer_id=customer_id)
            self.db.add(cart)
            await self.db.flush()

        return cart

    async def add_item(
        self,
        customer_id: uuid.UUID,
        product_id: uuid.UUID,
        variant_id: uuid.UUID | None = None,
        quantity: int = 1,
    ) -> dict:
        """Add item to cart. Updates quantity if already exists."""
        cart = await self.get_or_create_cart(customer_id)

        # Check if item already in cart
        result = await self.db.execute(
            select(CartItem).where(
                CartItem.cart_id == cart.id,
                CartItem.product_id == product_id,
                CartItem.variant_id == variant_id if variant_id else CartItem.variant_id.is_(None),
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.quantity += quantity
            existing.updated_at = datetime.now(timezone.utc)
        else:
            item = CartItem(
                cart_id=cart.id,
                product_id=product_id,
                variant_id=variant_id,
                quantity=quantity,
            )
            self.db.add(item)

        cart.last_activity = datetime.now(timezone.utc)
        await self.db.flush()

        return await self._cart_to_dict(cart)

    async def update_item(
        self,
        customer_id: uuid.UUID,
        item_id: uuid.UUID,
        quantity: int,
    ) -> dict:
        """Update cart item quantity. Removes if quantity is 0."""
        cart = await self.get_or_create_cart(customer_id)
        result = await self.db.execute(
            select(CartItem).where(
                CartItem.id == item_id,
                CartItem.cart_id == cart.id,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            return {"error": "Item not found in cart"}

        if quantity <= 0:
            await self.db.delete(item)
        else:
            item.quantity = quantity
            item.updated_at = datetime.now(timezone.utc)

        cart.last_activity = datetime.now(timezone.utc)
        await self.db.flush()
        return await self._cart_to_dict(cart)

    async def remove_item(self, customer_id: uuid.UUID, item_id: uuid.UUID) -> dict:
        """Remove item from cart using direct SQL to avoid ORM identity-map issues."""
        cart = await self.get_or_create_cart(customer_id)

        result = await self.db.execute(
            sql_delete(CartItem)
            .where(
                CartItem.id == item_id,
                CartItem.cart_id == cart.id,
            )
            .returning(CartItem.id)
        )
        deleted = result.fetchone()
        if not deleted:
            return {"error": "Item not found in cart"}

        # Expire identity map so _cart_to_dict reads fresh state from DB
        self.db.expire_all()
        cart.last_activity = datetime.now(timezone.utc)
        await self.db.flush()
        return await self._cart_to_dict(cart)

    async def get_cart(self, customer_id: uuid.UUID) -> dict:
        """Get customer's active cart."""
        cart = await self.get_or_create_cart(customer_id)
        return await self._cart_to_dict(cart)

    async def clear_cart(self, customer_id: uuid.UUID) -> dict:
        """Clear all items from the cart."""
        cart = await self.get_or_create_cart(customer_id)
        result = await self.db.execute(
            select(CartItem).where(CartItem.cart_id == cart.id)
        )
        for item in result.scalars().all():
            await self.db.delete(item)

        cart.last_activity = datetime.now(timezone.utc)
        await self.db.flush()
        return {"message": "Cart cleared", "cart_id": str(cart.id)}

    async def mark_converted(self, customer_id: uuid.UUID, order_id: uuid.UUID) -> None:
        """Mark cart as converted to order."""
        result = await self.db.execute(
            select(Cart).where(
                Cart.customer_id == customer_id,
                Cart.status == CartStatus.ACTIVE,
            )
        )
        cart = result.scalar_one_or_none()
        if cart:
            cart.status = CartStatus.CONVERTED
            cart.converted_order_id = order_id
            await self.db.flush()

    # ── Abandoned Cart Recovery ──────────────────────────────────────────────

    async def find_abandoned_carts(self, min_age_hours: int = 1) -> list[dict]:
        """
        Find carts that have been inactive for at least min_age_hours.
        Only returns carts with items that haven't already been recovered.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=min_age_hours)

        result = await self.db.execute(
            select(Cart).where(
                Cart.status == CartStatus.ACTIVE,
                Cart.last_activity < cutoff,
                Cart.recovery_email_sent == False,  # noqa: E712
            )
        )
        carts = result.scalars().all()

        abandoned = []
        for cart in carts:
            items = await self.db.execute(
                select(CartItem).where(CartItem.cart_id == cart.id)
            )
            cart_items = items.scalars().all()
            if cart_items:  # Only count carts with items
                abandoned.append({
                    "cart_id": str(cart.id),
                    "customer_id": str(cart.customer_id),
                    "item_count": len(cart_items),
                    "last_activity": cart.last_activity.isoformat(),
                    "hours_abandoned": int(
                        (datetime.now(timezone.utc) - cart.last_activity).total_seconds() / 3600
                    ),
                })

        return abandoned

    async def send_recovery(self, cart_id: uuid.UUID, channel: str, template: str) -> dict:
        """
        Record a recovery attempt and queue the notification.
        """
        result = await self.db.execute(select(Cart).where(Cart.id == cart_id))
        cart = result.scalar_one_or_none()
        if not cart:
            return {"error": "Cart not found"}

        attempt = CartRecoveryAttempt(
            cart_id=cart_id,
            channel=channel,
            template=template,
        )
        self.db.add(attempt)

        if channel == "email":
            cart.recovery_email_sent = True
        elif channel == "sms":
            cart.recovery_sms_sent = True

        await self.db.flush()

        logger.info(
            "Recovery %s sent for cart %s (template: %s)",
            channel, cart_id, template,
        )

        return {
            "attempt_id": str(attempt.id),
            "cart_id": str(cart_id),
            "channel": channel,
            "template": template,
            "sent_at": attempt.sent_at.isoformat(),
        }

    async def get_recovery_stats(self) -> dict:
        """Get cart recovery statistics."""
        total_carts = await self.db.execute(select(func.count(Cart.id)))
        active = await self.db.execute(
            select(func.count(Cart.id)).where(Cart.status == CartStatus.ACTIVE)
        )
        abandoned = await self.db.execute(
            select(func.count(Cart.id)).where(
                Cart.status == CartStatus.ACTIVE,
                Cart.recovery_email_sent == True,  # noqa: E712
            )
        )
        converted = await self.db.execute(
            select(func.count(Cart.id)).where(Cart.status == CartStatus.CONVERTED)
        )
        recovered = await self.db.execute(
            select(func.count(Cart.id)).where(
                Cart.status == CartStatus.CONVERTED,
                Cart.recovery_email_sent == True,  # noqa: E712
            )
        )

        total = total_carts.scalar() or 0
        conv = converted.scalar() or 0

        return {
            "total_carts": total,
            "active_carts": active.scalar() or 0,
            "abandoned_carts_contacted": abandoned.scalar() or 0,
            "converted_carts": conv,
            "recovered_carts": recovered.scalar() or 0,
            "conversion_rate": f"{(conv / total * 100):.1f}%" if total > 0 else "0%",
        }

    async def _cart_to_dict(self, cart: Cart) -> dict:
        """Convert cart to dictionary, skipping orphaned items (deleted products)."""
        from app.models.product import Product  # local import to avoid circular
        result = await self.db.execute(
            select(CartItem)
            .join(Product, Product.id == CartItem.product_id)
            .where(CartItem.cart_id == cart.id)
        )
        items = result.scalars().all()

        return {
            "id": str(cart.id),
            "customer_id": str(cart.customer_id),
            "status": cart.status.value,
            "items": [
                {
                    "id": str(item.id),
                    "product_id": str(item.product_id),
                    "variant_id": str(item.variant_id) if item.variant_id else None,
                    "quantity": item.quantity,
                    "added_at": item.added_at.isoformat(),
                }
                for item in items
            ],
            "item_count": len(items),
            "last_activity": cart.last_activity.isoformat(),
        }
