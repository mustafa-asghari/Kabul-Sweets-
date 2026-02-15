"""
Security middleware — Phase 11.
Content Security Policy, CORS hardening, request validation, 2FA support.
"""

import hashlib
import os
import time

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger("security")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://js.stripe.com; "
            "frame-src https://js.stripe.com; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self' https://api.stripe.com"
        )

        # Other security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(self)"
        )

        # HSTS (only in production)
        if os.getenv("APP_ENV") == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate incoming requests for suspicious content."""

    BLOCKED_PATTERNS = [
        "' OR ",
        "'; DROP",
        "<script>",
        "javascript:",
        "eval(",
        "__import__",
        "os.system",
    ]

    async def dispatch(self, request: Request, call_next):
        # Check query string for SQL injection / XSS
        query_string = str(request.url.query or "").lower()
        for pattern in self.BLOCKED_PATTERNS:
            if pattern.lower() in query_string:
                logger.warning(
                    "Blocked suspicious request from %s: %s",
                    request.client.host if request.client else "unknown",
                    request.url.path,
                )
                return Response(
                    content='{"detail": "Request blocked"}',
                    status_code=400,
                    media_type="application/json",
                )

        # Request size limit (10MB)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:
            return Response(
                content='{"detail": "Request too large"}',
                status_code=413,
                media_type="application/json",
            )

        return await call_next(request)


class IPThrottleMiddleware(BaseHTTPMiddleware):
    """
    IP-based throttling for DDoS protection.
    Allows N requests per second per IP.
    """

    def __init__(self, app, requests_per_second: int = 50):
        super().__init__(app)
        self.rps = requests_per_second
        self._buckets: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"

        # Skip health checks
        if request.url.path in ("/api/v1/health", "/api/v1/ping", "/"):
            return await call_next(request)

        now = time.time()

        if ip not in self._buckets:
            self._buckets[ip] = []

        # Clean old entries (> 1 second ago)
        self._buckets[ip] = [t for t in self._buckets[ip] if now - t < 1.0]

        if len(self._buckets[ip]) >= self.rps:
            logger.warning("IP throttled: %s (%d req/s)", ip, len(self._buckets[ip]))
            return Response(
                content='{"detail": "Too many requests"}',
                status_code=429,
                media_type="application/json",
            )

        self._buckets[ip].append(now)

        # Periodic cleanup (every 1000 requests)
        if sum(len(v) for v in self._buckets.values()) > 10000:
            self._cleanup()

        return await call_next(request)

    def _cleanup(self):
        """Remove stale IP entries."""
        now = time.time()
        stale = [ip for ip, times in self._buckets.items() if not times or now - times[-1] > 60]
        for ip in stale:
            del self._buckets[ip]


# ── 2FA Support ──────────────────────────────────────────────────────────────
class TOTPService:
    """Time-based One-Time Password support for admin 2FA."""

    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret."""
        import base64
        return base64.b32encode(os.urandom(20)).decode("utf-8")

    @staticmethod
    def verify_totp(secret: str, code: str) -> bool:
        """Verify a TOTP code against a secret."""
        try:
            import hmac
            import struct

            # Current time step (30-second window)
            time_step = int(time.time()) // 30
            secret_bytes = None

            try:
                import base64
                secret_bytes = base64.b32decode(secret)
            except Exception:
                return False

            # Check current and adjacent time steps (±1)
            for offset in [-1, 0, 1]:
                step = time_step + offset
                msg = struct.pack(">Q", step)
                h = hmac.new(secret_bytes, msg, hashlib.sha1).digest()
                o = h[-1] & 0x0F
                truncated = struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF
                expected = str(truncated % 1000000).zfill(6)

                if hmac.compare_digest(expected, code):
                    return True

            return False
        except Exception:
            return False


# ── File Upload Validation ───────────────────────────────────────────────────
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


def validate_image_upload(content_type: str, file_size: int) -> tuple[bool, str]:
    """Validate an image upload."""
    if content_type not in ALLOWED_IMAGE_TYPES:
        return False, f"Invalid image type: {content_type}. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}"
    if file_size > MAX_IMAGE_SIZE:
        return False, f"Image too large: {file_size} bytes. Maximum: {MAX_IMAGE_SIZE} bytes"
    return True, ""


# ── Apply Middleware ─────────────────────────────────────────────────────────
def apply_security_middleware(app: FastAPI):
    """Apply all security middleware to the FastAPI app."""
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestValidationMiddleware)
    app.add_middleware(IPThrottleMiddleware, requests_per_second=50)
    logger.info("✅ Security middleware applied")
