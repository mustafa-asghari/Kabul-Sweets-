"""
Image Processing Service — Gemini Imagen Integration.

Uses Google Gemini for AI-powered product photo enhancement.
Each image is processed in a SEPARATE API call (isolated context).
Category-specific prompts for different product types.
Admin can reject results and add custom prompts for re-processing.

Storage
-------
All image bytes (original uploads and Gemini results) are stored in AWS S3.
The database only keeps the S3 object key — never raw base64 blobs.

Backward compatibility: existing rows that contain "data:image/…;base64,…" strings
are served directly so old records keep working without a migration.
"""

import asyncio
import base64
import io
import uuid
from collections import deque
from enum import Enum

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("image_processing")
settings = get_settings()

GEMINI_API_KEY = settings.GEMINI_API_KEY.strip()
GEMINI_MODEL = (settings.GEMINI_IMAGE_MODEL or "gemini-2.0-flash-exp-image-generation").strip()

try:
    from PIL import Image
except Exception:
    Image = None  # pragma: no cover

PURE_WHITE_BG_MIN_CHANNEL = 250
PURE_WHITE_BG_MIN_RATIO = 0.995
PURE_WHITE_BG_BORDER_RATIO = 0.06
BG_SEED_MIN_CHANNEL = 220
BG_EXPAND_MIN_CHANNEL = 236
BG_EXPAND_NEUTRAL_MIN_VALUE = 200
BG_EXPAND_NEUTRAL_MAX_CHROMA = 16
SUBJECT_DETECT_MAX_CHANNEL = 248
SUBJECT_IGNORE_NEUTRAL_MIN_VALUE = 226
SUBJECT_IGNORE_NEUTRAL_MAX_CHROMA = 14
SUBJECT_STRICT_MIN_AREA_RATIO = 0.02
SUBJECT_STRICT_MIN_BBOX_AREA_RATIO = 0.16
FRAME_TARGET_OCCUPANCY = 0.82
FRAME_SUBJECT_MARGIN_RATIO = 0.03
FRAME_MIN_OUTPUT_SIDE = 1000
FRAME_MAX_OUTPUT_SIDE = 1400


# ── Category Prompts ─────────────────────────────────────────────────────────
class ImageCategory(str, Enum):
    CAKE = "cake"
    SWEET = "sweet"
    PASTRY = "pastry"
    COOKIE = "cookie"
    BREAD = "bread"
    DRINK = "drink"


