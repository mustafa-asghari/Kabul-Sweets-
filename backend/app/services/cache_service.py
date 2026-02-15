"""
Caching service — Phase 10.
Redis-based caching for products, homepage data, and query results.
"""

import json
import hashlib
from functools import wraps
from typing import Any

from app.core.logging import get_logger
from app.core.redis import get_redis

logger = get_logger("cache_service")

# Cache TTLs (seconds)
CACHE_TTL = {
    "product_list": 300,       # 5 min
    "product_detail": 600,     # 10 min
    "homepage_featured": 300,  # 5 min
    "homepage_popular": 300,   # 5 min
    "category_products": 300,  # 5 min
    "ai_query": 3600,          # 1 hour
    "dashboard": 60,           # 1 min
}


class CacheService:
    """Redis-based caching with automatic invalidation."""

    @staticmethod
    def _make_key(prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from prefix and arguments."""
        parts = [str(a) for a in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
        raw = ":".join([prefix] + parts)
        return f"ks:cache:{raw}"

    @staticmethod
    async def get(key: str) -> Any | None:
        """Get a cached value."""
        redis = await get_redis()
        if not redis:
            return None
        try:
            data = await redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning("Cache get failed for %s: %s", key, str(e))
            return None

    @staticmethod
    async def set(key: str, value: Any, ttl: int = 300) -> bool:
        """Set a cached value with TTL."""
        redis = await get_redis()
        if not redis:
            return False
        try:
            await redis.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.warning("Cache set failed for %s: %s", key, str(e))
            return False

    @staticmethod
    async def delete(key: str) -> bool:
        """Delete a cached value."""
        redis = await get_redis()
        if not redis:
            return False
        try:
            await redis.delete(key)
            return True
        except Exception as e:
            logger.warning("Cache delete failed for %s: %s", key, str(e))
            return False

    @staticmethod
    async def delete_pattern(pattern: str) -> int:
        """Delete all keys matching a pattern."""
        redis = await get_redis()
        if not redis:
            return 0
        try:
            keys = []
            async for key in redis.scan_iter(match=f"ks:cache:{pattern}*"):
                keys.append(key)
            if keys:
                await redis.delete(*keys)
            logger.info("Invalidated %d cache keys matching: %s", len(keys), pattern)
            return len(keys)
        except Exception as e:
            logger.warning("Cache pattern delete failed: %s", str(e))
            return 0

    # ── Convenience Methods ──────────────────────────────────────────────
    @classmethod
    async def get_or_set(cls, key: str, factory, ttl: int = 300):
        """Get from cache or compute and cache the result."""
        cached = await cls.get(key)
        if cached is not None:
            return cached

        result = await factory()
        await cls.set(key, result, ttl)
        return result

    # ── Product-specific ─────────────────────────────────────────────────
    @classmethod
    async def invalidate_product(cls, product_id: str = None):
        """Invalidate all product-related caches."""
        await cls.delete_pattern("product")
        await cls.delete_pattern("homepage")
        await cls.delete_pattern("category")
        if product_id:
            await cls.delete(cls._make_key("product_detail", product_id))
        logger.info("Product caches invalidated")

    @classmethod
    async def invalidate_order(cls):
        """Invalidate order-related caches (dashboard, analytics)."""
        await cls.delete_pattern("dashboard")
        await cls.delete_pattern("analytics")
        logger.info("Order caches invalidated")


# ── Rate Limiter (enhanced from Phase 2) ─────────────────────────────────────
class RateLimiter:
    """Token bucket rate limiter for public endpoints."""

    @staticmethod
    async def check(
        key: str,
        limit: int = 60,
        window: int = 60,
    ) -> tuple[bool, int]:
        """
        Check rate limit. Returns (allowed, remaining).
        """
        redis = await get_redis()
        if not redis:
            return True, limit  # Allow if Redis unavailable

        full_key = f"ks:ratelimit:{key}"
        try:
            current = await redis.incr(full_key)
            if current == 1:
                await redis.expire(full_key, window)

            remaining = max(0, limit - current)
            return current <= limit, remaining
        except Exception:
            return True, limit

    @staticmethod
    async def check_ai_endpoint(ip: str) -> tuple[bool, int]:
        """Rate limit for AI queries — stricter (10/min)."""
        return await RateLimiter.check(f"ai:{ip}", limit=10, window=60)
