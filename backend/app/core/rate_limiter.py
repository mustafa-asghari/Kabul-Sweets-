"""
Rate limiter — sliding-window, Redis-backed.

Per-user rate limiting for authenticated requests (keyed on user UUID).
Per-IP fallback for anonymous requests.

Usage in route handlers
-----------------------
    # Per-user (authenticated):
    await check_rate_limit(request, limit=20, window=60, user_id=str(admin.id))

    # Per-IP (anonymous / login endpoint):
    await check_rate_limit(request, limit=10, window=60)
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
    user_id: str | None = None,
) -> None:
    """
    Sliding-window rate limiter backed by Redis.

    Parameters
    ----------
    request  : the FastAPI Request object (used for IP fallback and path)
    limit    : max requests in `window` seconds (defaults to RATE_LIMIT_PER_MINUTE)
    window   : time window in seconds (default 60)
    user_id  : authenticated user UUID string; when present, limits are
               applied per-user rather than per-IP, preventing shared-IP abuse.

    Raises HTTP 429 when the limit is exceeded.
    """
    if limit is None:
        limit = settings.RATE_LIMIT_PER_MINUTE

    # Prefer user-scoped keys so one user can't exhaust another's quota
    if user_id:
        identity = f"user:{user_id}"
    else:
        client_ip = (request.client.host if request.client else "unknown")
        identity = f"ip:{client_ip}"

    # Normalise path to strip trailing slashes for consistent keys
    path = request.url.path.rstrip("/") or "/"
    key = f"rl:{identity}:{path}"

    try:
        redis = await get_redis()

        current = await redis.get(key)
        if current is not None and int(current) >= limit:
            logger.warning(
                "Rate limit hit: %s on %s (%s req/%ds)",
                identity, path, limit, window,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down and try again.",
                headers={"Retry-After": str(window)},
            )

        # Atomic increment + set expiry in a pipeline
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        await pipe.execute()

    except HTTPException:
        raise
    except Exception as exc:
        # Redis outage → fail open (allow the request) but log it
        logger.error("Rate limiter Redis error (allowing request through): %s", exc)


# ── Convenience wrappers — call these directly inside route handlers ──────────

async def rate_limit_auth(request: Request) -> None:
    """Strict limit for auth endpoints (login, register, password reset)."""
    await check_rate_limit(request, limit=settings.RATE_LIMIT_AUTH_PER_MINUTE, window=60)


async def rate_limit_upload(request: Request, user_id: str) -> None:
    """Limit image uploads per authenticated user."""
    await check_rate_limit(
        request,
        limit=settings.RATE_LIMIT_UPLOAD_PER_MINUTE,
        window=60,
        user_id=user_id,
    )


async def rate_limit_order(request: Request, user_id: str) -> None:
    """Limit order creation per authenticated user."""
    await check_rate_limit(
        request,
        limit=settings.RATE_LIMIT_ORDER_PER_MINUTE,
        window=60,
        user_id=user_id,
    )
