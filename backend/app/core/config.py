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
    BUSINESS_TIMEZONE: str = "Australia/Sydney"

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = Field(default_factory=list)

    # ── Gemini (AI) ──────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_IMAGE_MODEL: str = "gemini-3-pro-image-preview"
    GEMINI_TEXT_MODEL: str = "gemini-3-pro-preview"

    # ── Rate Limiting ────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── Logging ──────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

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
        elif isinstance(v, (list, tuple, set)):
            parsed = list(v)
        else:
            parsed = [v]

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
