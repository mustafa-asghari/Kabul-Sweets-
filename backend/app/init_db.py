"""
Database initialisation script.
- Creates all tables for brand-new databases (idempotent via create_all).
- Stamps Alembic migration history so upgrade head runs cleanly afterwards.

Run with: python -m app.init_db
"""

import asyncio
import logging
import subprocess

from sqlalchemy import text

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


async def _alembic_version_exists(conn) -> bool:
    result = await conn.execute(text(
        "SELECT EXISTS ("
        "  SELECT FROM information_schema.tables"
        "  WHERE table_name = 'alembic_version'"
        ")"
    ))
    return result.scalar()


async def _column_exists(conn, table: str, column: str) -> bool:
    result = await conn.execute(text(
        "SELECT EXISTS ("
        "  SELECT FROM information_schema.columns"
        f" WHERE table_name = '{table}' AND column_name = '{column}'"
        ")"
    ))
    return result.scalar()


async def init_db() -> None:
    log.info("Creating database tables (create_all)...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    log.info("Checking Alembic migration state...")
    async with engine.connect() as conn:
        alembic_exists = await _alembic_version_exists(conn)

        if not alembic_exists:
            # No migration history yet. Stamp at the correct revision so
            # `alembic upgrade head` only applies genuinely missing changes.
            clerk_col_exists = await _column_exists(conn, "users", "clerk_user_id")

            if clerk_col_exists:
                # create_all already built the full schema including clerk_user_id —
                # stamp as head so no migrations try to re-add existing columns.
                log.info("Stamping Alembic at head (fresh database, full schema in place).")
                subprocess.run(["alembic", "stamp", "add_clerk_user_id"], check=True)
            else:
                # Existing database created by an old create_all (no clerk_user_id yet) —
                # stamp at add_staff_role so upgrade head adds only the new column.
                log.info("Stamping Alembic at add_staff_role (existing database, needs clerk migration).")
                subprocess.run(["alembic", "stamp", "add_staff_role"], check=True)

    await engine.dispose()
    log.info("Database tables ready.")


if __name__ == "__main__":
    asyncio.run(init_db())
