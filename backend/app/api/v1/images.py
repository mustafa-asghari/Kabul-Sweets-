"""
Image Processing API endpoints.
Upload, process with Gemini AI, reject/re-process, and manage product images.
"""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.product import ProductCategory
from app.models.ml import ProcessedImage
from app.schemas.product import ProductCreate, VariantCreate
from app.models.user import User
from app.services.image_processing_service import ImageCategory, ImageProcessingService
from app.services.product_service import ProductService

router = APIRouter(prefix="/images", tags=["Image Processing"])
logger = get_logger("image_routes")

# Max 10MB per image
MAX_IMAGE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


# ── Schemas ──────────────────────────────────────────────────────────────────
class ProcessImageRequest(BaseModel):
    image_id: uuid.UUID
    category: str = Field(..., description="Category: cake, sweet, pastry, cookie, bread, drink")
    custom_prompt: str | None = Field(None, description="Optional custom prompt to add on top of category prompt")


class RejectImageRequest(BaseModel):
    image_id: uuid.UUID
    custom_prompt: str = Field(..., min_length=5, description="Custom instructions for re-processing")
    category: str | None = None


class ChooseImageRequest(BaseModel):
    image_id: uuid.UUID
    choice: str = Field(..., description="'original' or 'processed'")


class PublishProductFromImageRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    short_description: str | None = Field(None, max_length=500)
    description: str | None = None
    category: str = "cake"
    base_price: Decimal = Field(..., gt=0)
    is_cake: bool = True
    is_featured: bool = False
    max_per_order: int | None = Field(None, ge=1)
    sort_order: int = 0
    tags: list[str] | None = None
    create_default_variant: bool = True
    variant_name: str = Field("Default", min_length=1, max_length=100)
    stock_quantity: int = Field(0, ge=0)
    low_stock_threshold: int = Field(5, ge=0)


def _decode_data_url_to_response(data_url: str):
    from fastapi.responses import Response
    import base64

    if data_url.startswith("data:"):
        b64_data = data_url.split(",", 1)[1]
        mime = data_url.split(";")[0].split(":")[1]
        return Response(
            content=base64.b64decode(b64_data),
            media_type=mime,
            headers={"Cache-Control": "public, max-age=86400"},
        )
    return {"url": data_url}


# ── Upload Endpoints ─────────────────────────────────────────────────────────
@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    product_id: uuid.UUID | None = Form(None),
    custom_cake_id: uuid.UUID | None = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    [Admin] Upload a product image.
    Images are saved to the database. Use /process to enhance with AI.
    Multiple images can be uploaded — each gets its own ID.
    """
    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed: {', '.join(ALLOWED_TYPES)}",
        )

    # Read file data
    image_data = await file.read()

    # Validate size
    if len(image_data) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large: {len(image_data)} bytes. Maximum: {MAX_IMAGE_SIZE} bytes (10MB)",
        )

    service = ImageProcessingService(db)
    result = await service.upload_and_save_image(
        image_data=image_data,
        filename=file.filename or "unknown",
        content_type=file.content_type or "image/jpeg",
        product_id=product_id,
        custom_cake_id=custom_cake_id,
        uploaded_by=admin.id,
    )

    return result


@router.post("/upload-multiple")
async def upload_multiple_images(
    files: list[UploadFile] = File(...),
    product_id: uuid.UUID | None = Form(None),
    custom_cake_id: uuid.UUID | None = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    [Admin] Upload multiple product images at once.
    Each image gets its own ID and is processed independently.
    """
    results = []
    errors = []

    for file in files:
        if file.content_type not in ALLOWED_TYPES:
            errors.append({"filename": file.filename, "error": f"Invalid type: {file.content_type}"})
            continue

        image_data = await file.read()
        if len(image_data) > MAX_IMAGE_SIZE:
            errors.append({"filename": file.filename, "error": "File too large (max 10MB)"})
            continue

        service = ImageProcessingService(db)
        result = await service.upload_and_save_image(
            image_data=image_data,
            filename=file.filename or "unknown",
            content_type=file.content_type or "image/jpeg",
            product_id=product_id,
            custom_cake_id=custom_cake_id,
            uploaded_by=admin.id,
        )
        results.append(result)

    return {
        "uploaded": len(results),
        "errors": len(errors),
        "images": results,
        "failed": errors,
    }