CATEGORY_PROMPTS = {
    ImageCategory.CAKE: (
        "Transform this cake into a professional e-commerce product photo. "
        "Preserve the original cake design exactly (shape, colors, decorations, texture, and details). "
        "Do not redesign, simplify, or replace decorations. "
        "Use a clean studio background (pure white or very light neutral gray is acceptable). "
        "Place the cake centered with balanced studio lighting and NO shadow on the background, NO floor shadow, and NO reflection. "
        "Use a consistent camera distance and framing: cake + cake board must be fully visible, with balanced white space around the subject (roughly 80-85% frame occupancy). "
        "Do NOT add any cake stand, pedestal, plate, props, table textures, or decorative scene elements. "
        "A thin flat cake board under the cake is allowed, but no raised stand. "
        "Do NOT add any text, lettering, handwriting, logo, watermark, scribbles, or random lines on top of the cake. "
        "Do NOT add any decorative script, edible pen writing, piped words, stamp marks, or artifact lines anywhere on the cake. "
        "Keep the top surface clean and natural with no artificial writing artifacts. "
        "Enhance details of the frosting texture and printed animal decorations. "
        "Keep proportions and colours accurate and realistic. "
        "Commercial food photography, ultra high resolution, sharp focus, luxury bakery advertisement style."
    ),

    ImageCategory.SWEET: (
        "Transform this sweet/confection into a professional e-commerce product photo. "
        "Preserve the original design exactly (shape, colors, decorations, texture, and details). "
        "Do not redesign, simplify, or replace decorations. "
        "Use a clean studio background (pure white or very light neutral gray is acceptable). "
        "Place the sweets centered with balanced studio lighting and NO shadow on the background, NO floor shadow, and NO reflection. "
        "Use a consistent camera distance and framing: subject must be fully visible, with balanced white space around the subject (roughly 80-85% frame occupancy). "
        "Do NOT add any plate, tray, platter, props, table textures, or decorative scene elements. "
        "Enhance the texture details — show the shimmer of sugar, the richness of nuts, the smooth fudge surface. "
        "Do NOT add any text, lettering, logo, watermark, or random lines on the product. "
        "Keep proportions, colours, and traditional plating accurate and realistic. "
        "Commercial food photography, ultra high resolution, sharp focus, premium confectionery advertisement style."
    ),

    ImageCategory.PASTRY: (
        "Transform this pastry into a professional e-commerce product photo. "
        "Preserve the original pastry design exactly (shape, colors, layers, texture, and details). "
        "Do not redesign, simplify, or replace decorations. "
        "Use a clean studio background (pure white or very light neutral gray is acceptable). "
        "Place the pastry centered with balanced studio lighting and NO shadow on the background, NO floor shadow, and NO reflection. "
        "Use a consistent camera distance and framing: subject must be fully visible, with balanced white space around the subject (roughly 80-85% frame occupancy). "
        "Do NOT add any plate, tray, props, table textures, or decorative scene elements. "
        "Enhance the flaky layers, golden crispy texture, and powdered sugar details. "
        "Do NOT add any text, lettering, logo, watermark, or random lines on the product. "
        "Keep proportions, colours, and the delicate form accurate and realistic. "
        "Commercial food photography, ultra high resolution, sharp focus, artisan bakery advertisement style."
    ),

    ImageCategory.COOKIE: (
        "Transform these cookies/baklava into a professional e-commerce product photo. "
        "Preserve the original design exactly (shape, colors, patterns, texture, and details). "
        "Do not redesign, simplify, or replace decorations. "
        "Use a clean studio background (pure white or very light neutral gray is acceptable). "
        "Arrange the cookies/baklava in an appealing layout, centered with balanced studio lighting "
        "and NO shadow on the background, NO floor shadow, and NO reflection. "
        "Use a consistent camera distance and framing: subject must be fully visible, with balanced white space around the subject (roughly 80-85% frame occupancy). "
        "Do NOT add any plate, tray, props, table textures, or decorative scene elements. "
        "Enhance the intricate patterns, golden baked surfaces, pistachio and walnut details. "
        "Do NOT add any text, lettering, logo, watermark, or random lines on the product. "
        "Keep proportions, colours, and traditional decorative patterns accurate and realistic. "
        "Commercial food photography, ultra high resolution, sharp focus, luxury bakery advertisement style."
    ),

    ImageCategory.BREAD: (
        "Transform this bread into a professional e-commerce product photo. "
        "Preserve the original bread exactly (shape, colors, crust, texture, and details). "
        "Do not redesign, simplify, or replace any features. "
        "Use a clean studio background (pure white or very light neutral gray is acceptable). "
        "Place the bread centered with balanced studio lighting and NO shadow on the background, NO floor shadow, and NO reflection. "
        "Use a consistent camera distance and framing: subject must be fully visible, with balanced white space around the subject (roughly 80-85% frame occupancy). "
        "Do NOT add any cutting board, plate, tray, props, table textures, or decorative scene elements. "
        "Enhance the crust texture, golden-brown colour, and stuffing details if visible. "
        "Do NOT add any text, lettering, logo, watermark, or random lines on the product. "
        "Keep proportions, colours, and artisan qualities accurate and realistic. "
        "Commercial food photography, ultra high resolution, sharp focus, artisan bread advertisement style."
    ),

    ImageCategory.DRINK: (
        "Transform this beverage/tea into a professional e-commerce product photo. "
        "Preserve the original packaging and product exactly (shape, colors, label, and details). "
        "Do not redesign, simplify, or replace any features. "
        "Use a clean studio background (pure white or very light neutral gray is acceptable). "
        "Place the product centered with balanced studio lighting and NO shadow on the background, NO floor shadow, and NO reflection. "
        "Use a consistent camera distance and framing: subject must be fully visible, with balanced white space around the subject (roughly 80-85% frame occupancy). "
        "Do NOT add any tray, props, table textures, or decorative scene elements. "
        "Enhance the packaging details, label text clarity, and overall presentation. "
        "Do NOT add any extra text, lettering, logo, watermark, or random lines on the product. "
        "Keep proportions, colours, and branding accurate and realistic. "
        "Commercial food photography, ultra high resolution, sharp focus, premium product advertisement style."
    ),
}


