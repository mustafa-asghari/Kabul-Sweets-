"""
Image Processing API endpoints.
Upload, process with Gemini AI, reject/re-process, and manage product images.

Security layer
──────────────
• Magic-byte validation: raw file bytes are inspected — Content-Type spoofing is rejected.
• Per-user rate limiting: upload / process / reject are throttled by authenticated user ID.
• All image data lives in S3; the API never returns raw blobs (only pre-signed redirects).
"""

import uuid
from decimal import Decimal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import async_session_factory, get_db
from app.core.logging import get_logger
from app.core.rate_limiter import check_rate_limit, rate_limit_upload
from app.core.validators import (
    validate_image_magic_bytes,
    validate_image_size,
)
from app.models.ml import ProcessedImage
from app.models.product import ProductCategory
from app.models.user import User
from app.schemas.product import ProductCreate, VariantCreate
from app.services.image_processing_service import ImageCategory, ImageProcessingService
from app.services.product_service import ProductService

router = APIRouter(prefix="/images", tags=["Image Processing"])
logger = get_logger("image_routes")

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_BATCH_FILES = 10


# ── Background task runners ───────────────────────────────────────────────────

async def _run_process_image_task(
    image_id: uuid.UUID,
    category_value: str,
    custom_prompt: str | None,
):
    async with async_session_factory() as session:
        try:
            category = ImageCategory(category_value)
            service = ImageProcessingService(session)
            result = await service.process_image(
                image_id=image_id,
                category=category,
                custom_prompt=custom_prompt,
            )
            if "error" in result:
                logger.error("Background processing failed for %s: %s", image_id, result["error"])
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Background processing crashed for %s", image_id)


async def _run_reprocess_image_task(
    image_id: uuid.UUID,
    custom_prompt: str,
    category_value: str | None,
):
    async with async_session_factory() as session:
        try:
            service = ImageProcessingService(session)
            category = ImageCategory(category_value) if category_value else None
            result = await service.reject_and_reprocess(
                image_id=image_id,
                custom_prompt=custom_prompt,
                category=category,
            )
            if "error" in result:
                logger.error("Background reprocess failed for %s: %s", image_id, result["error"])
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Background reprocess crashed for %s", image_id)


# ── Schemas ───────────────────────────────────────────────────────────────────

class ProcessImageRequest(BaseModel):
    image_id: uuid.UUID
    category: str = Field(..., description="cake, sweet, pastry, cookie, bread, drink")
    custom_prompt: str | None = Field(None, max_length=2000)


class RejectImageRequest(BaseModel):
    image_id: uuid.UUID
    custom_prompt: str = Field(..., min_length=5, max_length=2000)
    category: str | None = None


class ChooseImageRequest(BaseModel):
    image_id: uuid.UUID
    choice: str = Field(..., description="'original' or 'processed'")


class PublishProductFromImageRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    short_description: str | None = Field(None, max_length=500)
    description: str | None = None
    category: str = "cake"
    base_price: Decimal = Field(..., gt=0, le=9999)
    is_cake: bool = True
    is_featured: bool = False
    max_per_order: int | None = Field(None, ge=1, le=100)
    sort_order: int = Field(0, ge=0)
    tags: list[str] | None = None
    create_default_variant: bool = True
    variant_name: str = Field("Default", min_length=1, max_length=100)
    stock_quantity: int = Field(0, ge=0, le=9999)
    low_stock_threshold: int = Field(5, ge=0, le=9999)


# ── Upload endpoints ──────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    product_id: uuid.UUID | None = Form(None),
    custom_cake_id: uuid.UUID | None = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    [Admin] Upload a product image to S3.
    Raw bytes are validated against known image magic bytes — Content-Type spoofing is rejected.
    Use /process to enhance with Gemini AI.
    """
    await rate_limit_upload(request, user_id=str(admin.id))

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed: {', '.join(sorted(ALLOWED_TYPES))}",
        )

    image_data = await file.read()
    validate_image_size(image_data)
    detected_mime = validate_image_magic_bytes(image_data)

    service = ImageProcessingService(db)
    result = await service.upload_and_save_image(
        image_data=image_data,
        filename=file.filename or "unknown",
        content_type=detected_mime,
        product_id=product_id,
        custom_cake_id=custom_cake_id,
        uploaded_by=admin.id,
    )
    return result


@router.post("/upload-multiple")
async def upload_multiple_images(
    request: Request,
    files: list[UploadFile] = File(...),
    product_id: uuid.UUID | None = Form(None),
    custom_cake_id: uuid.UUID | None = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Upload up to 10 product images at once. Each is validated and stored in S3."""
    await rate_limit_upload(request, user_id=str(admin.id))

    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_BATCH_FILES} files per batch.")

    results = []
    errors = []

    for file in files:
        if file.content_type not in ALLOWED_TYPES:
            errors.append({"filename": file.filename, "error": f"Invalid type: {file.content_type}"})
            continue

        image_data = await file.read()
        if len(image_data) > MAX_IMAGE_SIZE:
            errors.append({"filename": file.filename, "error": "File too large (max 10 MB)"})
            continue

        try:
            detected_mime = validate_image_magic_bytes(image_data)
        except HTTPException as exc:
            errors.append({"filename": file.filename, "error": exc.detail})
            continue

        service = ImageProcessingService(db)
        result = await service.upload_and_save_image(
            image_data=image_data,
            filename=file.filename or "unknown",
            content_type=detected_mime,
            product_id=product_id,
            custom_cake_id=custom_cake_id,
            uploaded_by=admin.id,
        )
        results.append(result)

    return {"uploaded": len(results), "errors": len(errors), "images": results, "failed": errors}


