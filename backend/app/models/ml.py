"""
ML models — Cake Price Prediction, Serving Estimation, and Custom Cakes.
"""

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── Custom Cake Status ───────────────────────────────────────────────────────
class CustomCakeStatus(str, enum.Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED_AWAITING_PAYMENT = "approved_awaiting_payment"
    PAID = "paid"
    IN_PRODUCTION = "in_production"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class DecorationComplexity(str, enum.Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ELABORATE = "elaborate"


# ── Cake Price Prediction ────────────────────────────────────────────────────
class CakePricePrediction(Base):
    """Stores price predictions and actual outcomes for model training."""

    __tablename__ = "cake_price_predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Input features
    diameter_inches: Mapped[float] = mapped_column(Float, nullable=False)
    height_inches: Mapped[float] = mapped_column(Float, nullable=False, default=4.0)
    layers: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    shape: Mapped[str] = mapped_column(String(50), default="round", nullable=False)

    # Cost components
    ingredients_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    labor_hours: Mapped[float] = mapped_column(Float, nullable=False, default=2.0)
    decoration_complexity: Mapped[DecorationComplexity] = mapped_column(
        Enum(DecorationComplexity), default=DecorationComplexity.MODERATE, nullable=False
    )
    is_rush_order: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Ingredients detail
    ingredients_detail: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # Prediction output
    predicted_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    predicted_margin: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Actual outcome (filled after admin approval)
    final_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    price_difference: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Model metadata
    model_version: Mapped[str] = mapped_column(String(50), default="v1.0-heuristic", nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Reference
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    custom_cake_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<CakePricePrediction ${self.predicted_price} (actual: ${self.final_price})>"


# ── Serving Size Estimation ──────────────────────────────────────────────────
class ServingEstimate(Base):
    """Stores serving size predictions."""

    __tablename__ = "serving_estimates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    diameter_inches: Mapped[float] = mapped_column(Float, nullable=False)
    height_inches: Mapped[float] = mapped_column(Float, nullable=False, default=4.0)
    layers: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    shape: Mapped[str] = mapped_column(String(50), default="round", nullable=False)
    serving_style: Mapped[str] = mapped_column(
        String(50), default="party", nullable=False
    )  # "party" (smaller) or "dessert" (larger)

    predicted_servings: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_servings: Mapped[int | None] = mapped_column(Integer, nullable=True)

    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


# ── Custom Cake Submissions ─────────────────────────────────────────────────
class CustomCake(Base):
    """Customer custom cake submissions."""

    __tablename__ = "custom_cakes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
    )

    status: Mapped[CustomCakeStatus] = mapped_column(
        Enum(CustomCakeStatus), default=CustomCakeStatus.PENDING_REVIEW,
        nullable=False, index=True,
    )

    # Cake specifications
    flavor: Mapped[str] = mapped_column(String(100), nullable=False)
    diameter_inches: Mapped[float] = mapped_column(Float, nullable=False)
    height_inches: Mapped[float] = mapped_column(Float, default=4.0, nullable=False)
    layers: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    shape: Mapped[str] = mapped_column(String(50), default="round", nullable=False)
    decoration_complexity: Mapped[DecorationComplexity] = mapped_column(
        Enum(DecorationComplexity), default=DecorationComplexity.MODERATE, nullable=False
    )
    decoration_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cake_message: Mapped[str | None] = mapped_column(String(200), nullable=True)
    event_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # wedding, birthday, etc.
    is_rush_order: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Ingredients
    ingredients: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    allergen_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Reference images
    reference_images: Mapped[list | None] = mapped_column(JSONB, default=list)

    # Pricing
    predicted_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    final_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    predicted_servings: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # AI-generated content
    ai_description_short: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ai_description_long: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_seo_description: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Pickup
    requested_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_slot: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Admin
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Stripe
    checkout_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        nullable=False, index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<CustomCake {self.flavor} {self.diameter_inches}\" ({self.status.value})>"


# ── Image Processing ────────────────────────────────────────────────────────
class ProcessedImage(Base):
    """Tracks image uploads and Gemini AI processing results."""

    __tablename__ = "processed_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    custom_cake_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # File info
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Image data (base64 encoded, stored in DB)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    processed_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Processing info
    processing_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="enhancement"
    )
    processing_status: Mapped[str] = mapped_column(
        String(20), default="uploaded", nullable=False
    )  # uploaded, processing, completed, failed, reprocessing
    processing_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Category and prompt tracking
    category_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    prompt_used: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Admin review
    admin_chosen: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # "original" or "processed"
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Size tracking
    original_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processed_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Errors
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<ProcessedImage {self.processing_type}: {self.processing_status}>"


# ── Model Version Tracking ──────────────────────────────────────────────────
class MLModelVersion(Base):
    """Tracks ML model versions and accuracy."""

    __tablename__ = "ml_model_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Accuracy metrics
    mean_absolute_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    mean_percentage_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    r_squared: Mapped[float | None] = mapped_column(Float, nullable=True)
    training_samples: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_extra: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<MLModelVersion {self.model_name} {self.version}>"
