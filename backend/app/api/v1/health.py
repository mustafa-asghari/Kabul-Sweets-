"""
Health check endpoints.
Verifies database and Redis connectivity.
"""

from fastapi import APIRouter

from app.core.database import engine
from app.core.logging import get_logger
from app.core.redis import get_redis

router = APIRouter(tags=["Health"])
logger = get_logger("health")


@router.get("/health")
async def health_check():
    """
    Basic health check.
    Returns system status including database and Redis connectivity.
    """
    health = {
        "status": "healthy",
        "service": "Kabul Sweets API",
        "database": "unknown",
        "redis": "unknown",
    }

    # Check database
    try:
        async with engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        health["database"] = "connected"
    except Exception as e:
        health["database"] = f"error: {str(e)}"
        health["status"] = "degraded"
        logger.error("Database health check failed: %s", str(e))

    # Check Redis
    try:
        redis = await get_redis()
        await redis.ping()
        health["redis"] = "connected"
    except Exception as e:
        health["redis"] = f"error: {str(e)}"
        health["status"] = "degraded"
        logger.error("Redis health check failed: %s", str(e))

    return health


@router.get("/ping")
async def ping():
    """Simple ping endpoint for load balancers."""
    return {"ping": "pong"}
