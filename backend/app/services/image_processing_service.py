"""
Image Processing Service — Gemini Imagen Integration.

Uses Google Gemini for AI-powered product photo enhancement.
Each image is processed in a SEPARATE API call (isolated context).
Category-specific prompts for different product types.
Admin can reject results and add custom prompts for re-processing.
"""

import base64
import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("image_processing")
settings = get_settings()

GEMINI_API_KEY = settings.GEMINI_API_KEY.strip()
GEMINI_MODEL = (settings.GEMINI_IMAGE_MODEL or "gemini-3-pro-image-preview").strip()


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
        "Place the cake centered with balanced studio lighting and NO shadow on the background or under the cake. "
        "Do NOT add any cake stand, pedestal, plate, props, table textures, or decorative scene elements. "
        "A thin flat cake board under the cake is allowed, but no raised stand. "
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

    async def list_images(
        self,
        product_id: uuid.UUID | None = None,
        custom_cake_id: uuid.UUID | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """List images with optional filters."""
        from app.models.ml import ProcessedImage

        query = select(ProcessedImage).order_by(desc(ProcessedImage.created_at))
        if product_id:
            query = query.where(ProcessedImage.product_id == product_id)
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

        try:
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
                    "temperature": 0.2,
                },
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    params={"key": GEMINI_API_KEY},
                    json=payload,
                    timeout=120.0,  # Image processing can take time
                )
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
            logger.error("Gemini API error (%d): %s", e.response.status_code, error_body)
            return None, f"Gemini API error ({e.response.status_code}): {error_body}"
        except Exception as e:
            logger.error("Gemini API call failed: %s", str(e))
            return None, f"Gemini API call failed: {str(e)}"
