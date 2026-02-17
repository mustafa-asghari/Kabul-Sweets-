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
PURE_WHITE_BG_MAX_RETRIES = 2
STRICT_WHITE_BG_APPEND = (
    "CRITICAL OUTPUT REQUIREMENT: The background must be EXACT pure white (#FFFFFF) "
    "on every edge and corner. No gray, no gradient, no vignette, no backdrop tone "
    "shift, and no shadow on the background. If background purity is not met, regenerate "
    "before returning the image."
)
FRAME_BG_MIN_CHANNEL = 246
FRAME_BG_ROW_RATIO = 0.997
FRAME_BG_BORDER_MIN_RATIO = 0.9
FRAME_MAX_TRIM_RATIO = 0.22
FRAME_TARGET_OCCUPANCY = 0.84
FRAME_MAX_OUTPUT_SIDE = 1600


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
        "Remove the entire background and replace with a clean pure white background (#FFFFFF). "
        "The background must be a flat, uniform white from edge to edge with no gradients, no vignettes, and no gray tint. "
        "Place the cake centered with balanced studio lighting and NO shadow on the background, NO floor shadow, and NO reflection. "
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
        "Remove the entire background and replace with a clean pure white background (#FFFFFF). "
        "Arrange the sweets elegantly, centered with balanced studio lighting and soft realistic shadow underneath. "
        "Enhance the texture details — show the shimmer of sugar, the richness of nuts, the smooth fudge surface. "
        "Keep proportions, colours, and traditional plating accurate and realistic. "
        "Commercial food photography, ultra high resolution, sharp focus, premium confectionery advertisement style."
    ),

    ImageCategory.PASTRY: (
        "Transform this pastry into a professional e-commerce product photo. "
        "Remove the entire background and replace with a clean pure white background (#FFFFFF). "
        "Place the pastry centered with balanced studio lighting and soft realistic shadow underneath. "
        "Enhance the flaky layers, golden crispy texture, and powdered sugar details. "
        "Keep proportions, colours, and the delicate form accurate and realistic. "
        "Commercial food photography, ultra high resolution, sharp focus, artisan bakery advertisement style."
    ),

    ImageCategory.COOKIE: (
        "Transform these cookies/baklava into a professional e-commerce product photo. "
        "Remove the entire background and replace with a clean pure white background (#FFFFFF). "
        "Arrange the cookies/baklava in an appealing layout, centered with balanced studio lighting "
        "and soft realistic shadow underneath. "
        "Enhance the intricate patterns, golden baked surfaces, pistachio and walnut details. "
        "Keep proportions, colours, and traditional decorative patterns accurate and realistic. "
        "Commercial food photography, ultra high resolution, sharp focus, luxury bakery advertisement style."
    ),

    ImageCategory.BREAD: (
        "Transform this bread into a professional e-commerce product photo. "
        "Remove the entire background and replace with a clean pure white background (#FFFFFF). "
        "Place the bread centered with balanced studio lighting and soft realistic shadow underneath. "
        "Enhance the crust texture, golden-brown colour, and stuffing details if visible. "
        "Keep proportions, colours, and artisan qualities accurate and realistic. "
        "Commercial food photography, ultra high resolution, sharp focus, artisan bread advertisement style."
    ),

    ImageCategory.DRINK: (
        "Transform this beverage/tea into a professional e-commerce product photo. "
        "Remove the entire background and replace with a clean pure white background (#FFFFFF). "
        "Place the product centered with balanced studio lighting and soft realistic shadow underneath. "
        "Enhance the packaging details, label text clarity, and overall presentation. "
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

            # Enforce pure-white background for cake photos.
            # If output is not white enough on borders, retry with stricter prompt.
            white_bg_retries = 0
            if category == ImageCategory.CAKE:
                while True:
                    is_white, metrics = self._background_is_pure_white(processed_b64)
                    if is_white:
                        break

                    if white_bg_retries >= PURE_WHITE_BG_MAX_RETRIES:
                        image.processing_status = "failed"
                        image.error_message = (
                            "Generated image background was not pure white after retries. "
                            "Please reprocess with a stricter custom prompt."
                        )
                        await self.db.flush()
                        return {
                            "error": image.error_message,
                            "image_id": str(image_id),
                            "background_metrics": metrics,
                        }

                    white_bg_retries += 1
                    strict_prompt = f"{full_prompt}\n\n{STRICT_WHITE_BG_APPEND}"
                    retry_b64, retry_error = await self._call_gemini(
                        image_b64=b64_data,
                        mime_type=mime_type,
                        prompt=strict_prompt,
                    )
                    if retry_error or not retry_b64:
                        image.processing_status = "failed"
                        image.error_message = retry_error or "Retry failed"
                        await self.db.flush()
                        return {"error": image.error_message, "image_id": str(image_id)}

                    processed_b64 = retry_b64
                    image.prompt_used = strict_prompt

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
                "white_background_retries": (
                    white_bg_retries if category == ImageCategory.CAKE else 0
                ),
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
        Trim excessive near-white borders and place the subject onto a square frame
        with consistent occupancy. Keeps originals unchanged when normalization is unsafe.
        """
        if Image is None:
            return image_b64, mime_type, False

        try:
            image_bytes = base64.b64decode(image_b64)
            with Image.open(io.BytesIO(image_bytes)) as img:
                rgba = img.convert("RGBA")

            white_bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            white_bg.paste(rgba, mask=rgba)
            rgb = white_bg.convert("RGB")

            width, height = rgb.size
            if width < 16 or height < 16:
                return image_b64, mime_type, False

            pixels = rgb.load()

            def is_bg(px: tuple[int, int, int]) -> bool:
                return (
                    px[0] >= FRAME_BG_MIN_CHANNEL
                    and px[1] >= FRAME_BG_MIN_CHANNEL
                    and px[2] >= FRAME_BG_MIN_CHANNEL
                )

            def row_bg_ratio(y: int) -> float:
                bg = 0
                for x in range(width):
                    if is_bg(pixels[x, y]):
                        bg += 1
                return bg / width

            def col_bg_ratio(x: int) -> float:
                bg = 0
                for y in range(height):
                    if is_bg(pixels[x, y]):
                        bg += 1
                return bg / height

            border_strip = max(2, int(min(width, height) * 0.05))
            border_bg = 0
            border_total = 0
            for y in range(border_strip):
                for x in range(width):
                    border_total += 1
                    if is_bg(pixels[x, y]):
                        border_bg += 1
            for y in range(height - border_strip, height):
                for x in range(width):
                    border_total += 1
                    if is_bg(pixels[x, y]):
                        border_bg += 1
            for y in range(border_strip, height - border_strip):
                for x in range(border_strip):
                    border_total += 1
                    if is_bg(pixels[x, y]):
                        border_bg += 1
                for x in range(width - border_strip, width):
                    border_total += 1
                    if is_bg(pixels[x, y]):
                        border_bg += 1

            if border_total == 0 or (border_bg / border_total) < FRAME_BG_BORDER_MIN_RATIO:
                return image_b64, mime_type, False

            top = 0
            while top < height and row_bg_ratio(top) >= FRAME_BG_ROW_RATIO:
                top += 1

            bottom = height - 1
            while bottom >= 0 and row_bg_ratio(bottom) >= FRAME_BG_ROW_RATIO:
                bottom -= 1

            left = 0
            while left < width and col_bg_ratio(left) >= FRAME_BG_ROW_RATIO:
                left += 1

            right = width - 1
            while right >= 0 and col_bg_ratio(right) >= FRAME_BG_ROW_RATIO:
                right -= 1

            if top >= bottom or left >= right:
                return image_b64, mime_type, False

            max_trim_x = int(width * FRAME_MAX_TRIM_RATIO)
            max_trim_y = int(height * FRAME_MAX_TRIM_RATIO)

            trim_top = min(top, max_trim_y)
            trim_bottom = min(height - 1 - bottom, max_trim_y)
            trim_left = min(left, max_trim_x)
            trim_right = min(width - 1 - right, max_trim_x)

            crop_left = trim_left
            crop_top = trim_top
            crop_right = width - trim_right
            crop_bottom = height - trim_bottom

            if crop_right <= crop_left or crop_bottom <= crop_top:
                return image_b64, mime_type, False

            cropped = rgb.crop((crop_left, crop_top, crop_right, crop_bottom))
            crop_w, crop_h = cropped.size
            if crop_w < 2 or crop_h < 2:
                return image_b64, mime_type, False

            output_side = min(max(width, height), FRAME_MAX_OUTPUT_SIDE)
            target_subject = max(1, int(output_side * FRAME_TARGET_OCCUPANCY))
            scale = min(target_subject / crop_w, target_subject / crop_h)
            resized_w = max(1, int(round(crop_w * scale)))
            resized_h = max(1, int(round(crop_h * scale)))

            resampling = getattr(Image, "Resampling", Image)
            resized = cropped.resize((resized_w, resized_h), resampling.LANCZOS)

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
                trim_top > 0
                or trim_bottom > 0
                or trim_left > 0
                or trim_right > 0
                or width != height
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
