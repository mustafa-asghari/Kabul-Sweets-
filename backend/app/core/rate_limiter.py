"""
Rate limiter middleware using Redis.
Implements sliding window rate limiting.
"""

from fastapi import HTTPException, Request, status

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.redis import get_redis

logger = get_logger("rate_limiter")
settings = get_settings()


async def check_rate_limit(
    request: Request,
    limit: int | None = None,
    window: int = 60,
) -> None:
    """
    Check rate limit for the request IP.
    Raises HTTP 429 if limit exceeded.
    """
    if limit is None:
        limit = settings.RATE_LIMIT_PER_MINUTE

    try:
        redis = await get_redis()
        client_ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{client_ip}:{request.url.path}"

        current = await redis.get(key)
        if current is not None and int(current) >= limit:
            logger.warning("Rate limit exceeded for %s on %s", client_ip, request.url.path)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        await pipe.execute()
    except HTTPException:
        raise
    except Exception as e:
        # If Redis is down, allow the request through but log it
        logger.error("Rate limiter error (allowing request): %s", str(e))
