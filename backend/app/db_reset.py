"""
Database reset script — drops all tables and re-seeds.
USE WITH CAUTION: This will delete ALL data!
Run with: python -m app.db_reset
"""

import asyncio
import sys

from app.core.database import async_session_factory, engine, Base
from app.core.logging import setup_logging, get_logger

# Import ALL models so SQLAlchemy knows about them
from app.models.user import User  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.product import Product, ProductVariant, StockAdjustment  # noqa: F401
from app.models.order import Order, OrderItem, Payment  # noqa: F401
from app.models.analytics import AnalyticsEvent, DailyRevenue  # noqa: F401
from app.models.business import ScheduleCapacity, CakeDeposit  # noqa: F401
from app.models.ml import (  # noqa: F401
    CakePricePrediction, ServingEstimate, CustomCake, ProcessedImage, MLModelVersion,
)


async def reset_database():
    setup_logging()
    logger = get_logger("db_reset")

    logger.warning("⚠️  DATABASE RESET — This will DELETE ALL data!")
    logger.warning("You have 3 seconds to cancel (Ctrl+C)...")

    await asyncio.sleep(3)

    # Drop all tables
    logger.info("🗑️  Dropping all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("✅ All tables dropped")

    # Recreate all tables
    logger.info("🔨 Recreating all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ All tables created")

    # Run the seed script
    logger.info("🌱 Seeding database...")
    from app.seed import seed_database
    await seed_database()

    logger.info("✅ Database reset complete!")


if __name__ == "__main__":
    if "--force" not in sys.argv:
        confirm = input("⚠️  This will DELETE ALL data. Type 'RESET' to confirm: ")
        if confirm != "RESET":
            print("Cancelled.")
            sys.exit(0)

    asyncio.run(reset_database())
