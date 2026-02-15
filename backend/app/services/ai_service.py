"""
AI + RAG service — Phase 9.
Embedding generation, vector search, and intelligent product Q&A.
Uses OpenAI embeddings + PostgreSQL pgvector (or in-memory fallback).
"""

import json
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.logging import get_logger

logger = get_logger("ai_service")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


# ── Models ───────────────────────────────────────────────────────────────────
class ProductEmbedding(Base):
    """Stores product embeddings for vector similarity search."""

    __tablename__ = "product_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    content_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "product", "faq", "category"
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_json: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON array of floats (fallback when pgvector unavailable)
    metadata_extra: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    model_version: Mapped[str] = mapped_column(String(50), default=EMBEDDING_MODEL)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<ProductEmbedding {self.content_type}: {self.content_text[:50]}>"


class AIQueryLog(Base):
    """Logs all AI queries for analytics and improvement."""

    __tablename__ = "ai_query_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    context_used: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    model_used: Mapped[str] = mapped_column(String(50), default=AI_MODEL)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5 user rating

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        nullable=False, index=True,
    )

    def __repr__(self) -> str:
        return f"<AIQueryLog '{self.query[:50]}'>"


# ── AI Service ───────────────────────────────────────────────────────────────
class AIService:
    """Handles AI-powered product Q&A with RAG pipeline."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding vector for text using OpenAI."""
        if not OPENAI_API_KEY:
            logger.warning("OpenAI API key not configured — using keyword search fallback")
            return None

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": EMBEDDING_MODEL,
                        "input": text,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
        except Exception as e:
            logger.error("Embedding generation failed: %s", str(e))
            return None

    async def index_product(self, product) -> bool:
        """Create/update embedding for a product."""
        # Build rich text representation
        content = self._build_product_text(product)
        embedding = await self.generate_embedding(content)

        # Check if existing embedding
        result = await self.db.execute(
            select(ProductEmbedding).where(
                ProductEmbedding.product_id == product.id,
                ProductEmbedding.content_type == "product",
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.content_text = content
            existing.embedding_json = json.dumps(embedding) if embedding else None
        else:
            emb = ProductEmbedding(
                product_id=product.id,
                content_type="product",
                content_text=content,
                embedding_json=json.dumps(embedding) if embedding else None,
                metadata_extra={
                    "name": product.name,
                    "category": product.category.value if hasattr(product.category, 'value') else str(product.category),
                    "price": str(product.base_price),
                },
            )
            self.db.add(emb)

        await self.db.flush()
        logger.info("Indexed product: %s", product.name)
        return True

    async def query(
        self,
        question: str,
        user_id: uuid.UUID | None = None,
    ) -> dict:
        """
        Answer a product question using RAG pipeline.
        1. Find relevant products via similarity search
        2. Build context from matches
        3. Generate answer using LLM
        """
        import time
        start = time.time()

        # Step 1: Retrieve relevant context
        context_docs = await self._retrieve_context(question)

        # Step 2: Generate answer
        answer, tokens = await self._generate_answer(question, context_docs)

        elapsed_ms = int((time.time() - start) * 1000)

        # Step 3: Log query
        log = AIQueryLog(
            user_id=user_id,
            query=question,
            response=answer,
            context_used={"documents": [d["name"] for d in context_docs]},
            tokens_used=tokens,
            response_time_ms=elapsed_ms,
        )
        self.db.add(log)
        await self.db.flush()

        return {
            "answer": answer,
            "sources": context_docs,
            "response_time_ms": elapsed_ms,
        }

    async def _retrieve_context(self, question: str, limit: int = 5) -> list[dict]:
        """Retrieve relevant product context using keyword or vector search."""
        # Try vector search first
        query_embedding = await self.generate_embedding(question)

        if query_embedding:
            # Vector similarity search (cosine distance in Python)
            results = await self.db.execute(
                select(ProductEmbedding).where(
                    ProductEmbedding.embedding_json.isnot(None)
                )
            )
            embeddings = results.scalars().all()

            scored = []
            for emb in embeddings:
                stored = json.loads(emb.embedding_json)
                score = self._cosine_similarity(query_embedding, stored)
                scored.append((score, emb))

            scored.sort(key=lambda x: x[0], reverse=True)
            top = scored[:limit]

            return [
                {
                    "name": emb.metadata_extra.get("name", ""),
                    "content": emb.content_text[:500],
                    "score": round(score, 4),
                    "category": emb.metadata_extra.get("category", ""),
                    "price": emb.metadata_extra.get("price", ""),
                }
                for score, emb in top
            ]
        else:
            # Fallback: keyword search
            from app.models.product import Product

            keywords = question.lower().split()
            results = await self.db.execute(
                select(Product).where(Product.is_active == True).limit(20)
            )
            products = results.scalars().all()

            scored = []
            for p in products:
                text = f"{p.name} {p.description or ''} {' '.join(p.tags or [])}".lower()
                score = sum(1 for kw in keywords if kw in text)
                if score > 0:
                    scored.append((score, p))

            scored.sort(key=lambda x: x[0], reverse=True)

            return [
                {
                    "name": p.name,
                    "content": self._build_product_text(p)[:500],
                    "score": float(score),
                    "category": p.category.value if hasattr(p.category, 'value') else str(p.category),
                    "price": str(p.base_price),
                }
                for score, p in scored[:limit]
            ]

    async def _generate_answer(
        self,
        question: str,
        context: list[dict],
    ) -> tuple[str, int | None]:
        """Generate answer using LLM with strict prompt."""
        if not OPENAI_API_KEY:
            # Fallback: construct answer from context without LLM
            if not context:
                return "I couldn't find any matching products. Please try rephrasing your question or browse our menu!", None

            answer_parts = ["Based on our menu, here's what I found:\n"]
            for doc in context:
                answer_parts.append(f"**{doc['name']}** (${doc['price']})")
                answer_parts.append(f"  {doc['content'][:200]}\n")
            return "\n".join(answer_parts), None

        try:
            import httpx

            # Build strict prompt
            context_text = "\n\n".join(
                f"Product: {d['name']} (${d['price']}, Category: {d['category']})\n{d['content']}"
                for d in context
            )

            system_prompt = """You are the Kabul Sweets AI assistant. You help customers find the right bakery products.

RULES:
1. ONLY answer based on the product information provided below
2. NEVER make up products, prices, or ingredients that aren't in the context
3. If you don't have enough information, say so honestly
4. Be warm, friendly, and helpful
5. Suggest relevant products from the context
6. Include prices when mentioning products
7. Keep responses concise (2-3 paragraphs max)

PRODUCT INFORMATION:
"""

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
                            {"role": "system", "content": system_prompt + context_text},
                            {"role": "user", "content": question},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 500,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                answer = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens")
                return answer, tokens

        except Exception as e:
            logger.error("LLM generation failed: %s", str(e))
            # Fallback
            if context:
                parts = ["Here are some products that might help:\n"]
                for d in context:
                    parts.append(f"• **{d['name']}** — ${d['price']}")
                return "\n".join(parts), None
            return "I'm having trouble right now. Please try again or browse our menu directly!", None

    def _build_product_text(self, product) -> str:
        """Build rich text representation for embedding."""
        variants_text = ""
        if hasattr(product, 'variants') and product.variants:
            variants_text = "Sizes/Options: " + ", ".join(
                f"{v.name} (${v.price})" for v in product.variants
            )

        return (
            f"Product: {product.name}\n"
            f"Category: {product.category.value if hasattr(product.category, 'value') else product.category}\n"
            f"Price: ${product.base_price}\n"
            f"Description: {product.description or 'N/A'}\n"
            f"{variants_text}\n"
            f"Tags: {', '.join(product.tags or [])}\n"
            f"{'This is a cake product. Custom messages can be added.' if product.is_cake else ''}"
        )

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        import math
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
