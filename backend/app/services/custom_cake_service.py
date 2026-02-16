"""
Custom Cake Service — Phase ML-5.
Handles the full custom cake lifecycle:
Submission → Admin Review → Price/Serving Prediction → Approval → Payment → Production.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.ml import CustomCake, CustomCakeStatus, DecorationComplexity
from app.services.ml_service import CakePricingService, ServingEstimationService

logger = get_logger("custom_cake_service")


class CustomCakeService:
    """Manages the custom cake submission and approval workflow."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _build_template_descriptions(
        self,
        flavor: str,
        decoration_description: str | None,
        event_type: str | None,
    ) -> dict:
        decoration = decoration_description.strip() if decoration_description else "classic"
        event = event_type.strip() if event_type else "special occasions"

        short = (
            f"A handcrafted {flavor} custom cake made for {event}."
        )
        long = (
            f"Our {flavor} custom cake is prepared fresh to order with careful attention to detail. "
            f"This design features {decoration} decoration and is tailored to your event needs."
        )
        seo = (
            f"Custom {flavor} cake by Kabul Sweets. Made fresh for {event} with personalized design options."
        )[:155]

        return {
            "short": short,
            "long": long,
            "seo": seo,
            "generated_by": "template",
            "model": None,
        }

    async def submit_custom_cake(
        self,
        customer_id: uuid.UUID,
        flavor: str,
        diameter_inches: float,
        height_inches: float = 4.0,
        layers: int = 1,
        shape: str = "round",
        decoration_complexity: str = "moderate",
        decoration_description: str | None = None,
        cake_message: str | None = None,
        event_type: str | None = None,
        is_rush_order: bool = False,
        ingredients: dict | None = None,
        allergen_notes: str | None = None,
        reference_images: list | None = None,
        requested_date: datetime | None = None,
        time_slot: str | None = None,
    ) -> dict:
        """
        Submit a custom cake request.
        Auto-predicts price and servings, then stores template descriptions.
        """
        complexity = DecorationComplexity(decoration_complexity)

        # Create the custom cake record
        cake = CustomCake(
            customer_id=customer_id,
            flavor=flavor,
            diameter_inches=diameter_inches,
            height_inches=height_inches,
            layers=layers,
            shape=shape,
            decoration_complexity=complexity,
            decoration_description=decoration_description,
            cake_message=cake_message,
            event_type=event_type,
            is_rush_order=is_rush_order,
            ingredients=ingredients or {},
            allergen_notes=allergen_notes,
            reference_images=reference_images or [],
            requested_date=requested_date,
            time_slot=time_slot,
            status=CustomCakeStatus.PENDING_REVIEW,
        )
        self.db.add(cake)
        await self.db.flush()
        await self.db.refresh(cake)

        # Auto-predict price
        pricing_service = CakePricingService(self.db)
        price_result = await pricing_service.predict_price(
            diameter_inches=diameter_inches,
            height_inches=height_inches,
            layers=layers,
            shape=shape,
            decoration_complexity=complexity,
            is_rush_order=is_rush_order,
            custom_cake_id=cake.id,
        )
        cake.predicted_price = price_result["predicted_price"]

        # Auto-estimate servings
        serving_service = ServingEstimationService(self.db)
        serving_result = await serving_service.estimate_servings(
            diameter_inches=diameter_inches,
            height_inches=height_inches,
            layers=layers,
            shape=shape,
        )
        cake.predicted_servings = serving_result["predicted_servings"]

        # Customer submission must not trigger paid AI APIs.
        descriptions = self._build_template_descriptions(
            flavor=flavor,
            decoration_description=decoration_description,
            event_type=event_type,
        )
        cake.ai_description_short = descriptions.get("short")
        cake.ai_description_long = descriptions.get("long")
        cake.ai_seo_description = descriptions.get("seo")

        await self.db.flush()

        logger.info(
            "Custom cake submitted: %s (predicted: $%s, %d servings)",
            cake.id, cake.predicted_price, cake.predicted_servings,
        )

        return {
            "custom_cake_id": str(cake.id),
            "status": cake.status.value,
            "predicted_price": cake.predicted_price,
            "predicted_servings": cake.predicted_servings,
            "predicted_size_inches": cake.diameter_inches,
            "price_breakdown": price_result["breakdown"],
            "serving_details": serving_result["details"],
            "ai_descriptions": descriptions,
        }

    async def admin_approve(
        self,
        cake_id: uuid.UUID,
        admin_id: uuid.UUID,
        final_price: Decimal,
        admin_notes: str | None = None,
    ) -> dict:
        """Admin approves a custom cake, sets final price, generates Stripe payment link, and emails customer."""
        cake = await self._get_cake(cake_id)
        if not cake:
            return {"error": "Custom cake not found"}

        if cake.status != CustomCakeStatus.PENDING_REVIEW:
            return {"error": f"Cannot approve cake in '{cake.status.value}' status"}

        cake.status = CustomCakeStatus.APPROVED_AWAITING_PAYMENT
        cake.final_price = final_price
        cake.admin_notes = admin_notes
        cake.approved_at = datetime.now(timezone.utc)
        cake.approved_by = admin_id

        # Record final price for model feedback
        pricing_service = CakePricingService(self.db)
        from app.models.ml import CakePricePrediction
        pred_result = await self.db.execute(
            select(CakePricePrediction).where(
                CakePricePrediction.custom_cake_id == cake_id
            ).order_by(desc(CakePricePrediction.created_at)).limit(1)
        )
        prediction = pred_result.scalar_one_or_none()
        if prediction:
            await pricing_service.record_final_price(prediction.id, final_price)

        await self.db.flush()

        # Generate Stripe payment link
        from app.services.stripe_service import StripeService
        from app.models.user import User

        customer = await self.db.execute(
            select(User).where(User.id == cake.customer_id)
        )
        customer_user = customer.scalar_one_or_none()
        customer_email = customer_user.email if customer_user else None

        description = (
            f'{cake.flavor} cake, {cake.diameter_inches}" {cake.shape}, '
            f'{cake.layers} layer(s), {cake.decoration_complexity.value} decoration'
        )

        payment_result = await StripeService.create_payment_link(
            custom_cake_id=str(cake_id),
            description=description,
            amount=final_price,
            customer_email=customer_email,
        )

        # Send payment link email to customer
        if customer_email:
            from app.workers.email_tasks import send_custom_cake_payment_email
            send_custom_cake_payment_email.delay({
                "customer_email": customer_email,
                "customer_name": customer_user.full_name if customer_user else "Valued Customer",
                "cake_description": description,
                "final_price": str(final_price),
                "payment_url": payment_result["checkout_url"],
                "custom_cake_id": str(cake_id),
            })

        logger.info("Custom cake %s approved at $%s — payment link sent", cake_id, final_price)

        return {
            "custom_cake_id": str(cake_id),
            "status": cake.status.value,
            "final_price": cake.final_price,
            "predicted_price": cake.predicted_price,
            "payment_url": payment_result["checkout_url"],
        }

    async def admin_reject(
        self,
        cake_id: uuid.UUID,
        admin_id: uuid.UUID,
        rejection_reason: str,
    ) -> dict:
        """Admin rejects a custom cake."""
        cake = await self._get_cake(cake_id)
        if not cake:
            return {"error": "Custom cake not found"}

        cake.status = CustomCakeStatus.REJECTED
        cake.rejection_reason = rejection_reason
        cake.approved_by = admin_id

        await self.db.flush()
        logger.info("Custom cake %s rejected: %s", cake_id, rejection_reason)

        return {
            "custom_cake_id": str(cake_id),
            "status": cake.status.value,
            "rejection_reason": rejection_reason,
        }

    async def mark_paid(self, cake_id: uuid.UUID) -> dict:
        """Mark a custom cake as paid (called from Stripe webhook)."""
        cake = await self._get_cake(cake_id)
        if not cake:
            return {"error": "Custom cake not found"}

        cake.status = CustomCakeStatus.PAID
        await self.db.flush()

        return {"custom_cake_id": str(cake_id), "status": cake.status.value}

    async def move_to_production(self, cake_id: uuid.UUID) -> dict:
        """Move a paid cake to production."""
        cake = await self._get_cake(cake_id)
        if not cake:
            return {"error": "Custom cake not found"}

        cake.status = CustomCakeStatus.IN_PRODUCTION
        await self.db.flush()

        return {"custom_cake_id": str(cake_id), "status": cake.status.value}

    async def mark_completed(self, cake_id: uuid.UUID) -> dict:
        """Mark a custom cake as completed."""
        cake = await self._get_cake(cake_id)
        if not cake:
            return {"error": "Custom cake not found"}

        cake.status = CustomCakeStatus.COMPLETED
        await self.db.flush()

        return {"custom_cake_id": str(cake_id), "status": cake.status.value}

    async def list_custom_cakes(
        self,
        status: CustomCakeStatus | None = None,
        customer_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CustomCake]:
        """List custom cakes with optional filters."""
        query = select(CustomCake).order_by(desc(CustomCake.created_at))
        if status:
            query = query.where(CustomCake.status == status)
        if customer_id:
            query = query.where(CustomCake.customer_id == customer_id)
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_custom_cake(self, cake_id: uuid.UUID) -> CustomCake | None:
        """Get a single custom cake by ID."""
        return await self._get_cake(cake_id)

    async def _get_cake(self, cake_id: uuid.UUID) -> CustomCake | None:
        result = await self.db.execute(
            select(CustomCake).where(CustomCake.id == cake_id)
        )
        return result.scalar_one_or_none()
