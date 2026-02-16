"""
ML & Custom Cake API endpoints.
Price prediction, serving estimation, description generation, and custom cake workflow.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.user import User
from app.services.custom_cake_service import CustomCakeService
from app.services.llm_service import DescriptionService
from app.services.ml_service import CakePricingService, ServingEstimationService

router = APIRouter(tags=["ML & Custom Cakes"])

ALLOWED_CUSTOM_CAKE_FLAVOR_NORMALIZED = {
    "spong + vanila",
    "sponge + vanilla",
    "sponge and vanilla",
    "vanilla + sponge",
}
ALLOWED_CUSTOM_CAKE_SIZES_INCHES = {10, 12, 14, 16}


# ── Schemas ──────────────────────────────────────────────────────────────────
class PricePredictionRequest(BaseModel):
    diameter_inches: float = Field(..., gt=4, le=24)
    height_inches: float = Field(4.0, gt=1, le=12)
    layers: int = Field(1, ge=1, le=5)
    shape: str = "round"
    ingredients_cost: Decimal | None = None
    labor_hours: float = Field(2.0, gt=0, le=20)
    decoration_complexity: str = "moderate"
    is_rush_order: bool = False


class ServingEstimateRequest(BaseModel):
    diameter_inches: float = Field(..., gt=4, le=24)
    height_inches: float = Field(4.0, gt=1, le=12)
    layers: int = Field(1, ge=1, le=5)
    shape: str = "round"
    serving_style: str = "party"


class DescriptionRequest(BaseModel):
    flavor: str
    ingredients: list[str] | None = None
    decoration_style: str | None = None
    event_type: str | None = None
    size_info: str | None = None
    tone: str = "luxury"


class CustomCakeSubmitRequest(BaseModel):
    flavor: str = Field(..., max_length=100)
    diameter_inches: float = Field(..., gt=4, le=24)
    height_inches: float = Field(4.0, gt=1, le=12)
    layers: int = Field(1, ge=1, le=5)
    shape: str = "round"
    decoration_complexity: str = "moderate"
    decoration_description: str | None = None
    cake_message: str | None = Field(None, max_length=200)
    event_type: str | None = None
    is_rush_order: bool = False
    ingredients: dict | None = None
    allergen_notes: str | None = None
    reference_images: list[str] | None = None
    requested_date: str | None = None
    time_slot: str | None = None


class AdminApproveRequest(BaseModel):
    final_price: Decimal = Field(..., gt=0)
    admin_notes: str | None = None


class AdminRejectRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=10)


# ── Price Prediction ─────────────────────────────────────────────────────────
@router.post("/ml/predict-price")
async def predict_cake_price(
    data: PricePredictionRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Predict cake price based on dimensions and specs."""
    from app.models.ml import DecorationComplexity
    service = CakePricingService(db)
    return await service.predict_price(
        diameter_inches=data.diameter_inches,
        height_inches=data.height_inches,
        layers=data.layers,
        shape=data.shape,
        ingredients_cost=data.ingredients_cost,
        labor_hours=data.labor_hours,
        decoration_complexity=DecorationComplexity(data.decoration_complexity),
        is_rush_order=data.is_rush_order,
    )


