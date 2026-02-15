"""
Redis connection manager.
Used for caching, rate limiting, and session management.
"""

import redis.asyncio as aioredis

from app.core.config import get_settings

settings = get_settings()

# ── Redis Client ─────────────────────────────────────────────────────────────
redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get or create Redis connection."""
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return redis_client


async def close_redis() -> None:
    """Close Redis connection on shutdown."""
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        redis_client = None
