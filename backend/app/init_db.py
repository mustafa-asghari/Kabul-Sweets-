"""
Database initialisation script.
Creates all tables (idempotent — safe to run on every startup).
Does NOT seed data.

Run with: python -m app.init_db
"""

import asyncio
import logging

from app.core.database import engine, Base

# Import every model so SQLAlchemy knows about all tables
import app.models.user          # noqa: F401
import app.models.audit_log     # noqa: F401
import app.models.product       # noqa: F401
import app.models.order         # noqa: F401
import app.models.analytics     # noqa: F401
import app.models.business      # noqa: F401
import app.models.ml            # noqa: F401
import app.models.cart          # noqa: F401

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def init_db() -> None:
    log.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    log.info("Database tables ready.")


if __name__ == "__main__":
    asyncio.run(init_db())
