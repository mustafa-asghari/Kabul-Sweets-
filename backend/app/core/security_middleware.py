"""
Security middleware — Content Security Policy, CORS hardening, request validation,
DDoS throttling, and 2FA support.
"""

import hashlib
import os
import time
import uuid

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("security")
_settings = get_settings()


# ── Security Headers ─────────────────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""

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
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(self)"
        )

        # Unique request ID for tracing (added to both request and response)
        req_id = request.state.__dict__.get("request_id", "")
        if req_id:
            response.headers["X-Request-ID"] = req_id

        # HSTS — production only
        if _settings.APP_ENV == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response


# ── Request Validation ───────────────────────────────────────────────────────

class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Reject requests that contain obvious injection patterns or are structurally
    suspicious. This is a fast first-pass guard — Pydantic / endpoint-level
    validators provide the second, domain-aware layer.
    """

    # Query-string / URL patterns that signal an attack attempt
    _SQL_PATTERNS = (
        "' or ",
        "' or 1=1",
        "'; drop",
        "; drop table",
        "union select",
        "' union",
        "or 1=1",
        "or '1'='1",
        "--",
        "/*",
        "xp_cmdshell",
        "exec(",
        "execute(",
    )

    _XSS_PATTERNS = (
        "<script",
        "javascript:",
        "vbscript:",
        "onload=",
        "onerror=",
        "eval(",
        "expression(",
        "document.cookie",
        "window.location",
    )

    _INJECTION_PATTERNS = (
        "__import__",
        "os.system",
        "subprocess.",
        "importlib",
        "/etc/passwd",
        "/etc/shadow",
        "../../../",
        "..\\..\\",
        "%2e%2e%2f",          # URL-encoded ../
        "%252e%252e%252f",    # double-encoded ../
    )

    _ALL_BLOCKED = _SQL_PATTERNS + _XSS_PATTERNS + _INJECTION_PATTERNS

    # Paths that are exempt from heavy validation (webhooks, health checks)
    _EXEMPT_PREFIXES = ("/api/v1/health", "/api/v1/ping", "/", "/docs", "/redoc")

    async def dispatch(self, request: Request, call_next):
        # Attach a unique request ID for tracing
        request.state.request_id = str(uuid.uuid4())

        path = request.url.path

        # Skip validation for exempt paths
        for prefix in self._EXEMPT_PREFIXES:
            if path == prefix or (prefix != "/" and path.startswith(prefix)):
                return await call_next(request)

        # ── Query string injection check ──────────────────────────────────
        raw_qs = (request.url.query or "").lower()
        for pattern in self._ALL_BLOCKED:
            if pattern in raw_qs:
                logger.warning(
                    "Blocked suspicious query string from %s: pattern=%r path=%s",
                    request.client.host if request.client else "?",
                    pattern,
                    path,
                )
                return Response(
                    content='{"detail":"Request blocked"}',
                    status_code=400,
                    media_type="application/json",
                )

        # ── Path traversal check ─────────────────────────────────────────
        raw_path = request.url.path.lower()
        for pattern in ("../", "..\\", "%2e%2e", "%252e"):
            if pattern in raw_path:
                logger.warning(
                    "Blocked path traversal attempt from %s: %s",
                    request.client.host if request.client else "?",
                    path,
                )
                return Response(
                    content='{"detail":"Invalid path"}',
                    status_code=400,
                    media_type="application/json",
                )

        # ── Content-Length cap (10 MB — Pydantic/routes enforce stricter limits) ─
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > 10 * 1024 * 1024:
                    return Response(
                        content='{"detail":"Request body too large"}',
                        status_code=413,
                        media_type="application/json",
                    )
            except ValueError:
                pass  # malformed header — let it through, route will reject

        return await call_next(request)


# ── IP-level DDoS throttle ────────────────────────────────────────────────────

class IPThrottleMiddleware(BaseHTTPMiddleware):
    """
    Fast in-memory IP-level throttle.
    Caps sustained burst rate before Redis-backed per-user limiting kicks in.
    Not a substitute for per-user rate limiting — works alongside it.
    """

    _SKIP_PATHS = {"/api/v1/health", "/api/v1/ping", "/"}

    def __init__(self, app, requests_per_second: int = 30):
        super().__init__(app)
        self.rps = requests_per_second
        self._buckets: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._SKIP_PATHS:
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.time()

        bucket = self._buckets.setdefault(ip, [])
        # Slide the window
        self._buckets[ip] = [t for t in bucket if now - t < 1.0]

        if len(self._buckets[ip]) >= self.rps:
            logger.warning(
                "IP burst throttle triggered: %s (%d req/s, cap=%d)",
                ip, len(self._buckets[ip]), self.rps,
            )
            return Response(
                content='{"detail":"Too many requests"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "1"},
            )

        self._buckets[ip].append(now)

        # Periodic cleanup to prevent unbounded memory growth
        total = sum(len(v) for v in self._buckets.values())
        if total > 10_000:
            self._cleanup(now)

        return await call_next(request)

    def _cleanup(self, now: float) -> None:
        stale = [ip for ip, ts in self._buckets.items() if not ts or now - ts[-1] > 60]
        for ip in stale:
            del self._buckets[ip]


# ── 2FA (TOTP) ───────────────────────────────────────────────────────────────

class TOTPService:
    """Time-based One-Time Password support for admin 2FA."""

    @staticmethod
    def generate_secret() -> str:
        import base64
        return base64.b32encode(os.urandom(20)).decode("utf-8")

    @staticmethod
    def verify_totp(secret: str, code: str) -> bool:
        try:
            import base64
            import hmac
            import struct

            secret_bytes = base64.b32decode(secret)
            step = int(time.time()) // 30

            for offset in (-1, 0, 1):
                msg = struct.pack(">Q", step + offset)
                h = hmac.new(secret_bytes, msg, hashlib.sha1).digest()
                o = h[-1] & 0x0F
                truncated = struct.unpack(">I", h[o: o + 4])[0] & 0x7FFFFFFF
                expected = str(truncated % 1_000_000).zfill(6)
                if hmac.compare_digest(expected, code):
                    return True
            return False
        except Exception:
            return False


# ── File upload validation (used at the route level) ─────────────────────────

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB


def validate_image_upload(content_type: str, file_size: int) -> tuple[bool, str]:
    """Lightweight pre-check before magic-byte inspection."""
    if content_type not in ALLOWED_IMAGE_TYPES:
        return False, (
            f"Invalid image type: {content_type}. "
            f"Allowed: {', '.join(sorted(ALLOWED_IMAGE_TYPES))}"
        )
    if file_size > MAX_IMAGE_SIZE:
        mb = MAX_IMAGE_SIZE // (1024 * 1024)
        return False, f"Image too large ({file_size} bytes). Maximum is {mb} MB."
    return True, ""


# ── Apply all middleware ──────────────────────────────────────────────────────

def apply_security_middleware(app: FastAPI) -> None:
    """Register all security middleware on the FastAPI application."""
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestValidationMiddleware)
    app.add_middleware(IPThrottleMiddleware, requests_per_second=30)
    logger.info("Security middleware applied (headers / validation / IP throttle)")
