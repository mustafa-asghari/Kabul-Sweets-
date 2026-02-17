"""
ML Service — Cake Price Prediction + Serving Size Estimation.
Phase ML-1 and ML-2.

Uses XGBoost when enough feedback data exists, with heuristic fallback.
"""

import math
import os
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.ml import (
    CakePricePrediction,
    DecorationComplexity,
    ServingEstimate,
)

logger = get_logger("ml_service")

# Optional heavy ML dependencies.
try:
    import numpy as np
    import xgboost as xgb
except Exception:  # pragma: no cover - fallback path when ML libs are unavailable
    np = None
    xgb = None


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid int for %s=%r. Falling back to %d.", name, raw, default)
        return default


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

SHAPE_INDEX = {
    "round": 0.0,
    "square": 1.0,
    "rectangle": 2.0,
    "heart": 3.0,
    "hexagon": 4.0,
    "tiered": 5.0,
}

COMPLEXITY_INDEX = {
    DecorationComplexity.SIMPLE: 0.0,
    DecorationComplexity.MODERATE: 1.0,
    DecorationComplexity.COMPLEX: 2.0,
    DecorationComplexity.ELABORATE: 3.0,
}

MODEL_VERSION_HEURISTIC = "v1.0-heuristic"
MODEL_VERSION_XGBOOST = "v2.0-xgboost"
DEFAULT_XGBOOST_MODEL_PATH = "/tmp/kabul_sweets_models/cake_price_xgboost.json"
ENABLE_XGBOOST = os.getenv("ML_USE_XGBOOST", "true").strip().lower() == "true"
XGBOOST_MODEL_PATH = os.getenv("XGBOOST_MODEL_PATH", DEFAULT_XGBOOST_MODEL_PATH)
XGBOOST_MIN_TRAINING_SAMPLES = _env_int("XGBOOST_MIN_TRAINING_SAMPLES", 30)
MIN_PRICE = Decimal("35.00")
TARGET_MARGIN = Decimal("0.50")


