"""
ML Service — Cake Price Prediction + Serving Size Estimation.
Phase ML-1 and ML-2.

Starts with heuristic rules, upgradable to XGBoost when training data accumulates.
"""

import math
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.ml import (
    CakePricePrediction,
    DecorationComplexity,
    ServingEstimate,
)

logger = get_logger("ml_service")

# ── Constants ────────────────────────────────────────────────────────────────
LABOR_RATE_PER_HOUR = Decimal("35.00")  # AUD

DECORATION_MULTIPLIER = {
    DecorationComplexity.SIMPLE: Decimal("1.0"),
    DecorationComplexity.MODERATE: Decimal("1.3"),
    DecorationComplexity.COMPLEX: Decimal("1.7"),
    DecorationComplexity.ELABORATE: Decimal("2.2"),
}

RUSH_ORDER_SURCHARGE = Decimal("1.25")  # 25% extra

# Base ingredient costs per cubic inch (approximate)
BASE_COST_PER_CUBIC_INCH = Decimal("0.12")

# Shape volume multipliers (relative to round)
SHAPE_VOLUME = {
    "round": 1.0,
    "square": 1.27,    # square has more volume than round of same "diameter"
    "rectangle": 1.35,
    "heart": 0.85,
    "hexagon": 1.1,
    "tiered": 1.5,
}


class CakePricingService:
    """Predicts cake prices using heuristic rules (upgradable to ML)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def predict_price(
        self,
        diameter_inches: float,
        height_inches: float = 4.0,
        layers: int = 1,
        shape: str = "round",
        ingredients_cost: Decimal | None = None,
        labor_hours: float = 2.0,
        decoration_complexity: DecorationComplexity = DecorationComplexity.MODERATE,
        is_rush_order: bool = False,
        ingredients_detail: dict | None = None,
        product_id: uuid.UUID | None = None,
        custom_cake_id: uuid.UUID | None = None,
    ) -> dict:
        """
        Predict cake price.
        Returns predicted price, margin suggestion, and breakdown.
        """
        # Step 1: Calculate volume
        volume = self._calculate_volume(diameter_inches, height_inches, layers, shape)

        # Step 2: Estimate ingredients cost if not provided
        if ingredients_cost is None:
            ingredients_cost = (Decimal(str(volume)) * BASE_COST_PER_CUBIC_INCH).quantize(Decimal("0.01"))

        # Step 3: Calculate labor cost
        labor_cost = (Decimal(str(labor_hours)) * LABOR_RATE_PER_HOUR).quantize(Decimal("0.01"))

        # Step 4: Apply decoration multiplier
        deco_mult = DECORATION_MULTIPLIER.get(decoration_complexity, Decimal("1.3"))

        # Step 5: Base cost
        base_cost = (ingredients_cost + labor_cost) * deco_mult

        # Step 6: Rush order surcharge
        if is_rush_order:
            base_cost = (base_cost * RUSH_ORDER_SURCHARGE).quantize(Decimal("0.01"))

        # Step 7: Target margin (40-60% markup)
        margin = Decimal("0.50")  # 50% target margin
        price = (base_cost / (1 - margin)).quantize(Decimal("0.01"))

        # Step 8: Round to nearest $5
        price = (Decimal(str(math.ceil(float(price) / 5) * 5))).quantize(Decimal("0.01"))

        # Step 9: Ensure minimum price
        min_price = Decimal("35.00")
        price = max(price, min_price)

        # Step 10: Compare with historical similar cakes
        historical_avg = await self._get_historical_average(
            diameter_inches, layers, decoration_complexity
        )

        # Blend with historical if available (70% model, 30% historical)
        if historical_avg and historical_avg > 0:
            blended = (price * Decimal("0.7")) + (historical_avg * Decimal("0.3"))
            price = (Decimal(str(math.ceil(float(blended) / 5) * 5))).quantize(Decimal("0.01"))

        # Calculate actual margin
        actual_margin = float((price - base_cost) / price * 100) if price > 0 else 0

        # Store prediction
        prediction = CakePricePrediction(
            diameter_inches=diameter_inches,
            height_inches=height_inches,
            layers=layers,
            shape=shape,
            ingredients_cost=ingredients_cost,
            labor_hours=labor_hours,
            decoration_complexity=decoration_complexity,
            is_rush_order=is_rush_order,
            ingredients_detail=ingredients_detail or {},
            predicted_price=price,
            predicted_margin=actual_margin,
            model_version="v1.0-heuristic",
            confidence_score=0.7 if not historical_avg else 0.85,
            product_id=product_id,
            custom_cake_id=custom_cake_id,
        )
        self.db.add(prediction)
        await self.db.flush()

        return {
            "predicted_price": price,
            "breakdown": {
                "volume_cubic_inches": round(volume, 1),
                "ingredients_cost": ingredients_cost,
                "labor_cost": labor_cost,
                "decoration_multiplier": float(deco_mult),
                "base_cost": base_cost,
                "rush_surcharge_applied": is_rush_order,
                "target_margin_pct": float(margin * 100),
                "actual_margin_pct": round(actual_margin, 1),
            },
            "historical_average": historical_avg,
            "confidence_score": prediction.confidence_score,
            "model_version": "v1.0-heuristic",
            "prediction_id": str(prediction.id),
        }

    async def record_final_price(
        self,
        prediction_id: uuid.UUID,
        final_price: Decimal,
    ) -> dict:
        """Record the admin's final approved price for model feedback."""
        result = await self.db.execute(
            select(CakePricePrediction).where(CakePricePrediction.id == prediction_id)
        )
        prediction = result.scalar_one_or_none()
        if not prediction:
            return {"error": "Prediction not found"}

        prediction.final_price = final_price
        prediction.price_difference = final_price - prediction.predicted_price
        await self.db.flush()

        return {
            "predicted": prediction.predicted_price,
            "final": final_price,
            "difference": prediction.price_difference,
            "accuracy_pct": round(
                float(1 - abs(prediction.price_difference) / prediction.predicted_price) * 100, 1
            ) if prediction.predicted_price > 0 else 0,
        }

    async def get_model_accuracy(self) -> dict:
        """Get prediction accuracy metrics."""
        result = await self.db.execute(
            select(
                func.count(CakePricePrediction.id).label("total"),
                func.avg(
                    func.abs(CakePricePrediction.price_difference)
                ).label("mae"),
                func.avg(CakePricePrediction.predicted_price).label("avg_predicted"),
                func.avg(CakePricePrediction.final_price).label("avg_actual"),
            ).where(CakePricePrediction.final_price.isnot(None))
        )
        row = result.one()

        return {
            "total_predictions": row.total,
            "mean_absolute_error": float(row.mae) if row.mae else None,
            "avg_predicted_price": float(row.avg_predicted) if row.avg_predicted else None,
            "avg_actual_price": float(row.avg_actual) if row.avg_actual else None,
            "model_version": "v1.0-heuristic",
        }

    def _calculate_volume(
        self,
        diameter: float,
        height: float,
        layers: int,
        shape: str,
    ) -> float:
        """Calculate cake volume in cubic inches."""
        radius = diameter / 2
        # Base cylindrical volume
        volume = math.pi * (radius ** 2) * height * layers
        # Apply shape multiplier
        shape_mult = SHAPE_VOLUME.get(shape, 1.0)
        return volume * shape_mult

    async def _get_historical_average(
        self,
        diameter: float,
        layers: int,
        complexity: DecorationComplexity,
    ) -> Decimal | None:
        """Get average price from historical predictions with similar specs."""
        result = await self.db.execute(
            select(func.avg(CakePricePrediction.final_price)).where(
                CakePricePrediction.final_price.isnot(None),
                CakePricePrediction.diameter_inches.between(diameter - 1, diameter + 1),
                CakePricePrediction.layers == layers,
                CakePricePrediction.decoration_complexity == complexity,
            )
        )
        avg = result.scalar()
        return Decimal(str(avg)).quantize(Decimal("0.01")) if avg else None


