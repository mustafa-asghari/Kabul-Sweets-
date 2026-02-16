"""
Celery application configuration.
Uses Redis as broker and result backend.
Falls back to synchronous tasks when Celery is unavailable.
"""

import os
from types import SimpleNamespace

from dotenv import load_dotenv

load_dotenv()

APP_ENV = os.getenv("APP_ENV", "development")
TASK_ALWAYS_EAGER = (
    os.getenv(
        "CELERY_TASK_ALWAYS_EAGER",
        "true" if APP_ENV.lower() != "production" else "false",
    ).lower()
    == "true"
)

try:
    from celery import Celery
except ModuleNotFoundError:
    Celery = None


class _SyncBoundTask:
    """Fallback object passed as task 'self' for bind=True tasks."""

    def retry(self, exc=None):
        if exc:
            raise exc
        raise RuntimeError("Task retry requested, but Celery is unavailable")


class _SyncTaskWrapper:
    """Wraps a task function and exposes `.delay()` for compatibility."""

    def __init__(self, func, bind: bool):
        self._func = func
        self._bind = bind
        self.__name__ = getattr(func, "__name__", "task")
        self.__doc__ = getattr(func, "__doc__", None)

    def __call__(self, *args, **kwargs):
        if self._bind:
            return self._func(_SyncBoundTask(), *args, **kwargs)
        return self._func(*args, **kwargs)

    def delay(self, *args, **kwargs):
        return self.__call__(*args, **kwargs)


class _SyncCeleryApp:
    """Minimal Celery-like interface used when celery is not installed."""

    def __init__(self):
        self.conf = SimpleNamespace(beat_schedule={})

    def task(self, *_, **kwargs):
        bind = bool(kwargs.get("bind"))

        def decorator(func):
            return _SyncTaskWrapper(func, bind=bind)

        return decorator


if Celery is not None:
    celery_app = Celery(
        "kabul_sweets",
        broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
        backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
    )
else:
    celery_app = _SyncCeleryApp()


if Celery is not None:
    celery_app.conf.update(
        # Serialization
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",

        # Timezone
        timezone="Australia/Sydney",
        enable_utc=True,

        # Retry defaults
        task_default_retry_delay=60,  # 1 minute
        task_max_retries=3,
        task_always_eager=TASK_ALWAYS_EAGER,
        task_eager_propagates=True,

        # Task routing
        task_routes={
            "app.workers.email_tasks.*": {"queue": "email"},
            "app.workers.sms_tasks.*": {"queue": "sms"},
            "app.workers.telegram_tasks.*": {"queue": "alerts"},
            "app.workers.analytics_tasks.*": {"queue": "analytics"},
            "app.workers.cart_tasks.*": {"queue": "default"},
            "app.workers.trend_tasks.*": {"queue": "analytics"},
        },

        # Worker settings
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,

        # Result expiration
        result_expires=3600,  # 1 hour

        # Task discovery
        imports=[
            "app.workers.email_tasks",
            "app.workers.sms_tasks",
            "app.workers.telegram_tasks",
            "app.workers.analytics_tasks",
            "app.workers.cart_tasks",
            "app.workers.trend_tasks",
        ],
    )

    celery_app.conf.beat_schedule = {
        "daily-revenue-aggregation": {
            "task": "app.workers.analytics_tasks.aggregate_daily_revenue",
            "schedule": 86400.0,  # Every 24 hours
        },
        "low-stock-check": {
            "task": "app.workers.analytics_tasks.check_low_stock_alerts",
            "schedule": 3600.0,  # Every hour
        },
        "abandoned-cart-recovery": {
            "task": "app.workers.cart_tasks.process_abandoned_carts",
            "schedule": 3600.0,  # Every hour
        },
        "weekly-trend-detection": {
            "task": "app.workers.trend_tasks.detect_trends",
            "schedule": 86400.0,  # Every 24 hours (analyzes weekly data)
        },
    }