# ── Process endpoints ─────────────────────────────────────────────────────────

@router.post("/process")
async def process_image(
    request: Request,
    data: ProcessImageRequest,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    [Admin] Process an uploaded image with Gemini AI.
    Returns immediately (queued=true). Poll GET /{image_id} for completion status.
    """
    await check_rate_limit(request, limit=10, window=60, user_id=str(admin.id))

    try:
        category = ImageCategory(data.category.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{data.category}'. Must be one of: {', '.join(c.value for c in ImageCategory)}",
        )

    result = await db.execute(select(ProcessedImage).where(ProcessedImage.id == data.image_id))
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    if image.processing_status in {"processing", "reprocessing"}:
        return {"image_id": str(data.image_id), "status": image.processing_status, "message": "Already processing."}

    image.processing_status = "processing"
    image.error_message = None
    await db.flush()

    background_tasks.add_task(_run_process_image_task, data.image_id, category.value, data.custom_prompt)

    return {"image_id": str(data.image_id), "status": "processing", "message": "Processing started.", "queued": True}


@router.post("/process-batch")
async def process_batch(
    request: Request,
    image_ids: list[uuid.UUID],
    background_tasks: BackgroundTasks,
    category: str = Query(...),
    custom_prompt: str | None = Query(None, max_length=2000),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Process multiple images with the same category."""
    await check_rate_limit(request, limit=5, window=60, user_id=str(admin.id))

    if len(image_ids) > MAX_BATCH_FILES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_BATCH_FILES} images per batch.")

    try:
        cat = ImageCategory(category.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    queued_ids: list[str] = []
    missing_ids: list[str] = []

    for image_id in image_ids:
        result = await db.execute(select(ProcessedImage).where(ProcessedImage.id == image_id))
        image = result.scalar_one_or_none()
        if not image:
            missing_ids.append(str(image_id))
            continue
        if image.processing_status in {"processing", "reprocessing"}:
            queued_ids.append(str(image_id))
            continue
        image.processing_status = "processing"
        image.error_message = None
        queued_ids.append(str(image_id))
        background_tasks.add_task(_run_process_image_task, image_id, cat.value, custom_prompt)

    await db.flush()
    return {
        "total": len(image_ids), "queued": len(queued_ids), "missing": len(missing_ids),
        "queued_image_ids": queued_ids, "missing_image_ids": missing_ids,
    }


# ── Reject & re-process ───────────────────────────────────────────────────────

@router.post("/reject")
async def reject_and_reprocess(
    request: Request,
    data: RejectImageRequest,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Reject a processed image and re-process with custom instructions."""
    await check_rate_limit(request, limit=10, window=60, user_id=str(admin.id))

    cat = None
    if data.category:
        try:
            cat = ImageCategory(data.category.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {data.category}")

    result = await db.execute(select(ProcessedImage).where(ProcessedImage.id == data.image_id))
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    if image.processing_status in {"processing", "reprocessing"}:
        return {"image_id": str(data.image_id), "status": image.processing_status, "message": "Already processing."}

    image.processing_status = "reprocessing"
    image.admin_chosen = None
    image.rejection_reason = data.custom_prompt
    image.error_message = None
    await db.flush()

    background_tasks.add_task(
        _run_reprocess_image_task, data.image_id, data.custom_prompt, cat.value if cat else None
    )

    return {"image_id": str(data.image_id), "status": "reprocessing", "message": "Reprocessing started.", "queued": True}


# ── Admin choose / delete ─────────────────────────────────────────────────────

@router.post("/choose")
async def choose_image_version(
    data: ChooseImageRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Choose which version (original / processed) to publish."""
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
    """[Admin] Delete an image — removes the DB record and both S3 objects."""
    service = ImageProcessingService(db)
    deleted = await service.delete_image(image_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Image not found")
    return {"message": "Image deleted", "image_id": str(image_id)}


# ── Image serving — S3 pre-signed URL redirects ───────────────────────────────

@router.get("/{image_id}/selected/public")
async def get_public_selected_image(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Public image endpoint for the storefront.
    Returns HTTP 307 redirect to a time-limited S3 pre-signed URL (24 h TTL).
    Only works for images explicitly approved by admin (admin_chosen set).
    Legacy base64 images are served inline for backward compatibility.
    """
    result = await db.execute(select(ProcessedImage).where(ProcessedImage.id == image_id))
    image = result.scalar_one_or_none()
    if not image or image.admin_chosen not in ("original", "processed"):
        raise HTTPException(status_code=404, detail="Approved image not found")

    selected_url, selected_source = ImageProcessingService.resolve_selected_image_url(image)
    if not selected_url:
        raise HTTPException(status_code=404, detail="Approved image source missing")

    # Legacy: normalise framing and persist
    if selected_url.startswith("data:"):
        normalized_url, changed = ImageProcessingService.normalize_public_data_url(selected_url)
        if changed and selected_source == "processed":
            image.processed_url = normalized_url
            await db.flush()
        selected_url = normalized_url

    from app.core.config import get_settings
    return await ImageProcessingService.build_serve_response(
        selected_url, ttl=get_settings().S3_PRESIGNED_URL_TTL
    )


@router.get("/{image_id}/original")
async def get_original_image(
    image_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get the original uploaded image — 307 redirect to S3 pre-signed URL (1 h TTL)."""
    result = await db.execute(select(ProcessedImage).where(ProcessedImage.id == image_id))
    image = result.scalar_one_or_none()
    if not image or not image.original_url:
        raise HTTPException(status_code=404, detail="Image not found")

    from app.core.config import get_settings
    return await ImageProcessingService.build_serve_response(
        image.original_url, ttl=get_settings().S3_ADMIN_URL_TTL
    )


@router.get("/{image_id}/processed")
async def get_processed_image(
    image_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get the Gemini-processed image — 307 redirect to S3 pre-signed URL (1 h TTL)."""
    result = await db.execute(select(ProcessedImage).where(ProcessedImage.id == image_id))
    image = result.scalar_one_or_none()
    if not image or not image.processed_url:
        raise HTTPException(status_code=404, detail="Processed image not found")

    from app.core.config import get_settings
    return await ImageProcessingService.build_serve_response(
        image.processed_url, ttl=get_settings().S3_ADMIN_URL_TTL
    )


# ── List / detail ─────────────────────────────────────────────────────────────

@router.get("/{image_id}")
async def get_image_details(
    image_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get image metadata (no raw data returned)."""
    service = ImageProcessingService(db)
    result = await service.get_image(image_id)
    if not result:
        raise HTTPException(status_code=404, detail="Image not found")
    return result


@router.get("/")
async def list_images(
    product_id: uuid.UUID | None = Query(None),
    custom_cake_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    include_published: bool = Query(False),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] List all uploaded images with optional filters."""
    valid_statuses = {"uploaded", "processing", "completed", "failed", "reprocessing", "published"}
    if status and status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}",
        )

    service = ImageProcessingService(db)
    return await service.list_images(
        product_id=product_id,
        custom_cake_id=custom_cake_id,
        status=status,
        include_published=include_published,
    )


# ── Publish ───────────────────────────────────────────────────────────────────

@router.post("/{image_id}/publish-product")
async def publish_image_as_product(
    image_id: uuid.UUID,
    data: PublishProductFromImageRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Publish an approved image as a new product."""
    result = await db.execute(select(ProcessedImage).where(ProcessedImage.id == image_id))
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    if image.product_id is not None:
        raise HTTPException(status_code=409, detail="This image has already been published as a product.")

    if image.admin_chosen not in ("original", "processed"):
        raise HTTPException(status_code=400, detail="Approve an image version first (Original or Processed).")

    selected_url, selected_source = ImageProcessingService.resolve_selected_image_url(image)
    if not selected_url:
        raise HTTPException(status_code=400, detail="Selected image data is missing.")

    try:
        ProductCategory(data.category)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category '{data.category}'.")

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
    image.processing_status = "published"
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
    include_published: bool = Query(False),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] List all uploaded images with optional filters."""
    service = ImageProcessingService(db)
    return await service.list_images(
        product_id=product_id,
        custom_cake_id=custom_cake_id,
        status=status,
        include_published=include_published,
    )


# ── Category Prompts Info ────────────────────────────────────────────────────
@router.get("/categories/prompts")
async def get_category_prompts(admin: User = Depends(require_admin)):
    """[Admin] View the AI prompts used for each product category."""
    from app.services.image_processing_service import CATEGORY_PROMPTS
    return {cat.value: prompt for cat, prompt in CATEGORY_PROMPTS.items()}