# ── Process Endpoints ────────────────────────────────────────────────────────
@router.post("/process")
async def process_image(
    data: ProcessImageRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    [Admin] Process an uploaded image with Gemini AI.

    Each image is sent to Gemini in a SEPARATE API call (isolated context).
    The category determines the base prompt:
    - **cake**: Professional white background, frosting detail enhancement
    - **sweet**: Elegant arrangement, sugar/nut texture emphasis
    - **pastry**: Flaky layers, golden crispy texture emphasis
    - **cookie**: Intricate patterns, golden baked surfaces
    - **bread**: Crust texture, artisan quality emphasis
    - **drink**: Packaging clarity, label enhancement

    Optionally add a custom prompt ON TOP of the category prompt.
    """
    try:
        category = ImageCategory(data.category.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{data.category}'. Must be: {', '.join(c.value for c in ImageCategory)}",
        )

    service = ImageProcessingService(db)
    result = await service.process_image(
        image_id=data.image_id,
        category=category,
        custom_prompt=data.custom_prompt,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/process-batch")
async def process_batch(
    image_ids: list[uuid.UUID],
    category: str = Query(...),
    custom_prompt: str | None = Query(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    [Admin] Process multiple images with the same category.
    Each image is processed in its own SEPARATE Gemini API call.
    """
    try:
        cat = ImageCategory(category.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    service = ImageProcessingService(db)
    results = []

    for image_id in image_ids:
        result = await service.process_image(
            image_id=image_id,
            category=cat,
            custom_prompt=custom_prompt,
        )
        results.append(result)

    succeeded = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]

    return {
        "total": len(results),
        "succeeded": len(succeeded),
        "failed": len(failed),
        "results": results,
    }


# ── Reject & Re-process ─────────────────────────────────────────────────────
@router.post("/reject")
async def reject_and_reprocess(
    data: RejectImageRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    [Admin] Reject a processed image and re-process with custom instructions.

    The custom prompt is ADDED ON TOP of the base category prompt.
    A completely new Gemini API call is made (fresh context).

    Example custom_prompt:
    "Make the shadow softer. The frosting colour should be more vibrant pink."
    """
    cat = None
    if data.category:
        try:
            cat = ImageCategory(data.category.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {data.category}")

    service = ImageProcessingService(db)
    result = await service.reject_and_reprocess(
        image_id=data.image_id,
        custom_prompt=data.custom_prompt,
        category=cat,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


# ── Admin Choose ─────────────────────────────────────────────────────────────
@router.post("/choose")
async def choose_image_version(
    data: ChooseImageRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    [Admin] Choose which version of an image to use.

    Options:
    - **original**: Keep the original uploaded image
    - **processed**: Use the Gemini-enhanced version
    """
    service = ImageProcessingService(db)
    result = await service.admin_choose_image(data.image_id, data.choice)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.delete("/{image_id}")
async def delete_image(
    image_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Delete an uploaded image (original + processed versions)."""
    service = ImageProcessingService(db)
    deleted = await service.delete_image(image_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Image not found")
    return {"message": "Image deleted", "image_id": str(image_id)}


@router.get("/{image_id}/selected/public")
async def get_public_selected_image(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Public image endpoint for storefront use.
    Only works for images explicitly approved by admin (chosen source set).
    """
    result = await db.execute(
        select(ProcessedImage).where(ProcessedImage.id == image_id)
    )
    image = result.scalar_one_or_none()
    if not image or image.admin_chosen not in ("original", "processed"):
        raise HTTPException(status_code=404, detail="Approved image not found")

    selected_url, _ = ImageProcessingService.resolve_selected_image_url(image)
    if not selected_url:
        raise HTTPException(status_code=404, detail="Approved image source missing")

    return _decode_data_url_to_response(selected_url)


@router.post("/{image_id}/publish-product")
async def publish_image_as_product(
    image_id: uuid.UUID,
    data: PublishProductFromImageRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    [Admin] Publish an approved image as a new product.
    Uses the admin-chosen source (processed/original) as thumbnail + image.
    """
    result = await db.execute(
        select(ProcessedImage).where(ProcessedImage.id == image_id)
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    if image.admin_chosen not in ("original", "processed"):
        raise HTTPException(
            status_code=400,
            detail="Approve an image version first (Original or Processed).",
        )

    selected_url, selected_source = ImageProcessingService.resolve_selected_image_url(image)
    if not selected_url:
        raise HTTPException(status_code=400, detail="Selected image data is missing.")

    try:
        ProductCategory(data.category)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{data.category}'.",
        )

    public_image_url = f"/api/v1/images/{image_id}/selected/public"
    variants: list[VariantCreate] = []
    if data.create_default_variant:
        variants.append(
            VariantCreate(
                name=data.variant_name,
                price=data.base_price,
                stock_quantity=data.stock_quantity,
                low_stock_threshold=data.low_stock_threshold,
            )
        )

    product_service = ProductService(db)
    product = await product_service.create_product(
        ProductCreate(
            name=data.name,
            description=data.description,
            short_description=data.short_description,
            category=data.category,
            base_price=data.base_price,
            images=[public_image_url],
            thumbnail=public_image_url,
            tags=data.tags or [],
            is_active=True,
            is_featured=data.is_featured,
            is_cake=data.is_cake,
            max_per_order=data.max_per_order,
            sort_order=data.sort_order,
            variants=variants,
        )
    )

    image.product_id = product.id
    await db.flush()

    return {
        "message": "Product published from approved image",
        "product_id": str(product.id),
        "product_slug": product.slug,
        "image_id": str(image_id),
        "selected_source": selected_source,
        "public_image_url": public_image_url,
    }


# ── View/List ────────────────────────────────────────────────────────────────
@router.get("/{image_id}")
async def get_image_details(
    image_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get image details (without raw image data)."""
    service = ImageProcessingService(db)
    result = await service.get_image(image_id)
    if not result:
        raise HTTPException(status_code=404, detail="Image not found")
    return result


@router.get("/{image_id}/original")
async def get_original_image(
    image_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get the original image data (base64)."""
    result = await db.execute(
        select(ProcessedImage).where(ProcessedImage.id == image_id)
    )
    image = result.scalar_one_or_none()
    if not image or not image.original_url:
        raise HTTPException(status_code=404, detail="Image not found")

    return _decode_data_url_to_response(image.original_url)


@router.get("/{image_id}/processed")
async def get_processed_image(
    image_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get the Gemini-processed image data (base64)."""
    result = await db.execute(
        select(ProcessedImage).where(ProcessedImage.id == image_id)
    )
    image = result.scalar_one_or_none()
    if not image or not image.processed_url:
        raise HTTPException(status_code=404, detail="Processed image not found")

    return _decode_data_url_to_response(image.processed_url)


@router.get("/")
async def list_images(
    product_id: uuid.UUID | None = Query(None),
    custom_cake_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] List all uploaded images with optional filters."""
    service = ImageProcessingService(db)
    return await service.list_images(
        product_id=product_id,
        custom_cake_id=custom_cake_id,
        status=status,
    )


# ── Category Prompts Info ────────────────────────────────────────────────────
@router.get("/categories/prompts")
async def get_category_prompts(
    admin: User = Depends(require_admin),
):
    """[Admin] View the AI prompts used for each product category."""
    from app.services.image_processing_service import CATEGORY_PROMPTS
    return {
        cat.value: prompt
        for cat, prompt in CATEGORY_PROMPTS.items()
    }
