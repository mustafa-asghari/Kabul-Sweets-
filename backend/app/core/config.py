"""
Application configuration loaded from environment variables.
Uses pydantic-settings for validation and type coercion.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    model_config = SettingsConfigDict(  
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ── Application ──────────────────────────────────────────────────────
    APP_NAME: str = "Kabul Sweets"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = Field(...)
    API_PREFIX: str = "/api/v1"

    # ── Server ───────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(...)
    DATABASE_ECHO: bool = False

    # ── Redis ────────────────────────────────────────────────────────────
    REDIS_URL: str = Field(...)

    # ── JWT Auth ─────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = Field(...)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # ── Telegram Bot (Admin Alerts) ─────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    TELEGRAM_ADMIN_CHAT_IDS: List[int] = []
    TELEGRAM_ACTING_ADMIN_EMAIL: str | None = None
    ADMIN_FRONTEND_URL: str = Field(...)
    FRONTEND_URL: str = Field(...)
    BUSINESS_TIMEZONE: str = "Australia/Brisbane"

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = Field(default_factory=list)

    # ── Gemini (AI) ──────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_IMAGE_MODEL: str = "gemini-2.0-flash-exp-image-generation"
    GEMINI_TEXT_MODEL: str = "gemini-2.0-flash"

    # ── SMTP ─────────────────────────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 0
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = ""
    SMTP_TIMEOUT_SECONDS: float = 15.0

    # ── Mailgun ──────────────────────────────────────────────────────────
    MAILGUN_API_KEY: str = ""
    MAILGUN_DOMAIN: str = ""
    MAILGUN_BASE_URL: str = "https://api.mailgun.net"
    MAILGUN_FROM_EMAIL: str = ""
    MAILGUN_FROM_NAME: str = ""
    MAILGUN_TIMEOUT_SECONDS: float = 15.0

    # ── Resend ───────────────────────────────────────────────────────────
    RESEND_API_KEY: str = ""

    # ── Stripe ───────────────────────────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_SUCCESS_URL: str = ""
    STRIPE_CANCEL_URL: str = ""

    # ── Celery ───────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""
    CELERY_TASK_ALWAYS_EAGER: str = ""

    # ── ML ────────────────────────────────────────────────────────────────
    ML_USE_XGBOOST: bool = True
    XGBOOST_MODEL_PATH: str = ""
    XGBOOST_MIN_TRAINING_SAMPLES: int = 50

    # ── Monitoring ────────────────────────────────────────────────────────
    SENTRY_DSN: str = ""
    APP_VERSION: str = "0.1.0"

    # ── AWS S3 (image storage — no blobs in the DB) ──────────────────────
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_ENDPOINT_URL: str = ""          # blank = real AWS; set for MinIO/LocalStack
    S3_BUCKET_NAME: str = "kabul-sweets-media"
    S3_PRESIGNED_URL_TTL: int = 86400   # 24 h — public product images
    S3_ADMIN_URL_TTL: int = 3600        # 1 h  — admin-only originals

    # ── Rate Limiting ────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60          # default for most endpoints
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10     # login / register / password-reset
    RATE_LIMIT_UPLOAD_PER_MINUTE: int = 20   # image uploads (per authenticated user)
    RATE_LIMIT_ORDER_PER_MINUTE: int = 30    # order creation (per user)

    # ── Logging ──────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def coerce_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("TELEGRAM_ADMIN_CHAT_IDS", mode="before")
    @classmethod
    def parse_telegram_admin_chat_ids(cls, v):
        if v is None:
            return []

        if isinstance(v, int):
            return [v]

        if isinstance(v, str):
            import json

            try:
                parsed = json.loads(v)
            except json.JSONDecodeError:
                parsed = [item.strip() for item in v.split(",") if item.strip()]
        else:
            parsed = v
        
        if isinstance(parsed, (int, float)):
            parsed = [parsed]
        elif isinstance(v, (list, tuple, set)):
            parsed = list(v)
        elif not isinstance(parsed, list):
             # Fallback for unexpected types
            parsed = [parsed]

        if not parsed:
            return []

        return [int(chat_id) for chat_id in parsed]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def sync_database_url(self) -> str:
        """Synchronous DB URL for Alembic migrations."""
        return self.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg")


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