class CakePricingService:
    """Predicts cake prices using XGBoost with heuristic fallback."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._xgb_model: Any | None = None
        self._xgb_samples: int = 0
        self._xgb_attempted: bool = False

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
        shape = (shape or "round").strip().lower()

        # Step 1: Calculate volume
        volume = self._calculate_volume(diameter_inches, height_inches, layers, shape)

        # Step 2: Estimate ingredients cost if not provided
        if ingredients_cost is None:
            ingredients_cost = (
                Decimal(str(volume)) * BASE_COST_PER_CUBIC_INCH
            ).quantize(Decimal("0.01"))

        # Step 3: Calculate labor cost
        labor_cost = (Decimal(str(labor_hours)) * LABOR_RATE_PER_HOUR).quantize(Decimal("0.01"))

        # Step 4: Apply decoration multiplier
        deco_mult = DECORATION_MULTIPLIER.get(decoration_complexity, Decimal("1.3"))

        # Step 5: Base cost
        base_cost = (ingredients_cost + labor_cost) * deco_mult

        # Step 6: Rush order surcharge
        if is_rush_order:
            base_cost = (base_cost * RUSH_ORDER_SURCHARGE).quantize(Decimal("0.01"))

        # Step 7: Heuristic baseline
        heuristic_price = self._predict_heuristic_price(base_cost)

        # Step 8: Compare with historical similar cakes
        historical_avg = await self._get_historical_average(
            diameter_inches, layers, decoration_complexity
        )

        # Step 9: Try XGBoost prediction.
        xgb_price, xgb_confidence, xgb_samples = await self._predict_xgboost_price(
            diameter_inches=diameter_inches,
            height_inches=height_inches,
            layers=layers,
            shape=shape,
            ingredients_cost=ingredients_cost,
            labor_hours=labor_hours,
            decoration_complexity=decoration_complexity,
            is_rush_order=is_rush_order,
            volume=volume,
            base_cost=base_cost,
        )

        if xgb_price is not None:
            # Keep some heuristic influence to stay business-safe.
            price = self._normalize_price(
                (xgb_price * Decimal("0.8")) + (heuristic_price * Decimal("0.2"))
            )
            model_version = MODEL_VERSION_XGBOOST
            confidence_score = xgb_confidence
        else:
            price = heuristic_price
            model_version = MODEL_VERSION_HEURISTIC
            confidence_score = 0.7

        # Blend with historical if available.
        if historical_avg and historical_avg > 0:
            blended = (price * Decimal("0.85")) + (historical_avg * Decimal("0.15"))
            price = self._normalize_price(blended)
            confidence_score = min(0.97, confidence_score + 0.03)
        elif model_version == MODEL_VERSION_HEURISTIC:
            confidence_score = 0.75

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
            model_version=model_version,
            confidence_score=confidence_score,
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
                "target_margin_pct": float(TARGET_MARGIN * 100),
                "actual_margin_pct": round(actual_margin, 1),
                "xgboost_active": model_version == MODEL_VERSION_XGBOOST,
                "xgboost_training_samples": (
                    xgb_samples if model_version == MODEL_VERSION_XGBOOST else 0
                ),
            },
            "historical_average": historical_avg,
            "confidence_score": prediction.confidence_score,
            "model_version": model_version,
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
        latest_model_result = await self.db.execute(
            select(CakePricePrediction.model_version)
            .order_by(CakePricePrediction.created_at.desc())
            .limit(1)
        )
        latest_model = latest_model_result.scalar_one_or_none() or MODEL_VERSION_HEURISTIC

        training_samples = await self._count_training_samples()
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
            "model_version": latest_model,
            "xgboost_enabled": ENABLE_XGBOOST and xgb is not None and np is not None,
            "xgboost_training_samples": training_samples,
            "xgboost_min_training_samples": XGBOOST_MIN_TRAINING_SAMPLES,
        }

    def _predict_heuristic_price(self, base_cost: Decimal) -> Decimal:
        raw_price = (base_cost / (1 - TARGET_MARGIN)).quantize(Decimal("0.01"))
        return self._normalize_price(raw_price)

    def _normalize_price(self, raw_price: Decimal) -> Decimal:
        rounded = Decimal(str(math.ceil(float(raw_price) / 5) * 5)).quantize(Decimal("0.01"))
        return max(rounded, MIN_PRICE)

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

    async def _count_training_samples(self) -> int:
        result = await self.db.execute(
            select(func.count(CakePricePrediction.id)).where(CakePricePrediction.final_price.isnot(None))
        )
        count = result.scalar_one_or_none()
        return int(count or 0)

    async def _predict_xgboost_price(
        self,
        diameter_inches: float,
        height_inches: float,
        layers: int,
        shape: str,
        ingredients_cost: Decimal,
        labor_hours: float,
        decoration_complexity: DecorationComplexity,
        is_rush_order: bool,
        volume: float,
        base_cost: Decimal,
    ) -> tuple[Decimal | None, float, int]:
        if not ENABLE_XGBOOST:
            return None, 0.0, 0

        model, samples = await self._get_or_train_xgboost_model()
        if model is None or np is None:
            return None, 0.0, samples

        features = np.asarray(
            [
                self._build_feature_vector(
                    diameter_inches=diameter_inches,
                    height_inches=height_inches,
                    layers=layers,
                    shape=shape,
                    ingredients_cost=ingredients_cost,
                    labor_hours=labor_hours,
                    decoration_complexity=decoration_complexity,
                    is_rush_order=is_rush_order,
                    volume=volume,
                    base_cost=base_cost,
                )
            ],
            dtype=float,
        )
        try:
            predicted_raw = float(model.predict(features)[0])
        except Exception as exc:
            logger.warning("XGBoost prediction failed: %s", str(exc))
            return None, 0.0, samples

        if predicted_raw <= 0:
            return None, 0.0, samples

        predicted = self._normalize_price(Decimal(str(predicted_raw)))
        confidence = 0.78
        if samples >= XGBOOST_MIN_TRAINING_SAMPLES:
            confidence += min(0.16, (samples - XGBOOST_MIN_TRAINING_SAMPLES) / 500)
        return predicted, min(confidence, 0.96), samples

    async def _get_or_train_xgboost_model(self) -> tuple[Any | None, int]:
        if self._xgb_attempted:
            return self._xgb_model, self._xgb_samples

        self._xgb_attempted = True

        if xgb is None or np is None:
            logger.warning("XGBoost dependencies are unavailable, using heuristic pricing.")
            return None, 0

        loaded_model = self._load_xgboost_model()
        if loaded_model is not None:
            self._xgb_model = loaded_model
            self._xgb_samples = await self._count_training_samples()
            return self._xgb_model, self._xgb_samples

        trained_model, sample_count = await self._train_xgboost_model()
        self._xgb_model = trained_model
        self._xgb_samples = sample_count
        return self._xgb_model, self._xgb_samples

    def _load_xgboost_model(self) -> Any | None:
        model_path = Path(XGBOOST_MODEL_PATH)
        if not model_path.exists():
            return None

        try:
            model = xgb.XGBRegressor(
                objective="reg:squarederror",
                n_estimators=320,
                learning_rate=0.05,
                max_depth=6,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=42,
            )
            model.load_model(str(model_path))
            logger.info("Loaded XGBoost pricing model from %s", model_path)
            return model
        except Exception as exc:
            logger.warning("Failed to load XGBoost model (%s): %s", model_path, str(exc))
            return None

    async def _train_xgboost_model(self) -> tuple[Any | None, int]:
        result = await self.db.execute(
            select(CakePricePrediction).where(CakePricePrediction.final_price.isnot(None))
        )
        rows = result.scalars().all()
        sample_count = len(rows)
        if sample_count < XGBOOST_MIN_TRAINING_SAMPLES:
            logger.info(
                "Skipping XGBoost training: %d/%d samples available.",
                sample_count,
                XGBOOST_MIN_TRAINING_SAMPLES,
            )
            return None, sample_count

        features: list[list[float]] = []
        targets: list[float] = []
        for row in rows:
            if row.final_price is None:
                continue

            volume = self._calculate_volume(
                row.diameter_inches, row.height_inches, row.layers, row.shape
            )
            deco_mult = DECORATION_MULTIPLIER.get(row.decoration_complexity, Decimal("1.3"))
            base_cost = (
                row.ingredients_cost + Decimal(str(row.labor_hours)) * LABOR_RATE_PER_HOUR
            ) * deco_mult
            if row.is_rush_order:
                base_cost = base_cost * RUSH_ORDER_SURCHARGE

            features.append(
                self._build_feature_vector(
                    diameter_inches=row.diameter_inches,
                    height_inches=row.height_inches,
                    layers=row.layers,
                    shape=row.shape,
                    ingredients_cost=row.ingredients_cost,
                    labor_hours=row.labor_hours,
                    decoration_complexity=row.decoration_complexity,
                    is_rush_order=row.is_rush_order,
                    volume=volume,
                    base_cost=base_cost,
                )
            )
            targets.append(float(row.final_price))

        if len(features) < XGBOOST_MIN_TRAINING_SAMPLES:
            return None, len(features)

        try:
            x_arr = np.asarray(features, dtype=float)
            y_arr = np.asarray(targets, dtype=float)

            model = xgb.XGBRegressor(
                objective="reg:squarederror",
                n_estimators=320,
                learning_rate=0.05,
                max_depth=6,
                min_child_weight=2,
                subsample=0.9,
                colsample_bytree=0.9,
                reg_alpha=0.05,
                reg_lambda=1.2,
                random_state=42,
            )
            model.fit(x_arr, y_arr)

            model_path = Path(XGBOOST_MODEL_PATH)
            model_path.parent.mkdir(parents=True, exist_ok=True)
            model.save_model(str(model_path))
            logger.info(
                "Trained XGBoost pricing model with %d samples at %s",
                len(features),
                model_path,
            )

            return model, len(features)
        except Exception as exc:
            logger.warning("XGBoost training failed: %s", str(exc))
            return None, len(features)

    def _build_feature_vector(
        self,
        diameter_inches: float,
        height_inches: float,
        layers: int,
        shape: str,
        ingredients_cost: Decimal,
        labor_hours: float,
        decoration_complexity: DecorationComplexity,
        is_rush_order: bool,
        volume: float,
        base_cost: Decimal,
    ) -> list[float]:
        shape_key = (shape or "round").strip().lower()
        shape_value = SHAPE_INDEX.get(shape_key, 0.0)
        deco_value = COMPLEXITY_INDEX.get(decoration_complexity, 1.0)

        radius = diameter_inches / 2
        cross_section_area = math.pi * (radius ** 2)
        volume_per_layer = volume / max(layers, 1)

        return [
            float(diameter_inches),
            float(height_inches),
            float(layers),
            float(shape_value),
            float(deco_value),
            1.0 if is_rush_order else 0.0,
            float(volume),
            float(ingredients_cost),
            float(labor_hours),
            float(base_cost),
            float(cross_section_area),
            float(volume_per_layer),
        ]


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
