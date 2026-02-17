"""
Kabul Sweets — Main FastAPI Application
========================================
Initializes the app with middleware, routes, and lifecycle events.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.redis import close_redis

settings = get_settings()


ORDER_STATUS_ENUM_SYNC_SQL = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus')
       AND NOT EXISTS (
            SELECT 1
            FROM pg_type t
            JOIN pg_enum e ON e.enumtypid = t.oid
            WHERE t.typname = 'orderstatus'
              AND e.enumlabel = 'PENDING_APPROVAL'
       )
    THEN
        ALTER TYPE orderstatus ADD VALUE 'PENDING_APPROVAL' AFTER 'PENDING';
    END IF;
END $$;
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown events."""
    # ── Startup ──────────────────────────────────────────────────────────
    setup_logging()
    logger = get_logger("main")
    logger.info("🧁 Starting %s (env=%s)", settings.APP_NAME, settings.APP_ENV)
    logger.info("API prefix: %s", settings.API_PREFIX)

    # Auto-create tables and seed if database is empty
    try:
        from app.core.database import engine, Base, async_session_factory
        from sqlalchemy import text

        # Import ALL models so Base.metadata knows about them
        from app.models.user import User  # noqa: F401
        from app.models.audit_log import AuditLog  # noqa: F401
        from app.models.product import Product, ProductVariant, StockAdjustment  # noqa: F401
        from app.models.order import Order, OrderItem, Payment  # noqa: F401
        from app.models.analytics import AnalyticsEvent, DailyRevenue  # noqa: F401
        from app.services.ai_service import ProductEmbedding, AIQueryLog  # noqa: F401
        from app.models.business import ScheduleCapacity, CakeDeposit  # noqa: F401
        from app.models.ml import (  # noqa: F401
            CakePricePrediction, ServingEstimate, CustomCake, ProcessedImage, MLModelVersion,
        )

        # In production, rely on Alembic migrations exclusively.
        # In dev/test, auto-create tables for convenience.
        if settings.is_production:
            logger.info("🔒 Production mode — using Alembic migrations only (skipping create_all)")
        else:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.execute(text(ORDER_STATUS_ENUM_SYNC_SQL))
            logger.info("✅ Database tables verified (dev mode — create_all)")

        # Check if database needs seeding (no users = empty DB)
        # Auto-seeding is disabled in production for security.
        if settings.is_production:
            logger.info("🔒 Production mode — auto-seeding disabled")
        else:
            async with async_session_factory() as session:
                result = await session.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()
                if user_count == 0:
                    logger.info("🌱 Empty database detected — auto-seeding...")
                    from app.seed import seed_database
                    await seed_database()
                else:
                    logger.info("📦 Database has %d users — skipping seed", user_count)
    except Exception as e:
        logger.error("Database setup error: %s", str(e))
        logger.info("💡 Make sure PostgreSQL is running: docker compose up -d")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    logger.info("Shutting down %s...", settings.APP_NAME)
    await close_redis()
    logger.info("Goodbye! 🍰")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        description=(
            "Backend API for Kabul Sweets — an Afghan bakery e-commerce platform. "
            "Manage products, orders, payments, and more."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS Middleware ──────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ───────────────────────────────────────────────────────────
    app.include_router(api_v1_router, prefix=settings.API_PREFIX)

    # ── Root Endpoint ────────────────────────────────────────────────────
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": "0.1.0",
            "docs": "/docs",
            "health": f"{settings.API_PREFIX}/health",
        }

    return app


# Create the app instance
app = create_app()
