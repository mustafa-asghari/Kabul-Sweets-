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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown events."""
    # ── Startup ──────────────────────────────────────────────────────────
    setup_logging()
    logger = get_logger("main")
    logger.info("🧁 Starting %s (env=%s)", settings.APP_NAME, settings.APP_ENV)
    logger.info("API prefix: %s", settings.API_PREFIX)

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
