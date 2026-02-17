"""
Celery application configuration.
Uses Redis as broker and result backend.
Falls back to synchronous tasks when Celery is unavailable.
"""

import os
from types import SimpleNamespace
from urllib.parse import urlparse, urlunparse

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


def _build_redis_url(base_url: str, db: int) -> str:
    """
    Build a Redis URL that reuses host/auth/query from base_url
    but switches to the requested DB index.
    """
    parsed = urlparse(base_url)
    if parsed.scheme not in {"redis", "rediss"}:
        return base_url
    return urlunparse(parsed._replace(path=f"/{db}"))


def _is_local_redis_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.hostname in {"localhost", "127.0.0.1", "::1"}


def _resolve_redis_base_url() -> str:
    redis_url = os.getenv("REDIS_URL")
    docker_redis_url = os.getenv("DOCKER_REDIS_URL")

    # Safety: prefer docker/non-local URL if REDIS_URL is localhost.
    if redis_url and docker_redis_url:
        if _is_local_redis_url(redis_url) and not _is_local_redis_url(docker_redis_url):
            return docker_redis_url
        return redis_url

    if redis_url:
        return redis_url
    if docker_redis_url:
        return docker_redis_url
    return "redis://localhost:6379/0"


def _resolve_celery_url(primary_env: str, fallback_env: str, db: int) -> str:
    """
    Resolve Celery URLs in this order:
    1) explicit env (CELERY_*)
    2) docker-specific env (DOCKER_CELERY_*)
    3) derived from REDIS_URL / DOCKER_REDIS_URL by DB index
    4) localhost fallback
    """
    redis_base = _resolve_redis_base_url()
    explicit = os.getenv(primary_env)
    if explicit:
        # Safety: if Celery URL points to localhost but REDIS_URL points to
        # a remote/service host, follow REDIS_URL to avoid localhost failures.
        if _is_local_redis_url(explicit) and not _is_local_redis_url(redis_base):
            return _build_redis_url(redis_base, db)
        return explicit

    fallback = os.getenv(fallback_env)
    if fallback:
        if _is_local_redis_url(fallback) and not _is_local_redis_url(redis_base):
            return _build_redis_url(redis_base, db)
        return fallback

    return _build_redis_url(redis_base, db)


CELERY_BROKER_URL = _resolve_celery_url(
    "CELERY_BROKER_URL",
    "DOCKER_CELERY_BROKER_URL",
    db=1,
)
CELERY_RESULT_BACKEND = _resolve_celery_url(
    "CELERY_RESULT_BACKEND",
    "DOCKER_CELERY_RESULT_BACKEND",
    db=2,
)


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
        broker=CELERY_BROKER_URL,
        backend=CELERY_RESULT_BACKEND,
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
