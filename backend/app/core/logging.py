"""
Structured logging configuration.
Uses Python's built-in logging with JSON-like structured output.
"""

import logging
import sys
from datetime import datetime, timezone

from app.core.config import get_settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured log entries."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = (
            f"{timestamp} | {record.levelname:<8} | "
            f"{record.name}:{record.funcName}:{record.lineno} | "
            f"{record.getMessage()}"
        )
        if record.exc_info and record.exc_info[1]:
            log_entry += f" | EXCEPTION: {self.formatException(record.exc_info)}"
        return log_entry


def setup_logging() -> None:
    """Configure application-wide logging."""
    settings = get_settings()

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(console_handler)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DATABASE_ECHO else logging.WARNING
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.getLogger("app").info("Logging system initialized (level=%s)", settings.LOG_LEVEL)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger for a module."""
    return logging.getLogger(f"app.{name}")
