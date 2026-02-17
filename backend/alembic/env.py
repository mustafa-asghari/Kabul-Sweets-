"""
Alembic environment configuration.
Loads the actual database URL from app settings and
configures Alembic to use the application's SQLAlchemy models.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.core.database import Base

# Import all models so Alembic can detect them
from app.models.user import User  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.product import Product, ProductVariant, StockAdjustment  # noqa: F401
from app.models.order import Order, OrderItem, Payment  # noqa: F401
from app.models.analytics import AnalyticsEvent, DailyRevenue  # noqa: F401
from app.models.business import ScheduleCapacity, CakeDeposit  # noqa: F401
from app.models.ml import CakePricePrediction, ServingEstimate, CustomCake, ProcessedImage, MLModelVersion  # noqa: F401

# Alembic Config object
config = context.config

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = Base.metadata

# Override sqlalchemy.url with the app's sync URL
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.sync_database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
