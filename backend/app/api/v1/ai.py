"""
AI assistant endpoints — Phase 9.
Natural-language product Q&A with RAG.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.user import User
from app.services.ai_service import AIService
from app.services.cache_service import RateLimiter

router = APIRouter(prefix="/ai", tags=["AI Assistant"])
logger = get_logger("ai_routes")


# ── Schemas ──────────────────────────────────────────────────────────────────
class AIQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)


class AIQueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    response_time_ms: int


class IndexProductRequest(BaseModel):
    product_id: uuid.UUID


# ── Endpoints ────────────────────────────────────────────────────────────────
@router.post("/ask", response_model=AIQueryResponse)
async def ask_question(
    data: AIQueryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Ask a natural-language question about products.
    Uses RAG to retrieve relevant products and generate an answer.
    Rate limited to 10 requests/min per IP.
    """
    # Rate limit
    ip = request.client.host if request.client else "unknown"
    allowed, remaining = await RateLimiter.check_ai_endpoint(ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many AI queries. Please wait a moment.",
        )

    service = AIService(db)

    # Extract user ID if authenticated
    user_id = None
    try:
        from app.api.deps import bearer_scheme
        from app.core.security import decode_token
        creds = await bearer_scheme(request)
        if creds:
            payload = decode_token(creds.credentials)
            if payload:
                user_id = payload.get("sub")
    except Exception:
        pass

    result = await service.query(data.question, user_id=user_id)
    return result


@router.post("/index-product")
async def index_product(
    data: IndexProductRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Index a product for AI search."""
    from app.services.product_service import ProductService

    product_service = ProductService(db)
    product = await product_service.get_product(data.product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    ai_service = AIService(db)
    await ai_service.index_product(product)

    return {"message": f"Product '{product.name}' indexed for AI search"}


@router.post("/index-all")
async def index_all_products(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Index all active products for AI search."""
    from app.services.product_service import ProductService

    product_service = ProductService(db)
    products = await product_service.list_products(is_active=True, limit=500)

    ai_service = AIService(db)
    count = 0
    for product in products:
        await ai_service.index_product(product)
        count += 1

    return {"message": f"{count} products indexed for AI search"}
