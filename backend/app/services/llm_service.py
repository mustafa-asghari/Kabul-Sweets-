"""
LLM Description Service — Phase ML-3.
Auto-generates marketing descriptions, short descriptions, and SEO meta.
"""

import os

from app.core.logging import get_logger

logger = get_logger("llm_service")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")


class DescriptionService:
    """Generates marketing descriptions for cakes and products."""

    TONE_MAP = {
        "luxury": "elegant, sophisticated, premium language with sensory descriptions",
        "fun": "playful, joyful, and approachable language with emoji where appropriate",
        "elegant": "refined, classic, and graceful descriptions",
        "traditional": "warm, authentic, emphasizing heritage and tradition",
    }

    async def generate_descriptions(
        self,
        flavor: str,
        ingredients: list[str] | None = None,
        decoration_style: str | None = None,
        event_type: str | None = None,
        size_info: str | None = None,
        tone: str = "luxury",
    ) -> dict:
        """
        Generate three descriptions:
        - short (1-2 sentences, for cards)
        - long (2-3 paragraphs, for product page)
        - seo (meta description, 155 chars max)
        """
        if not OPENAI_API_KEY:
            return self._generate_fallback(flavor, ingredients, decoration_style, event_type)

        try:
            import httpx

            tone_instruction = self.TONE_MAP.get(tone, self.TONE_MAP["luxury"])

            prompt = f"""Generate three marketing descriptions for an Afghan bakery cake/product.

PRODUCT DETAILS:
- Flavor: {flavor}
- Ingredients: {', '.join(ingredients) if ingredients else 'Traditional Afghan recipe'}
- Decoration: {decoration_style or 'Classic Afghan style'}
- Event Type: {event_type or 'Any occasion'}
- Size: {size_info or 'Various sizes available'}

TONE: {tone_instruction}

BRAND: Kabul Sweets — an authentic Afghan bakery in Australia

Respond ONLY in this exact JSON format (no markdown, no code blocks):
{{"short": "One to two sentence description for product cards.", "long": "Two to three paragraph marketing description for the product page. Include sensory details about taste, texture, and the experience.", "seo": "Meta description under 155 characters for search engines."}}"""

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": AI_MODEL,
                        "messages": [
                            {"role": "system", "content": "You are a premium bakery marketing copywriter. Respond only with valid JSON."},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.7,
                        "max_tokens": 500,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                text = data["choices"][0]["message"]["content"]

                import json
                result = json.loads(text)
                return {
                    "short": result.get("short", ""),
                    "long": result.get("long", ""),
                    "seo": result.get("seo", "")[:155],
                    "generated_by": "ai",
                    "model": AI_MODEL,
                }

        except Exception as e:
            logger.error("LLM description generation failed: %s", str(e))
            return self._generate_fallback(flavor, ingredients, decoration_style, event_type)

    def _generate_fallback(
        self,
        flavor: str,
        ingredients: list[str] | None,
        decoration_style: str | None,
        event_type: str | None,
    ) -> dict:
        """Generate template-based descriptions when LLM is unavailable."""
        ingredients_text = f"crafted with {', '.join(ingredients)}" if ingredients else "made with traditional Afghan ingredients"

        short = f"A beautiful {flavor} creation from Kabul Sweets, {ingredients_text}."

        deco = f" Decorated in {decoration_style} style." if decoration_style else ""
        event = f" Perfect for {event_type} celebrations." if event_type else " Perfect for any special occasion."

        long = (
            f"Indulge in the exquisite flavors of our {flavor}, "
            f"{ingredients_text}. Each piece is handcrafted by our skilled bakers "
            f"using authentic Afghan recipes passed down through generations.\n\n"
            f"{deco}{event}\n\n"
            f"At Kabul Sweets, we believe every celebration deserves a centerpiece "
            f"that tells a story — one of tradition, craftsmanship, and love."
        )

        seo = f"{flavor} from Kabul Sweets — authentic Afghan bakery. {ingredients_text}. Order for pickup today."
        seo = seo[:155]

        return {
            "short": short,
            "long": long,
            "seo": seo,
            "generated_by": "template",
            "model": None,
        }