@router.get("/ml/pricing-accuracy")
async def get_pricing_accuracy(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get cake price prediction accuracy metrics."""
    service = CakePricingService(db)
    return await service.get_model_accuracy()


# ── Serving Estimation ───────────────────────────────────────────────────────
@router.post("/ml/estimate-servings")
async def estimate_servings(
    data: ServingEstimateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Estimate how many people a cake serves based on dimensions."""
    service = ServingEstimationService(db)
    return await service.estimate_servings(
        diameter_inches=data.diameter_inches,
        height_inches=data.height_inches,
        layers=data.layers,
        shape=data.shape,
        serving_style=data.serving_style,
    )


# ── Description Generation ──────────────────────────────────────────────────
@router.post("/ml/generate-description")
async def generate_description(
    data: DescriptionRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Generate AI marketing descriptions for a product."""
    service = DescriptionService()
    return await service.generate_descriptions(
        flavor=data.flavor,
        ingredients=data.ingredients,
        decoration_style=data.decoration_style,
        event_type=data.event_type,
        size_info=data.size_info,
        tone=data.tone,
    )


# ── Custom Cake Submissions ─────────────────────────────────────────────────
@router.post("/custom-cakes")
async def submit_custom_cake(
    data: CustomCakeSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a custom cake request. Auto-predicts price and servings."""
    service = CustomCakeService(db)

    normalized_flavor = " ".join(data.flavor.strip().lower().split())
    if normalized_flavor not in ALLOWED_CUSTOM_CAKE_FLAVOR_NORMALIZED:
        raise HTTPException(
            status_code=400,
            detail="Only Spong + Vanila flavor is available for custom orders.",
        )

    size_inches = int(data.diameter_inches)
    if data.diameter_inches not in ALLOWED_CUSTOM_CAKE_SIZES_INCHES:
        raise HTTPException(
            status_code=400,
            detail="Available cake sizes are 10, 12, 14, and 16 inches.",
        )

    requested_date = None
    if data.requested_date:
        try:
            requested_date = datetime.fromisoformat(data.requested_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

    return await service.submit_custom_cake(
        customer_id=current_user.id,
        flavor="Spong + Vanila",
        diameter_inches=float(size_inches),
        height_inches=4.0,
        layers=1,
        shape="round",
        decoration_complexity="moderate",
        decoration_description=data.decoration_description,
        cake_message=data.cake_message,
        event_type=data.event_type,
        is_rush_order=data.is_rush_order,
        ingredients=data.ingredients,
        allergen_notes=data.allergen_notes,
        reference_images=data.reference_images,
        requested_date=requested_date,
        time_slot=data.time_slot,
    )


@router.get("/custom-cakes/my-cakes")
async def get_my_custom_cakes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get your custom cake submissions."""
    service = CustomCakeService(db)
    cakes = await service.list_custom_cakes(customer_id=current_user.id)
    return [
        {
            "id": str(c.id),
            "flavor": c.flavor,
            "status": c.status.value,
            "predicted_price": str(c.predicted_price) if c.predicted_price else None,
            "final_price": str(c.final_price) if c.final_price else None,
            "predicted_servings": c.predicted_servings,
            "requested_date": c.requested_date.isoformat() if c.requested_date else None,
            "created_at": c.created_at.isoformat(),
        }
        for c in cakes
    ]


# ── Admin Custom Cake Management ─────────────────────────────────────────────
@router.get("/admin/custom-cakes")
async def list_all_custom_cakes(
    status: str | None = Query(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] List all custom cake submissions."""
    from app.models.ml import CustomCakeStatus

    status_filter = None
    if status:
        try:
            status_filter = CustomCakeStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    service = CustomCakeService(db)
    cakes = await service.list_custom_cakes(status=status_filter)
    return [
        {
            "id": str(c.id),
            "customer_id": str(c.customer_id),
            "flavor": c.flavor,
            "diameter": c.diameter_inches,
            "layers": c.layers,
            "shape": c.shape,
            "decoration": c.decoration_complexity.value,
            "status": c.status.value,
            "predicted_price": str(c.predicted_price) if c.predicted_price else None,
            "final_price": str(c.final_price) if c.final_price else None,
            "predicted_servings": c.predicted_servings,
            "is_rush": c.is_rush_order,
            "requested_date": c.requested_date.isoformat() if c.requested_date else None,
            "cake_message": c.cake_message,
            "event_type": c.event_type,
            "ai_description_short": c.ai_description_short,
            "created_at": c.created_at.isoformat(),
        }
        for c in cakes
    ]


@router.get("/admin/custom-cakes/{cake_id}")
async def get_custom_cake_detail(
    cake_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get full custom cake details."""
    service = CustomCakeService(db)
    cake = await service.get_custom_cake(cake_id)
    if not cake:
        raise HTTPException(status_code=404, detail="Custom cake not found")

    return {
        "id": str(cake.id),
        "customer_id": str(cake.customer_id),
        "flavor": cake.flavor,
        "diameter": cake.diameter_inches,
        "height": cake.height_inches,
        "layers": cake.layers,
        "shape": cake.shape,
        "decoration_complexity": cake.decoration_complexity.value,
        "decoration_description": cake.decoration_description,
        "cake_message": cake.cake_message,
        "event_type": cake.event_type,
        "is_rush": cake.is_rush_order,
        "ingredients": cake.ingredients,
        "allergen_notes": cake.allergen_notes,
        "reference_images": cake.reference_images,
        "status": cake.status.value,
        "predicted_price": str(cake.predicted_price) if cake.predicted_price else None,
        "final_price": str(cake.final_price) if cake.final_price else None,
        "predicted_servings": cake.predicted_servings,
        "ai_description_short": cake.ai_description_short,
        "ai_description_long": cake.ai_description_long,
        "ai_seo_description": cake.ai_seo_description,
        "admin_notes": cake.admin_notes,
        "rejection_reason": cake.rejection_reason,
        "approved_at": cake.approved_at.isoformat() if cake.approved_at else None,
        "requested_date": cake.requested_date.isoformat() if cake.requested_date else None,
        "time_slot": cake.time_slot,
        "created_at": cake.created_at.isoformat(),
        "updated_at": cake.updated_at.isoformat(),
    }


@router.post("/admin/custom-cakes/{cake_id}/approve")
async def approve_custom_cake(
    cake_id: uuid.UUID,
    data: AdminApproveRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Approve a custom cake and set the final price."""
    service = CustomCakeService(db)
    result = await service.admin_approve(
        cake_id=cake_id,
        admin_id=admin.id,
        final_price=data.final_price,
        admin_notes=data.admin_notes,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/admin/custom-cakes/{cake_id}/reject")
async def reject_custom_cake(
    cake_id: uuid.UUID,
    data: AdminRejectRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Reject a custom cake with reason."""
    service = CustomCakeService(db)
    result = await service.admin_reject(
        cake_id=cake_id,
        admin_id=admin.id,
        rejection_reason=data.rejection_reason,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/admin/custom-cakes/{cake_id}/status")
async def update_custom_cake_status(
    cake_id: uuid.UUID,
    action: str = Query(..., description="Action: 'production' or 'completed'"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Move custom cake to production or mark completed."""
    service = CustomCakeService(db)
    if action == "production":
        result = await service.move_to_production(cake_id)
    elif action == "completed":
        result = await service.mark_completed(cake_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'production' or 'completed'")

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
