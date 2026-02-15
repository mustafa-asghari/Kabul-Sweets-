"""
Deposit payment service for cake orders.
Handles split payments: deposit (50%) upfront, remainder before pickup.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.business import CakeDeposit
from app.models.order import Order, OrderStatus
from app.services.stripe_service import StripeService

logger = get_logger("deposit_service")

DEFAULT_DEPOSIT_PERCENTAGE = 50


class DepositService:
    """Manages cake deposit payments."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_deposit(
        self,
        order_id: uuid.UUID,
        deposit_percentage: int = DEFAULT_DEPOSIT_PERCENTAGE,
    ) -> dict:
        """
        Create a deposit payment record for a cake order.
        Splits the total into deposit + remaining balance.
        """
        order = await self._get_order(order_id)
        if not order:
            return {"error": "Order not found"}

        if not order.has_cake:
            return {"error": "Deposit payments are only available for cake orders"}

        if order.status != OrderStatus.PENDING:
            return {"error": f"Order is already {order.status.value}"}

        # Check if deposit already exists
        existing = await self.db.execute(
            select(CakeDeposit).where(CakeDeposit.order_id == order_id)
        )
        if existing.scalar_one_or_none():
            return {"error": "Deposit already exists for this order"}

        # Calculate amounts
        deposit_amount = (order.total * Decimal(deposit_percentage)) / Decimal(100)
        remaining = order.total - deposit_amount

        deposit = CakeDeposit(
            order_id=order_id,
            deposit_amount=deposit_amount.quantize(Decimal("0.01")),
            remaining_amount=remaining.quantize(Decimal("0.01")),
            deposit_percentage=deposit_percentage,
        )
        self.db.add(deposit)
        await self.db.flush()

        logger.info(
            "Deposit created for order %s: $%s deposit, $%s remaining",
            order.order_number, deposit_amount, remaining,
        )

        return {
            "id": str(deposit.id),
            "order_id": str(order_id),
            "order_number": order.order_number,
            "total": str(order.total),
            "deposit_amount": str(deposit.deposit_amount),
            "remaining_amount": str(deposit.remaining_amount),
            "deposit_percentage": deposit.deposit_percentage,
            "deposit_paid": False,
            "final_paid": False,
        }

    async def checkout_deposit(self, order_id: uuid.UUID, customer_email: str) -> dict:
        """Create a Stripe checkout for the deposit portion."""
        deposit = await self._get_deposit(order_id)
        if not deposit:
            return {"error": "No deposit found for this order"}

        if deposit.deposit_paid:
            return {"error": "Deposit already paid"}

        order = await self._get_order(order_id)
        result = await StripeService.create_checkout_session(
            order_id=str(order_id),
            order_number=f"{order.order_number}-DEPOSIT",
            amount=deposit.deposit_amount,
            currency="aud",
            customer_email=customer_email,
            line_items_description=f"Cake deposit ({deposit.deposit_percentage}%) for {order.order_number}",
        )

        deposit.deposit_payment_intent = result.get("session_id")
        await self.db.flush()

        return {
            "checkout_url": result["checkout_url"],
            "session_id": result["session_id"],
            "amount": str(deposit.deposit_amount),
            "type": "deposit",
        }

    async def checkout_remaining(self, order_id: uuid.UUID, customer_email: str) -> dict:
        """Create a Stripe checkout for the remaining balance."""
        deposit = await self._get_deposit(order_id)
        if not deposit:
            return {"error": "No deposit found for this order"}

        if not deposit.deposit_paid:
            return {"error": "Deposit must be paid first"}

        if deposit.final_paid:
            return {"error": "Final payment already completed"}

        order = await self._get_order(order_id)
        result = await StripeService.create_checkout_session(
            order_id=str(order_id),
            order_number=f"{order.order_number}-FINAL",
            amount=deposit.remaining_amount,
            currency="aud",
            customer_email=customer_email,
            line_items_description=f"Remaining balance for {order.order_number}",
        )

        deposit.final_payment_intent = result.get("session_id")
        await self.db.flush()

        return {
            "checkout_url": result["checkout_url"],
            "session_id": result["session_id"],
            "amount": str(deposit.remaining_amount),
            "type": "final",
        }

    async def mark_deposit_paid(self, order_id: uuid.UUID) -> dict:
        """Mark deposit as paid (called by webhook)."""
        deposit = await self._get_deposit(order_id)
        if not deposit:
            return {"error": "No deposit found"}

        deposit.deposit_paid = True
        deposit.deposit_paid_at = datetime.now(timezone.utc)

        # Update order status
        order = await self._get_order(order_id)
        if order:
            order.status = OrderStatus.CONFIRMED
        await self.db.flush()

        logger.info("Deposit paid for order %s", order.order_number if order else order_id)
        return {"status": "deposit_paid", "order_id": str(order_id)}

    async def mark_final_paid(self, order_id: uuid.UUID) -> dict:
        """Mark final payment as paid (called by webhook)."""
        deposit = await self._get_deposit(order_id)
        if not deposit:
            return {"error": "No deposit found"}

        deposit.final_paid = True
        deposit.final_paid_at = datetime.now(timezone.utc)

        order = await self._get_order(order_id)
        if order:
            order.status = OrderStatus.PAID
            order.paid_at = datetime.now(timezone.utc)
        await self.db.flush()

        logger.info("Final payment complete for order %s", order.order_number if order else order_id)
        return {"status": "fully_paid", "order_id": str(order_id)}

    async def get_deposit_status(self, order_id: uuid.UUID) -> dict | None:
        """Get deposit payment status for an order."""
        deposit = await self._get_deposit(order_id)
        if not deposit:
            return None

        order = await self._get_order(order_id)
        return {
            "id": str(deposit.id),
            "order_id": str(order_id),
            "order_number": order.order_number if order else None,
            "total": str(order.total) if order else None,
            "deposit_amount": str(deposit.deposit_amount),
            "remaining_amount": str(deposit.remaining_amount),
            "deposit_percentage": deposit.deposit_percentage,
            "deposit_paid": deposit.deposit_paid,
            "deposit_paid_at": deposit.deposit_paid_at.isoformat() if deposit.deposit_paid_at else None,
            "final_paid": deposit.final_paid,
            "final_paid_at": deposit.final_paid_at.isoformat() if deposit.final_paid_at else None,
            "fully_paid": deposit.deposit_paid and deposit.final_paid,
        }

    async def _get_order(self, order_id: uuid.UUID) -> Order | None:
        result = await self.db.execute(select(Order).where(Order.id == order_id))
        return result.scalar_one_or_none()

    async def _get_deposit(self, order_id: uuid.UUID) -> CakeDeposit | None:
        result = await self.db.execute(
            select(CakeDeposit).where(CakeDeposit.order_id == order_id)
        )
        return result.scalar_one_or_none()
