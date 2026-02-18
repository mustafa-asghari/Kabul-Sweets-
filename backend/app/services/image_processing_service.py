"""
Image Processing Service — Gemini Imagen Integration.

Uses Google Gemini for AI-powered product photo enhancement.
Each image is processed in a SEPARATE API call (isolated context).
Category-specific prompts for different product types.
Admin can reject results and add custom prompts for re-processing.
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
GEMINI_MODEL = (settings.GEMINI_IMAGE_MODEL or "gemini-3-pro-image-preview").strip()

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional fallback
    Image = None

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
    """

    def __init__(self, db: AsyncSession):
        self.db = db

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
        Save an uploaded image to the database.
        Does NOT process it yet — that happens in a separate call.
        """
        from app.models.ml import ProcessedImage

        # Encode image as base64 for storage
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        image = ProcessedImage(
            product_id=product_id,
            custom_cake_id=custom_cake_id,
            original_url=f"data:{content_type};base64,{image_b64}",
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

        logger.info("Image uploaded: %s (%d bytes)", filename, len(image_data))

        return {
            "image_id": str(image.id),
            "filename": filename,
            "size_bytes": len(image_data),
            "status": "uploaded",
            "message": "Image saved. Use /process endpoint to enhance it.",
        }

    async def process_image(
        self,
        image_id: uuid.UUID,
        category: ImageCategory,
        custom_prompt: str | None = None,
    ) -> dict:
        """
        Process a SINGLE image with Gemini.
        Each call is completely isolated — no shared context window.

        Args:
            image_id: The saved image to process
            category: Product category (determines the base prompt)
            custom_prompt: Optional admin override/addition to the prompt
        """
        from app.models.ml import ProcessedImage

        # Fetch the image from DB
        result = await self.db.execute(
            select(ProcessedImage).where(ProcessedImage.id == image_id)
        )
        image = result.scalar_one_or_none()
        if not image:
            return {"error": "Image not found"}

        if not image.original_url:
            return {"error": "No original image data found"}

        # Mark as processing
        image.processing_status = "processing"
        await self.db.flush()

        # Build the prompt
        base_prompt = CATEGORY_PROMPTS.get(category, CATEGORY_PROMPTS[ImageCategory.CAKE])

        if custom_prompt:
            # Admin added a custom prompt on top
            full_prompt = f"{base_prompt}\n\nADDITIONAL INSTRUCTIONS:\n{custom_prompt}"
        else:
            full_prompt = base_prompt

        # Store which prompt was used
        image.prompt_used = full_prompt
        image.category_used = category.value

        try:
            # Extract base64 data from the data URL
            if image.original_url.startswith("data:"):
                # Format: data:image/jpeg;base64,/9j/4AAQ...
                b64_data = image.original_url.split(",", 1)[1]
                mime_type = image.original_url.split(";")[0].split(":")[1]
            else:
                return {"error": "Unsupported image format"}

            # Call Gemini API — SEPARATE CONTEXT for each image
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

            # Normalize subject framing so published cards stay visually consistent.
            processed_b64, mime_type, framing_changed = self._normalize_image_framing(
                processed_b64,
                mime_type,
            )

            # Store processed result
            image.processed_url = f"data:{mime_type};base64,{processed_b64}"
            image.processed_size_bytes = len(base64.b64decode(processed_b64))
            image.processing_status = "completed"
            image.error_message = None
            image.processing_attempts = (image.processing_attempts or 0) + 1
            await self.db.flush()

            logger.info(
                "Image processed: %s (%s → %s bytes)",
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
                "white_background_retries": 0,
                "framing_normalized": framing_changed,
            }

        except Exception as e:
            image.processing_status = "failed"
            image.error_message = str(e)
            image.processing_attempts = (image.processing_attempts or 0) + 1
            await self.db.flush()
            logger.error("Image processing failed for %s: %s", image_id, str(e))
            return {"error": str(e), "image_id": str(image_id)}

    async def reject_and_reprocess(
        self,
        image_id: uuid.UUID,
        custom_prompt: str,
        category: ImageCategory | None = None,
    ) -> dict:
        """
        Admin rejects the processed image and re-processes with a custom prompt.
        The custom prompt is ADDED ON TOP of the base category prompt.
        Creates a fresh Gemini API call (new context).
        """
        from app.models.ml import ProcessedImage

        result = await self.db.execute(
            select(ProcessedImage).where(ProcessedImage.id == image_id)
        )
        image = result.scalar_one_or_none()
        if not image:
            return {"error": "Image not found"}

        # Use existing category or provided one
        cat = category or ImageCategory(image.category_used or "cake")

        # Mark as re-processing
        image.processing_status = "reprocessing"
        image.admin_chosen = None  # Reset admin choice
        image.rejection_reason = custom_prompt
        await self.db.flush()

        logger.info("Re-processing image %s with custom prompt", image_id)

        # Re-process with custom prompt on top
        return await self.process_image(
            image_id=image_id,
            category=cat,
            custom_prompt=custom_prompt,
        )

    async def admin_choose_image(
        self,
        image_id: uuid.UUID,
        choice: str,  # "original" or "processed"
    ) -> dict:
        """Admin chooses which version to use (original or processed)."""
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

    async def get_image(self, image_id: uuid.UUID) -> dict | None:
        """Get image details and data."""
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
        """Delete an uploaded/processed image record."""
        from app.models.ml import ProcessedImage

        result = await self.db.execute(
            select(ProcessedImage).where(ProcessedImage.id == image_id)
        )
        image = result.scalar_one_or_none()
        if not image:
            return False

        await self.db.delete(image)
        await self.db.flush()
        logger.info("Image deleted: %s", image_id)
        return True

    @staticmethod
    def resolve_selected_image_url(image) -> tuple[str | None, str]:
        """Return selected image data URL and selected source."""
        if image.admin_chosen == "processed" and image.processed_url:
            return image.processed_url, "processed"
        return image.original_url, "original"

    async def list_images(
        self,
        product_id: uuid.UUID | None = None,
        custom_cake_id: uuid.UUID | None = None,
        status: str | None = None,
        include_published: bool = False,
        limit: int = 50,
    ) -> list[dict]:
        """List images with optional filters."""
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

    async def _call_gemini(
        self,
        image_b64: str,
        mime_type: str,
        prompt: str,
    ) -> tuple[str | None, str | None]:
        """
        Call Google Gemini API with a SINGLE image.
        Each call is COMPLETELY ISOLATED — fresh context, no memory.

        Returns: (processed_image_b64, error_message)
        """
        if not GEMINI_API_KEY:
            logger.warning("Gemini API key not configured — returning mock result")
            return None, "Gemini API key not configured. Set GEMINI_API_KEY in .env"

        import httpx

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

        # Build request — each image is a SEPARATE, ISOLATED call
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": image_b64,
                            }
                        },
                        {
                            "text": prompt,
                        },
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["image", "text"],
                "temperature": 0.0,
            },
        }

        max_attempts = 3
        timeout = httpx.Timeout(120.0, connect=20.0)
        last_error: str | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout, http2=False) as client:
                    response = await client.post(
                        url,
                        params={"key": GEMINI_API_KEY},
                        json=payload,
                    )

                # Retry transient upstream statuses
                if response.status_code in (429, 500, 502, 503, 504):
                    error_body = response.text[:500] if response.text else "Unknown"
                    last_error = f"Gemini API error ({response.status_code}): {error_body}"
                    if attempt < max_attempts:
                        wait_seconds = 1.5 * (2 ** (attempt - 1))
                        logger.warning(
                            "Gemini transient HTTP %d (attempt %d/%d). Retrying in %.1fs",
                            response.status_code,
                            attempt,
                            max_attempts,
                            wait_seconds,
                        )
                        await asyncio.sleep(wait_seconds)
                        continue
                    logger.error("Gemini API error (%d): %s", response.status_code, error_body)
                    return None, last_error

                response.raise_for_status()
                data = response.json()

                # Extract the generated image from response
                candidates = data.get("candidates", [])
                if not candidates:
                    return None, "No response from Gemini"

                parts = candidates[0].get("content", {}).get("parts", [])

                # Find the image part in the response
                for part in parts:
                    if "inlineData" in part:
                        return part["inlineData"]["data"], None

                # If no image returned, check for text response
                for part in parts:
                    if "text" in part:
                        return None, f"Gemini returned text instead of image: {part['text'][:200]}"

                return None, "Gemini response contained no image data"

            except httpx.HTTPStatusError as e:
                error_body = e.response.text[:500] if e.response else "Unknown"
                last_error = f"Gemini API error ({e.response.status_code}): {error_body}"
                logger.error("Gemini API error (%d): %s", e.response.status_code, error_body)
                return None, last_error
            except (
                httpx.RemoteProtocolError,
                httpx.ReadError,
                httpx.ReadTimeout,
                httpx.ConnectError,
                httpx.WriteError,
            ) as e:
                last_error = f"Gemini API call failed: {str(e)}"
                if attempt < max_attempts:
                    wait_seconds = 1.5 * (2 ** (attempt - 1))
                    logger.warning(
                        "Gemini transport error on attempt %d/%d: %s. Retrying in %.1fs",
                        attempt,
                        max_attempts,
                        str(e),
                        wait_seconds,
                    )
                    await asyncio.sleep(wait_seconds)
                    continue
                logger.error("Gemini API call failed after %d attempts: %s", max_attempts, str(e))
                return None, last_error
            except Exception as e:
                last_error = f"Gemini API call failed: {str(e)}"
                logger.error("Gemini API call failed: %s", str(e))
                return None, last_error

        return None, last_error or "Gemini API call failed for unknown reason"

    @staticmethod
    def normalize_public_data_url(data_url: str) -> tuple[str, bool]:
        """
        Normalize a data URL image into a consistent product frame.
        Returns (possibly_updated_data_url, changed).
        """
        if not data_url.startswith("data:"):
            return data_url, False

        try:
            header, image_b64 = data_url.split(",", 1)
            mime_type = header.split(";")[0].split(":")[1]
        except Exception:
            return data_url, False

        normalized_b64, normalized_mime, changed = ImageProcessingService._normalize_image_framing(
            image_b64,
            mime_type,
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
        Enforce a pure-white background and place the subject onto a square frame
        with consistent "farther" occupancy for visual consistency across cards.
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

            pixels = rgb.load()
            total_pixels = width * height
            visited = bytearray(total_pixels)
            queue: deque[tuple[int, int]] = deque()

            def to_index(x: int, y: int) -> int:
                return y * width + x

            def is_seed_bg(px: tuple[int, int, int]) -> bool:
                value = max(px)
                chroma = max(px) - min(px)
                return (
                    (
                        px[0] >= BG_SEED_MIN_CHANNEL
                        and px[1] >= BG_SEED_MIN_CHANNEL
                        and px[2] >= BG_SEED_MIN_CHANNEL
                    )
                    or (
                        value >= BG_SEED_MIN_CHANNEL
                        and chroma <= BG_EXPAND_NEUTRAL_MAX_CHROMA
                    )
                )

            def is_expand_bg(px: tuple[int, int, int]) -> bool:
                value = max(px)
                chroma = max(px) - min(px)
                return (
                    (
                        px[0] >= BG_EXPAND_MIN_CHANNEL
                        and px[1] >= BG_EXPAND_MIN_CHANNEL
                        and px[2] >= BG_EXPAND_MIN_CHANNEL
                    )
                    or (
                        value >= BG_EXPAND_NEUTRAL_MIN_VALUE
                        and chroma <= BG_EXPAND_NEUTRAL_MAX_CHROMA
                    )
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

            background_count = 0
            while queue:
                x, y = queue.popleft()
                idx = to_index(x, y)
                if visited[idx]:
                    continue
                if not is_expand_bg(pixels[x, y]):
                    continue
                visited[idx] = 1
                background_count += 1

                if x > 0:
                    queue.append((x - 1, y))
                if x < width - 1:
                    queue.append((x + 1, y))
                if y > 0:
                    queue.append((x, y - 1))
                if y < height - 1:
                    queue.append((x, y + 1))

            def detect_subject_bounds(ignore_neutral_light: bool) -> tuple[int, int, int, int, int]:
                left = width
                top = height
                right = -1
                bottom = -1
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
                                or (
                                    value >= SUBJECT_IGNORE_NEUTRAL_MIN_VALUE
                                    and chroma <= SUBJECT_IGNORE_NEUTRAL_MAX_CHROMA
                                )
                            )
                        ):
                            continue

                        if (
                            r < SUBJECT_DETECT_MAX_CHANNEL
                            or g < SUBJECT_DETECT_MAX_CHANNEL
                            or b < SUBJECT_DETECT_MAX_CHANNEL
                        ):
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

            left, top, right, bottom, strict_subject_pixels = detect_subject_bounds(
                ignore_neutral_light=True
            )
            strict_area_ratio = strict_subject_pixels / total_pixels if total_pixels else 0.0
            strict_bbox_ratio = 0.0
            if right >= left and bottom >= top:
                strict_bbox_ratio = ((right - left + 1) * (bottom - top + 1)) / total_pixels

            if (
                strict_subject_pixels == 0
                or strict_area_ratio < SUBJECT_STRICT_MIN_AREA_RATIO
                or strict_bbox_ratio < SUBJECT_STRICT_MIN_BBOX_AREA_RATIO
            ):
                left, top, right, bottom, _ = detect_subject_bounds(ignore_neutral_light=False)

            if right < left or bottom < top:
                subject_crop = rgb
            else:
                margin = max(2, int(min(width, height) * FRAME_SUBJECT_MARGIN_RATIO))
                crop_left = max(0, left - margin)
                crop_top = max(0, top - margin)
                crop_right = min(width, right + margin + 1)
                crop_bottom = min(height, bottom + margin + 1)
                subject_crop = rgb.crop((crop_left, crop_top, crop_right, crop_bottom))

            crop_w, crop_h = subject_crop.size
            if crop_w < 2 or crop_h < 2:
                return image_b64, mime_type, False

            output_side = min(max(max(width, height), FRAME_MIN_OUTPUT_SIDE), FRAME_MAX_OUTPUT_SIDE)
            target_subject = max(1, int(output_side * FRAME_TARGET_OCCUPANCY))
            scale = min(target_subject / crop_w, target_subject / crop_h)
            resized_w = max(1, int(round(crop_w * scale)))
            resized_h = max(1, int(round(crop_h * scale)))

            resampling = getattr(Image, "Resampling", Image)
            resized = subject_crop.resize((resized_w, resized_h), resampling.LANCZOS)

            canvas = Image.new("RGB", (output_side, output_side), (255, 255, 255))
            paste_x = (output_side - resized_w) // 2
            paste_y = (output_side - resized_h) // 2
            canvas.paste(resized, (paste_x, paste_y))

            output_buffer = io.BytesIO()
            target_mime = mime_type.lower()
            if "png" in target_mime:
                canvas.save(output_buffer, format="PNG", optimize=True)
                output_mime = "image/png"
            elif "webp" in target_mime:
                canvas.save(output_buffer, format="WEBP", quality=95, method=6)
                output_mime = "image/webp"
            else:
                canvas.save(
                    output_buffer,
                    format="JPEG",
                    quality=95,
                    optimize=True,
                    progressive=True,
                )
                output_mime = "image/jpeg"

            changed = (
                width != output_side
                or height != output_side
                or abs(scale - 1.0) > 0.02
            )
            if not changed:
                return image_b64, mime_type, False

            normalized_b64 = base64.b64encode(output_buffer.getvalue()).decode("utf-8")
            return normalized_b64, output_mime, True
        except Exception as exc:
            logger.warning("Image framing normalization skipped: %s", str(exc))
            return image_b64, mime_type, False

    def _background_is_pure_white(self, image_b64: str) -> tuple[bool, dict]:
        """
        Check border pixels to verify if the generated background is pure white.
        Uses only border strips to avoid evaluating the cake itself.
        """
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

            # Top and bottom strips
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

            # Left and right strips (excluding already-counted corners)
            for y in range(strip, height - strip):
                for x in range(strip):
                    total_count += 1
                    if is_white(pixels[x, y]):
                        white_count += 1

                for x in range(width - strip, width):
                    total_count += 1
                    if is_white(pixels[x, y]):
                        white_count += 1

            ratio = (white_count / total_count) if total_count else 0.0
            metrics = {
                "white_ratio": round(ratio, 4),
                "threshold": PURE_WHITE_BG_MIN_RATIO,
                "min_channel": PURE_WHITE_BG_MIN_CHANNEL,
                "strip_px": strip,
                "image_size": f"{width}x{height}",
            }
            return ratio >= PURE_WHITE_BG_MIN_RATIO, metrics

        except Exception as exc:
            logger.warning("White background check failed: %s", str(exc))
            return True, {"check_skipped": True, "reason": "check_error"}
