"""
Monitoring service — Phase 12.
Structured error tracking, health monitoring, and alerting.
"""

import os
import time
import traceback
from datetime import datetime, timezone

from app.core.logging import get_logger

logger = get_logger("monitoring")

SENTRY_DSN = os.getenv("SENTRY_DSN", "")


def setup_sentry(app=None):
    """Initialize Sentry for error monitoring (if configured)."""
    if not SENTRY_DSN:
        logger.info("Sentry DSN not configured — error tracking disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            traces_sample_rate=0.1,  # 10% of transactions
            profiles_sample_rate=0.1,
            environment=os.getenv("APP_ENV", "development"),
            release=os.getenv("APP_VERSION", "0.1.0"),
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
            ],
        )
        logger.info("✅ Sentry initialized")
    except ImportError:
        logger.warning("sentry-sdk not installed — error tracking disabled")


class HealthMonitor:
    """Monitors system health and tracks failures."""

    _failure_counts: dict[str, int] = {}
    _last_check: dict[str, float] = {}

    @classmethod
    def record_failure(cls, service: str, error: str):
        """Record a service failure."""
        cls._failure_counts[service] = cls._failure_counts.get(service, 0) + 1
        logger.error(
            "Service failure [%s] (count: %d): %s",
            service, cls._failure_counts[service], error,
        )

        # Alert if too many failures
        if cls._failure_counts[service] >= 5:
            cls._send_alert(service, cls._failure_counts[service], error)
            cls._failure_counts[service] = 0

    @classmethod
    def record_success(cls, service: str):
        """Record a service success (resets failure count)."""
        if cls._failure_counts.get(service, 0) > 0:
            logger.info("Service recovered: %s", service)
        cls._failure_counts[service] = 0
        cls._last_check[service] = time.time()

    @classmethod
    def get_status(cls) -> dict:
        """Get current health status."""
        return {
            "failures": dict(cls._failure_counts),
            "last_checks": {
                k: datetime.fromtimestamp(v, tz=timezone.utc).isoformat()
                for k, v in cls._last_check.items()
            },
        }

    @classmethod
    def _send_alert(cls, service: str, count: int, error: str):
        """Send alert for repeated failures."""
        logger.critical(
            "🚨 ALERT: %s has failed %d times. Last error: %s",
            service, count, error,
        )
        # Publish to Redis for admin dashboard
        try:
            import json
            import redis as redis_sync
            r = redis_sync.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
            r.publish("admin:alerts", json.dumps({
                "type": "service_failure",
                "service": service,
                "failure_count": count,
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }))
        except Exception:
            pass


class RequestTimer:
    """Track request timing for performance monitoring."""

    @staticmethod
    def start() -> float:
        return time.perf_counter()

    @staticmethod
    def elapsed_ms(start: float) -> int:
        return int((time.perf_counter() - start) * 1000)

    @staticmethod
    def log_slow_request(path: str, method: str, elapsed_ms: int, threshold: int = 1000):
        """Log slow requests exceeding threshold."""
        if elapsed_ms > threshold:
            logger.warning(
                "🐌 Slow request: %s %s took %dms (threshold: %dms)",
                method, path, elapsed_ms, threshold,
            )


class WebhookMonitor:
    """Track webhook processing for reliability."""

    _webhook_stats: dict[str, dict] = {}

    @classmethod
    def record_webhook(cls, source: str, event_type: str, success: bool, error: str | None = None):
        """Record a webhook processing result."""
        key = f"{source}:{event_type}"
        if key not in cls._webhook_stats:
            cls._webhook_stats[key] = {"success": 0, "failure": 0, "last_error": None}

        if success:
            cls._webhook_stats[key]["success"] += 1
        else:
            cls._webhook_stats[key]["failure"] += 1
            cls._webhook_stats[key]["last_error"] = error
            logger.error("Webhook failed [%s]: %s", key, error)

            # Alert on repeated failures
            if cls._webhook_stats[key]["failure"] >= 3:
                HealthMonitor.record_failure(f"webhook:{source}", error or "Unknown")

    @classmethod
    def get_stats(cls) -> dict:
        return dict(cls._webhook_stats)


class TaskMonitor:
    """Track Celery task outcomes."""

    _task_stats: dict[str, dict] = {}

    @classmethod
    def record_task(cls, task_name: str, success: bool, duration_ms: int = 0, error: str | None = None):
        """Record a Celery task result."""
        if task_name not in cls._task_stats:
            cls._task_stats[task_name] = {"success": 0, "failure": 0, "total_ms": 0}

        if success:
            cls._task_stats[task_name]["success"] += 1
            cls._task_stats[task_name]["total_ms"] += duration_ms
        else:
            cls._task_stats[task_name]["failure"] += 1
            logger.error("Task failed [%s]: %s", task_name, error)

            if cls._task_stats[task_name]["failure"] >= 3:
                HealthMonitor.record_failure(f"task:{task_name}", error or "Unknown")

    @classmethod
    def get_stats(cls) -> dict:
        return dict(cls._task_stats)