class ServingEstimationService:
    """Predicts how many people a cake feeds."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Serving sizes in square inches
    PARTY_SERVING_SQ_IN = 2.0    # Small party slice
    DESSERT_SERVING_SQ_IN = 3.5  # Generous dessert slice

    async def estimate_servings(
        self,
        diameter_inches: float,
        height_inches: float = 4.0,
        layers: int = 1,
        shape: str = "round",
        serving_style: str = "party",
        product_id: uuid.UUID | None = None,
    ) -> dict:
        """Estimate serving count based on cake dimensions."""
        # Calculate cross-sectional area
        if shape == "round":
            area = math.pi * (diameter_inches / 2) ** 2
        elif shape == "square":
            area = diameter_inches ** 2
        elif shape == "rectangle":
            area = diameter_inches * (diameter_inches * 0.75)  # Assume 4:3 ratio
        elif shape == "heart":
            area = math.pi * (diameter_inches / 2) ** 2 * 0.8
        else:
            area = math.pi * (diameter_inches / 2) ** 2

        # Height factor (standard is 4 inches)
        height_factor = height_inches / 4.0

        # Layer factor (each layer adds ~80% more volume due to filling)
        layer_factor = 1 + (layers - 1) * 0.8

        # Total volume factor
        volume = area * height_factor * layer_factor

        # Calculate servings
        if serving_style == "party":
            servings = int(volume / self.PARTY_SERVING_SQ_IN)
        else:
            servings = int(volume / self.DESSERT_SERVING_SQ_IN)

        # Ensure minimum of 4 servings
        servings = max(servings, 4)

        # Store estimate
        estimate = ServingEstimate(
            diameter_inches=diameter_inches,
            height_inches=height_inches,
            layers=layers,
            shape=shape,
            serving_style=serving_style,
            predicted_servings=servings,
            product_id=product_id,
        )
        self.db.add(estimate)
        await self.db.flush()

        return {
            "predicted_servings": servings,
            "serving_style": serving_style,
            "details": {
                "cross_section_area": round(area, 1),
                "height_factor": round(height_factor, 2),
                "layer_factor": round(layer_factor, 2),
                "effective_volume": round(volume, 1),
            },
            "suggestion": self._suggest_size(servings, serving_style),
        }

    def _suggest_size(self, servings: int, style: str) -> str:
        """Generate a human-readable suggestion."""
        if style == "party":
            if servings <= 10:
                return "Perfect for a small gathering"
            elif servings <= 20:
                return "Great for a medium party"
            elif servings <= 40:
                return "Ideal for a large celebration"
            else:
                return "Perfect for a big event or wedding"
        else:
            if servings <= 6:
                return "Intimate dessert for a small group"
            elif servings <= 12:
                return "Generous portions for a dinner party"
            elif servings <= 25:
                return "Plenty for everyone at a celebration"
            else:
                return "Abundant dessert for a large event"