class ImageProcessingService:
    """
    Processes product images using Google Gemini.
    Each image is processed in its own isolated API call — no shared context.

    Storage model
    ─────────────
    • New records  → original_url / processed_url hold S3 object keys
                     (e.g. "images/originals/550e8400….jpg")
    • Legacy records → original_url / processed_url hold base64 data URLs
                     (e.g. "data:image/jpeg;base64,…")
    Both formats are supported transparently.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Internal helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _is_s3_key(value: str | None) -> bool:
        """Return True if the value is an S3 key rather than a base64 data URL."""
        return bool(value) and not value.startswith("data:")

    @staticmethod
    async def _bytes_from_url(url: str, content_type: str | None) -> tuple[bytes, str]:
        """
        Return (raw_bytes, mime_type) whether the url is an S3 key or a base64 data URL.
        """
        if url.startswith("data:"):
            # Legacy base64 format
            header, b64 = url.split(",", 1)
            mime = header.split(";")[0].split(":")[1]
            return base64.b64decode(b64), mime
        else:
            # S3 key
            from app.services.storage_service import get_storage
            data = await get_storage().download(url)
            mime = content_type or "image/jpeg"
            return data, mime

    # ── Upload ───────────────────────────────────────────────────────────────

    async def upload_and_save_image(
        self,
        image_data: bytes,
        filename: str,
        content_type: str,
        product_id: uuid.UUID | None = None,
        custom_cake_id: uuid.UUID | None = None,
        uploaded_by: uuid.UUID | None = None,
    ) -> dict:
        """
        Upload an image to S3 and record its metadata in the database.
        The database stores only the S3 key — no base64.
        """
        from app.models.ml import ProcessedImage
        from app.services.storage_service import StorageService, get_storage

        image_id = uuid.uuid4()
        storage = get_storage()

        # Build S3 key and upload
        s3_key = StorageService.key_for_original(image_id, content_type)
        await storage.upload(s3_key, image_data, content_type)

        image = ProcessedImage(
            id=image_id,
            product_id=product_id,
            custom_cake_id=custom_cake_id,
            original_url=s3_key,          # S3 key, not base64
            processing_type="enhancement",
            processing_status="uploaded",
            original_size_bytes=len(image_data),
            original_filename=filename,
            content_type=content_type,
            uploaded_by=uploaded_by,
        )
        self.db.add(image)
        await self.db.flush()
        await self.db.refresh(image)

        logger.info("Image uploaded to S3: %s (%d bytes) → %s", filename, len(image_data), s3_key)

        return {
            "image_id": str(image.id),
            "filename": filename,
            "size_bytes": len(image_data),
            "status": "uploaded",
            "message": "Image saved to S3. Use /process to enhance it with AI.",
        }

    # ── Process ──────────────────────────────────────────────────────────────

    async def process_image(
        self,
        image_id: uuid.UUID,
        category: ImageCategory,
        custom_prompt: str | None = None,
    ) -> dict:
        """
        Process a SINGLE image with Gemini AI.
        Downloads from S3 (or reads legacy base64), sends to Gemini,
        uploads the result back to S3, and stores only the key in the DB.
        """
        from app.models.ml import ProcessedImage
        from app.services.storage_service import StorageService, get_storage

        result = await self.db.execute(
            select(ProcessedImage).where(ProcessedImage.id == image_id)
        )
        image = result.scalar_one_or_none()
        if not image:
            return {"error": "Image not found"}

        if not image.original_url:
            return {"error": "No original image data found"}

        image.processing_status = "processing"
        await self.db.flush()

        # Build the Gemini prompt
        base_prompt = CATEGORY_PROMPTS.get(category, CATEGORY_PROMPTS[ImageCategory.CAKE])
        full_prompt = (
            f"{base_prompt}\n\nADDITIONAL INSTRUCTIONS:\n{custom_prompt}"
            if custom_prompt
            else base_prompt
        )
        image.prompt_used = full_prompt
        image.category_used = category.value

        try:
            # ── 1. Get original image bytes ────────────────────────────────
            image_bytes, mime_type = await self._bytes_from_url(
                image.original_url, image.content_type
            )

            # ── 2. Resize for Gemini if needed (> 3 MB) ───────────────────
            b64_data = base64.b64encode(image_bytes).decode("utf-8")
            if len(b64_data) > 3 * 1024 * 1024 and Image is not None:
                try:
                    with Image.open(io.BytesIO(image_bytes)) as pil_img:
                        max_dim = max(pil_img.size)
                        if max_dim > 1600:
                            scale = 1600 / max_dim
                            new_w = int(pil_img.width * scale)
                            new_h = int(pil_img.height * scale)
                            resized = pil_img.resize((new_w, new_h), Image.Resampling.BILINEAR)
                            buf = io.BytesIO()
                            fmt = "PNG" if "png" in mime_type.lower() else "JPEG"
                            resized.save(buf, format=fmt, quality=85, optimize=True)
                            b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
                            logger.info(
                                "Resized image for Gemini: %dx%d → %dx%d",
                                pil_img.width, pil_img.height, new_w, new_h,
                            )
                except Exception as resize_err:
                    logger.warning("Could not resize image for Gemini: %s", resize_err)

            # ── 3. Call Gemini ─────────────────────────────────────────────
            processed_b64, error = await self._call_gemini(
                image_b64=b64_data,
                mime_type=mime_type,
                prompt=full_prompt,
            )

            if error:
                image.processing_status = "failed"
                image.error_message = error
                await self.db.flush()
                return {"error": error, "image_id": str(image_id)}

            # ── 4. Normalise framing ────────────────────────────────────────
            processed_b64, output_mime, framing_changed = self._normalize_image_framing(
                processed_b64, mime_type
            )

            # ── 5. Upload processed image to S3 ───────────────────────────
            processed_bytes = base64.b64decode(processed_b64)
            storage = get_storage()

            if self._is_s3_key(image.original_url):
                # New-format record: upload processed bytes to S3
                processed_key = StorageService.key_for_processed(image_id, output_mime)
                await storage.upload(processed_key, processed_bytes, output_mime)
                image.processed_url = processed_key
            else:
                # Legacy record: keep result as base64 for backward compat
                image.processed_url = f"data:{output_mime};base64,{processed_b64}"

            image.processed_size_bytes = len(processed_bytes)
            image.processing_status = "completed"
            image.error_message = None
            image.processing_attempts = (image.processing_attempts or 0) + 1
            await self.db.flush()

            logger.info(
                "Image processed: %s (orig=%s → processed=%s bytes)",
                image_id,
                image.original_size_bytes,
                image.processed_size_bytes,
            )

            return {
                "image_id": str(image_id),
                "status": "completed",
                "original_size": image.original_size_bytes,
                "processed_size": image.processed_size_bytes,
                "category": category.value,
                "custom_prompt_used": bool(custom_prompt),
                "framing_normalized": framing_changed,
            }

        except Exception as exc:
            image.processing_status = "failed"
            image.error_message = str(exc)
            image.processing_attempts = (image.processing_attempts or 0) + 1
            await self.db.flush()
            logger.error("Image processing failed for %s: %s", image_id, exc)
            return {"error": str(exc), "image_id": str(image_id)}

    # ── Reject & reprocess ───────────────────────────────────────────────────

    async def reject_and_reprocess(
        self,
        image_id: uuid.UUID,
        custom_prompt: str,
        category: ImageCategory | None = None,
    ) -> dict:
        """Admin rejects a result and re-processes with a custom prompt."""
        from app.models.ml import ProcessedImage

        result = await self.db.execute(
            select(ProcessedImage).where(ProcessedImage.id == image_id)
        )
        image = result.scalar_one_or_none()
        if not image:
            return {"error": "Image not found"}

        cat = category or ImageCategory(image.category_used or "cake")

        image.processing_status = "reprocessing"
        image.admin_chosen = None
        image.rejection_reason = custom_prompt
        await self.db.flush()

        logger.info("Re-processing image %s with custom prompt", image_id)
        return await self.process_image(
            image_id=image_id,
            category=cat,
            custom_prompt=custom_prompt,
        )

    # ── Admin choose ─────────────────────────────────────────────────────────

    async def admin_choose_image(self, image_id: uuid.UUID, choice: str) -> dict:
        """Admin selects which version (original / processed) to publish."""
        from app.models.ml import ProcessedImage

        result = await self.db.execute(
            select(ProcessedImage).where(ProcessedImage.id == image_id)
        )
        image = result.scalar_one_or_none()
        if not image:
            return {"error": "Image not found"}

        if choice not in ("original", "processed"):
            return {"error": "Choice must be 'original' or 'processed'"}

        if choice == "processed" and image.processing_status != "completed":
            return {"error": "No processed image available yet"}

        image.admin_chosen = choice
        await self.db.flush()

        return {
            "image_id": str(image_id),
            "chosen": choice,
            "message": f"Admin chose the {choice} version",
        }

    # ── Get / list / delete ──────────────────────────────────────────────────

    async def get_image(self, image_id: uuid.UUID) -> dict | None:
        """Return image metadata (no raw data, no S3 keys exposed)."""
        from app.models.ml import ProcessedImage

        result = await self.db.execute(
            select(ProcessedImage).where(ProcessedImage.id == image_id)
        )
        image = result.scalar_one_or_none()
        if not image:
            return None

        return {
            "id": str(image.id),
            "product_id": str(image.product_id) if image.product_id else None,
            "custom_cake_id": str(image.custom_cake_id) if image.custom_cake_id else None,
            "original_filename": image.original_filename,
            "status": image.processing_status,
            "category": image.category_used,
            "original_size": image.original_size_bytes,
            "processed_size": image.processed_size_bytes,
            "admin_chosen": image.admin_chosen,
            "prompt_used": image.prompt_used,
            "rejection_reason": image.rejection_reason,
            "processing_attempts": image.processing_attempts,
            "error": image.error_message,
            "has_original": bool(image.original_url),
            "has_processed": bool(image.processed_url),
            "created_at": image.created_at.isoformat(),
        }

    async def delete_image(self, image_id: uuid.UUID) -> bool:
        """Delete both the DB record and the associated S3 objects."""
        from app.models.ml import ProcessedImage
        from app.services.storage_service import get_storage

        result = await self.db.execute(
            select(ProcessedImage).where(ProcessedImage.id == image_id)
        )
        image = result.scalar_one_or_none()
        if not image:
            return False

        storage = get_storage()

        # Delete S3 objects (silently skip failures to avoid blocking DB delete)
        for url in (image.original_url, image.processed_url):
            if url and self._is_s3_key(url):
                try:
                    await storage.delete(url)
                except Exception as exc:
                    logger.warning("Failed to delete S3 object %s: %s", url, exc)

        await self.db.delete(image)
        await self.db.flush()
        logger.info("Image deleted: %s", image_id)
        return True

    # ── Serving helpers ──────────────────────────────────────────────────────

    @staticmethod
    def resolve_selected_image_url(image) -> tuple[str | None, str]:
        """Return (url_or_key, selected_source) based on admin_chosen."""
        if image.admin_chosen == "processed" and image.processed_url:
            return image.processed_url, "processed"
        return image.original_url, "original"

    @staticmethod
    async def build_serve_response(url: str, content_type: str | None = None, ttl: int = 86400):
        """
        Build a FastAPI response for an image URL that may be either:
          - a base64 data URL (legacy) → decode and return bytes directly
          - an S3 object key (new)     → generate pre-signed URL → HTTP 307 redirect
        """
        import base64 as b64_module

        from fastapi.responses import RedirectResponse, Response

        if url.startswith("data:"):
            # Legacy: decode base64 and serve inline
            try:
                mime = url.split(";")[0].split(":")[1]
                raw = b64_module.b64decode(url.split(",", 1)[1])
                return Response(
                    content=raw,
                    media_type=mime,
                    headers={"Cache-Control": f"public, max-age={ttl}"},
                )
            except Exception:
                from fastapi import HTTPException
                raise HTTPException(status_code=500, detail="Failed to decode legacy image data")
        else:
            # New format: redirect to a time-limited S3 pre-signed URL
            from app.services.storage_service import get_storage
            presigned = await get_storage().presigned_url(url, ttl=ttl)
            return RedirectResponse(url=presigned, status_code=307)

    async def list_images(
        self,
        product_id: uuid.UUID | None = None,
        custom_cake_id: uuid.UUID | None = None,
        status: str | None = None,
        include_published: bool = False,
        limit: int = 50,
    ) -> list[dict]:
        """List images with optional filters (no raw data returned)."""
        from app.models.ml import ProcessedImage

        query = select(ProcessedImage).order_by(desc(ProcessedImage.created_at))
        if product_id:
            query = query.where(ProcessedImage.product_id == product_id)
        elif not include_published:
            query = query.where(ProcessedImage.product_id.is_(None))
        if custom_cake_id:
            query = query.where(ProcessedImage.custom_cake_id == custom_cake_id)
        if status:
            query = query.where(ProcessedImage.processing_status == status)
        query = query.limit(limit)

        result = await self.db.execute(query)
        images = result.scalars().all()

        return [
            {
                "id": str(img.id),
                "product_id": str(img.product_id) if img.product_id else None,
                "original_filename": img.original_filename,
                "status": img.processing_status,
                "category": img.category_used,
                "admin_chosen": img.admin_chosen,
                "processing_attempts": img.processing_attempts,
                "has_processed": bool(img.processed_url),
                "created_at": img.created_at.isoformat(),
            }
            for img in images
        ]

    # ── Gemini API call ──────────────────────────────────────────────────────

    async def _call_gemini(
        self,
        image_b64: str,
        mime_type: str,
        prompt: str,
    ) -> tuple[str | None, str | None]:
        """
        Single, isolated Gemini API call.
        Returns (processed_image_b64, error_message).
        """
        if not GEMINI_API_KEY:
            logger.warning("Gemini API key not configured — skipping image processing")
            return None, "Gemini API key not configured. Set GEMINI_API_KEY in .env"

        import httpx

        url = (
            f"https://generativelanguage.googleapis.com/v1beta"
            f"/models/{GEMINI_MODEL}:generateContent"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"inlineData": {"mimeType": mime_type, "data": image_b64}},
                        {"text": prompt},
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["IMAGE", "TEXT"],
                "temperature": 1.0,
            },
        }

        max_attempts = 2
        timeout = httpx.Timeout(60.0, connect=10.0)
        last_error: str | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout, http2=False) as client:
                    response = await client.post(
                        url,
                        params={"key": GEMINI_API_KEY},
                        json=payload,
                    )

                if response.status_code in (429, 500, 502, 503, 504):
                    error_body = response.text[:500] if response.text else "Unknown"
                    last_error = f"Gemini API error ({response.status_code}): {error_body}"
                    if attempt < max_attempts:
                        wait = 1.5 * (2 ** (attempt - 1))
                        logger.warning(
                            "Gemini transient %d (attempt %d/%d). Retry in %.1fs",
                            response.status_code, attempt, max_attempts, wait,
                        )
                        await asyncio.sleep(wait)
                        continue
                    return None, last_error

                response.raise_for_status()
                data = response.json()

                candidates = data.get("candidates", [])
                if not candidates:
                    return None, "No response from Gemini"

                parts = candidates[0].get("content", {}).get("parts", [])

                for part in parts:
                    if "inlineData" in part:
                        return part["inlineData"]["data"], None

                for part in parts:
                    if "text" in part:
                        return None, f"Gemini returned text instead of image: {part['text'][:200]}"

                return None, "Gemini response contained no image data"

            except httpx.HTTPStatusError as exc:
                body = exc.response.text[:500] if exc.response else "Unknown"
                last_error = f"Gemini API error ({exc.response.status_code}): {body}"
                logger.error("Gemini HTTP error %d: %s", exc.response.status_code, body)
                return None, last_error

            except (
                httpx.RemoteProtocolError,
                httpx.ReadError,
                httpx.ReadTimeout,
                httpx.ConnectError,
                httpx.WriteError,
            ) as exc:
                last_error = f"Gemini transport error: {exc}"
                if attempt < max_attempts:
                    wait = 1.5 * (2 ** (attempt - 1))
                    logger.warning(
                        "Gemini transport error attempt %d/%d: %s. Retry in %.1fs",
                        attempt, max_attempts, exc, wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                return None, last_error

            except Exception as exc:
                logger.error("Gemini call failed: %s", exc)
                return None, f"Gemini call failed: {exc}"

        return None, last_error or "Gemini call failed for unknown reason"

    # ── Framing normalisation ────────────────────────────────────────────────

    @staticmethod
    def normalize_public_data_url(data_url: str) -> tuple[str, bool]:
        """Normalise a legacy base64 data URL. Returns (url, changed)."""
        if not data_url.startswith("data:"):
            return data_url, False

        try:
            header, image_b64 = data_url.split(",", 1)
            mime_type = header.split(";")[0].split(":")[1]
        except Exception:
            return data_url, False

        normalized_b64, normalized_mime, changed = (
            ImageProcessingService._normalize_image_framing(image_b64, mime_type)
        )
        if not changed:
            return data_url, False
        return f"data:{normalized_mime};base64,{normalized_b64}", True

    @staticmethod
    def _normalize_image_framing(
        image_b64: str,
        mime_type: str,
    ) -> tuple[str, str, bool]:
        """
        Enforce a pure-white background and place the subject on a square frame
        with consistent occupancy for visual consistency across product cards.
        """
        if Image is None:
            return image_b64, mime_type, False

        try:
            image_bytes = base64.b64decode(image_b64)
            with Image.open(io.BytesIO(image_bytes)) as img:
                rgba = img.convert("RGBA")

            flattened = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            flattened.paste(rgba, mask=rgba)
            rgb = flattened.convert("RGB")

            width, height = rgb.size
            if width < 16 or height < 16:
                return image_b64, mime_type, False

            total_pixels = width * height

            if total_pixels > 2000 * 2000:
                logger.info(
                    "Image too large for BFS analysis (%dx%d). Skipping normalisation.",
                    width, height,
                )
                return image_b64, mime_type, False

            pixels = rgb.load()
            visited = bytearray(total_pixels)
            queue: deque[tuple[int, int]] = deque()

            def to_index(x: int, y: int) -> int:
                return y * width + x

            def is_seed_bg(px: tuple[int, int, int]) -> bool:
                value = max(px)
                chroma = max(px) - min(px)
                return (
                    (px[0] >= BG_SEED_MIN_CHANNEL and px[1] >= BG_SEED_MIN_CHANNEL and px[2] >= BG_SEED_MIN_CHANNEL)
                    or (value >= BG_SEED_MIN_CHANNEL and chroma <= BG_EXPAND_NEUTRAL_MAX_CHROMA)
                )

            def is_expand_bg(px: tuple[int, int, int]) -> bool:
                value = max(px)
                chroma = max(px) - min(px)
                return (
                    (px[0] >= BG_EXPAND_MIN_CHANNEL and px[1] >= BG_EXPAND_MIN_CHANNEL and px[2] >= BG_EXPAND_MIN_CHANNEL)
                    or (value >= BG_EXPAND_NEUTRAL_MIN_VALUE and chroma <= BG_EXPAND_NEUTRAL_MAX_CHROMA)
                )

            for x in range(width):
                if is_seed_bg(pixels[x, 0]):
                    queue.append((x, 0))
                if is_seed_bg(pixels[x, height - 1]):
                    queue.append((x, height - 1))
            for y in range(height):
                if is_seed_bg(pixels[0, y]):
                    queue.append((0, y))
                if is_seed_bg(pixels[width - 1, y]):
                    queue.append((width - 1, y))

            while queue:
                x, y = queue.popleft()
                idx = to_index(x, y)
                if visited[idx]:
                    continue
                if not is_expand_bg(pixels[x, y]):
                    continue
                visited[idx] = 1
                if x > 0:
                    queue.append((x - 1, y))
                if x < width - 1:
                    queue.append((x + 1, y))
                if y > 0:
                    queue.append((x, y - 1))
                if y < height - 1:
                    queue.append((x, y + 1))

            def detect_subject_bounds(ignore_neutral_light: bool) -> tuple[int, int, int, int, int]:
                left, top, right, bottom = width, height, -1, -1
                subject_pixels = 0
                for y in range(height):
                    row_start = y * width
                    for x in range(width):
                        r, g, b = pixels[x, y]
                        value = max(r, g, b)
                        chroma = max(r, g, b) - min(r, g, b)
                        if (
                            ignore_neutral_light
                            and (
                                visited[row_start + x]
                                or (value >= SUBJECT_IGNORE_NEUTRAL_MIN_VALUE and chroma <= SUBJECT_IGNORE_NEUTRAL_MAX_CHROMA)
                            )
                        ):
                            continue
                        if r < SUBJECT_DETECT_MAX_CHANNEL or g < SUBJECT_DETECT_MAX_CHANNEL or b < SUBJECT_DETECT_MAX_CHANNEL:
                            subject_pixels += 1
                            if x < left:
                                left = x
                            if x > right:
                                right = x
                            if y < top:
                                top = y
                            if y > bottom:
                                bottom = y
                return left, top, right, bottom, subject_pixels

            left, top, right, bottom, strict_pixels = detect_subject_bounds(ignore_neutral_light=True)
            strict_area_ratio = strict_pixels / total_pixels if total_pixels else 0.0
            strict_bbox_ratio = 0.0
            if right >= left and bottom >= top:
                strict_bbox_ratio = ((right - left + 1) * (bottom - top + 1)) / total_pixels

            if (
                strict_pixels == 0
                or strict_area_ratio < SUBJECT_STRICT_MIN_AREA_RATIO
                or strict_bbox_ratio < SUBJECT_STRICT_MIN_BBOX_AREA_RATIO
            ):
                left, top, right, bottom, _ = detect_subject_bounds(ignore_neutral_light=False)

            if right < left or bottom < top:
                subject_crop = rgb
            else:
                margin = max(2, int(min(width, height) * FRAME_SUBJECT_MARGIN_RATIO))
                subject_crop = rgb.crop((
                    max(0, left - margin),
                    max(0, top - margin),
                    min(width, right + margin + 1),
                    min(height, bottom + margin + 1),
                ))

            crop_w, crop_h = subject_crop.size
            if crop_w < 2 or crop_h < 2:
                return image_b64, mime_type, False

            output_side = min(max(max(width, height), 800), 1200)
            target_subject = max(1, int(output_side * FRAME_TARGET_OCCUPANCY))
            scale = min(target_subject / crop_w, target_subject / crop_h)
            resized_w = max(1, int(round(crop_w * scale)))
            resized_h = max(1, int(round(crop_h * scale)))

            resampling = getattr(Image, "Resampling", Image)
            resized = subject_crop.resize((resized_w, resized_h), resampling.BILINEAR)

            canvas = Image.new("RGB", (output_side, output_side), (255, 255, 255))
            canvas.paste(resized, ((output_side - resized_w) // 2, (output_side - resized_h) // 2))

            buf = io.BytesIO()
            target_mime = mime_type.lower()
            if "png" in target_mime:
                canvas.save(buf, format="PNG", optimize=False, compress_level=6)
                output_mime = "image/png"
            elif "webp" in target_mime:
                canvas.save(buf, format="WEBP", quality=85, method=4)
                output_mime = "image/webp"
            else:
                canvas.save(buf, format="JPEG", quality=85, optimize=False, progressive=False)
                output_mime = "image/jpeg"

            changed = (
                width != output_side
                or height != output_side
                or abs(scale - 1.0) > 0.02
            )
            if not changed:
                return image_b64, mime_type, False

            return base64.b64encode(buf.getvalue()).decode("utf-8"), output_mime, True

        except Exception as exc:
            logger.warning("Image framing normalisation skipped: %s", exc)
            return image_b64, mime_type, False

    def _background_is_pure_white(self, image_b64: str) -> tuple[bool, dict]:
        """Check border pixels to verify if the generated background is pure white."""
        if Image is None:
            return True, {"check_skipped": True, "reason": "Pillow unavailable"}

        try:
            image_bytes = base64.b64decode(image_b64)
            with Image.open(io.BytesIO(image_bytes)) as img:
                rgb = img.convert("RGB")
                width, height = rgb.size
                pixels = rgb.load()

            strip = max(2, int(min(width, height) * PURE_WHITE_BG_BORDER_RATIO))
            white_count = 0
            total_count = 0

            def is_white(px: tuple[int, int, int]) -> bool:
                return (
                    px[0] >= PURE_WHITE_BG_MIN_CHANNEL
                    and px[1] >= PURE_WHITE_BG_MIN_CHANNEL
                    and px[2] >= PURE_WHITE_BG_MIN_CHANNEL
                )

            for y in range(strip):
                for x in range(width):
                    total_count += 1
                    if is_white(pixels[x, y]):
                        white_count += 1

            for y in range(height - strip, height):
                for x in range(width):
                    total_count += 1
                    if is_white(pixels[x, y]):
                        white_count += 1

            for y in range(strip, height - strip):
                for x in range(strip):
                    total_count += 1
                    if is_white(pixels[x, y]):
                        white_count += 1
                for x in range(width - strip, width):
                    total_count += 1
                    if is_white(pixels[x, y]):
                        white_count += 1

            ratio = white_count / total_count if total_count else 0.0
            return ratio >= PURE_WHITE_BG_MIN_RATIO, {
                "white_ratio": round(ratio, 4),
                "threshold": PURE_WHITE_BG_MIN_RATIO,
                "min_channel": PURE_WHITE_BG_MIN_CHANNEL,
                "strip_px": strip,
                "image_size": f"{width}x{height}",
            }

        except Exception as exc:
            logger.warning("White background check failed: %s", exc)
            return True, {"check_skipped": True, "reason": "check_error"}
