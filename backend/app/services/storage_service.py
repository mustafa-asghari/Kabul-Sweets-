"""
AWS S3 storage service for all media files.

All images (original uploads and Gemini-processed results) are stored here.
Nothing image-related is stored as blobs in the database — only S3 object keys.

Backward-compatible: existing records that contain "data:image/..." base64 strings
continue to work. New uploads always go to S3.
"""

import asyncio
import functools
import threading
from typing import Optional

from app.core.logging import get_logger

logger = get_logger("storage")

# ── MIME → file extension map ─────────────────────────────────────────────────
MIME_TO_EXT: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}

# ── Thread-local boto3 client (boto3 clients are not thread-safe) ────────────
_thread_local = threading.local()


def _make_boto3_client():
    """Create a boto3 S3 client using current settings. Called once per thread."""
    import boto3
    from app.core.config import get_settings
    s = get_settings()
    kwargs: dict = {
        "region_name": s.AWS_REGION or "us-east-1",
    }
    if s.AWS_ACCESS_KEY_ID:
        kwargs["aws_access_key_id"] = s.AWS_ACCESS_KEY_ID
    if s.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_secret_access_key"] = s.AWS_SECRET_ACCESS_KEY
    if s.AWS_ENDPOINT_URL:
        # Allows using MinIO or LocalStack for local dev
        kwargs["endpoint_url"] = s.AWS_ENDPOINT_URL
    return boto3.client("s3", **kwargs)


def _s3():
    """Return this thread's S3 client, creating it if needed."""
    if not hasattr(_thread_local, "client"):
        _thread_local.client = _make_boto3_client()
    return _thread_local.client


# ── Storage service ──────────────────────────────────────────────────────────
class StorageService:
    """
    Async-compatible S3 storage via boto3 + ThreadPoolExecutor.

    All boto3 calls (synchronous) are wrapped in asyncio.run_in_executor
    so they never block the event loop.

    S3 key conventions
    ──────────────────
    • Original uploads  : images/originals/{uuid}.{ext}
    • Processed by AI   : images/processed/{uuid}.{ext}
    """

    def __init__(self) -> None:
        from app.core.config import get_settings
        s = get_settings()
        self.bucket: str = s.S3_BUCKET_NAME
        self.public_ttl: int = s.S3_PRESIGNED_URL_TTL
        self.admin_ttl: int = s.S3_ADMIN_URL_TTL

    # ── Internal helper ──────────────────────────────────────────────────────

    @staticmethod
    async def _run(fn, *args, **kwargs) -> object:
        """Run a synchronous callable in the default thread-pool executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, functools.partial(fn, *args, **kwargs)
        )

    # ── Public API ───────────────────────────────────────────────────────────

    async def upload(self, key: str, data: bytes, content_type: str = "image/jpeg") -> str:
        """
        Upload raw bytes to S3 under the given key.
        Returns the key (so callers can store it in the DB).
        """
        def _put():
            _s3().put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )

        await self._run(_put)
        logger.info("S3 upload: s3://%s/%s (%d bytes)", self.bucket, key, len(data))
        return key

    async def download(self, key: str) -> bytes:
        """Download an S3 object and return its raw bytes."""
        def _get() -> bytes:
            resp = _s3().get_object(Bucket=self.bucket, Key=key)
            return resp["Body"].read()

        data: bytes = await self._run(_get)  # type: ignore[assignment]
        logger.debug("S3 download: s3://%s/%s (%d bytes)", self.bucket, key, len(data))
        return data

    async def delete(self, key: str) -> None:
        """Delete an object from S3. Safe to call if the key doesn't exist."""
        def _del():
            _s3().delete_object(Bucket=self.bucket, Key=key)

        await self._run(_del)
        logger.info("S3 delete: s3://%s/%s", self.bucket, key)

    async def presigned_url(self, key: str, ttl: int | None = None) -> str:
        """
        Generate a time-limited pre-signed GET URL for the given key.
        Default TTL comes from settings (S3_PRESIGNED_URL_TTL).
        """
        expires = ttl if ttl is not None else self.public_ttl

        def _sign() -> str:
            return _s3().generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires,
            )

        url: str = await self._run(_sign)  # type: ignore[assignment]
        return url

    async def exists(self, key: str) -> bool:
        """Return True if the key exists in S3."""
        try:
            def _head():
                _s3().head_object(Bucket=self.bucket, Key=key)
            await self._run(_head)
            return True
        except Exception:
            return False

    # ── Convenience helpers ──────────────────────────────────────────────────

    @staticmethod
    def is_s3_key(value: str | None) -> bool:
        """
        Return True if the value is an S3 object key (new format).
        Return False if it's a base64 data URL (legacy format).
        """
        if not value:
            return False
        return not value.startswith("data:")

    @staticmethod
    def key_for_original(image_id: object, content_type: str) -> str:
        """Build the S3 key for an original upload."""
        ext = MIME_TO_EXT.get(content_type, "jpg")
        return f"images/originals/{image_id}.{ext}"

    @staticmethod
    def key_for_processed(image_id: object, mime_type: str) -> str:
        """Build the S3 key for a Gemini-processed image."""
        ext = MIME_TO_EXT.get(mime_type, "jpg")
        return f"images/processed/{image_id}.{ext}"


# ── Singleton ─────────────────────────────────────────────────────────────────
_storage_instance: Optional[StorageService] = None


def get_storage() -> StorageService:
    """Return the application-wide StorageService singleton."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = StorageService()
    return _storage_instance
