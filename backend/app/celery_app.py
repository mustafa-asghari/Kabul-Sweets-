"""
Celery application configuration.
Uses Redis as broker and result backend.
"""

import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# ── Celery App ───────────────────────────────────────────────────────────────
celery_app = Celery(
    "kabul_sweets",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
)

# ── Configuration ────────────────────────────────────────────────────────────
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

    # Task routing
    task_routes={
        "app.workers.email_tasks.*": {"queue": "email"},
        "app.workers.sms_tasks.*": {"queue": "sms"},
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
        "app.workers.analytics_tasks",
        "app.workers.cart_tasks",
        "app.workers.trend_tasks",
    ],
)

# ── Beat Schedule (periodic tasks) ──────────────────────────────────────────
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
