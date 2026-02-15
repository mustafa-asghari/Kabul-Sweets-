"""
Database seed script.
Creates the initial admin user if one doesn't exist.
Run with: python -m app.seed
"""

import asyncio
import sys

from sqlalchemy import select

from app.core.database import async_session_factory, engine, Base
from app.core.logging import setup_logging, get_logger
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog  # noqa: F401 — ensure table is created


async def seed_database():
    """Seed the database with initial data."""
    setup_logging()
    logger = get_logger("seed")

    logger.info("🌱 Starting database seed...")

    # Create tables (for development; in production use Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables created/verified")

    async with async_session_factory() as session:
        # Check if admin exists
        result = await session.execute(
            select(User).where(User.role == UserRole.ADMIN)
        )
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            logger.info("Admin user already exists: %s", existing_admin.email)
        else:
            # Create default admin
            admin = User(
                email="admin@kabulsweets.com.au",
                hashed_password=hash_password("Admin@2024!"),
                full_name="Kabul Sweets Admin",
                phone="+61400000000",
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
            )
            session.add(admin)
            await session.commit()
            logger.info("✅ Admin user created: admin@kabulsweets.com.au")

        # Create a demo customer if none exists
        result = await session.execute(
            select(User).where(User.role == UserRole.CUSTOMER)
        )
        existing_customer = result.scalar_one_or_none()

        if existing_customer:
            logger.info("Customer user already exists: %s", existing_customer.email)
        else:
            customer = User(
                email="customer@example.com",
                hashed_password=hash_password("Customer@2024!"),
                full_name="Demo Customer",
                phone="+61411111111",
                role=UserRole.CUSTOMER,
                is_active=True,
                is_verified=True,
            )
            session.add(customer)
            await session.commit()
            logger.info("✅ Demo customer created: customer@example.com")

    logger.info("🌱 Database seed complete!")


if __name__ == "__main__":
    asyncio.run(seed_database())
