"""Add clerk_user_id column and make hashed_password nullable

Revision ID: add_clerk_user_id
Revises: add_staff_role
Create Date: 2026-02-22

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'add_clerk_user_id'
down_revision = 'add_staff_role'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use raw SQL with IF NOT EXISTS so this is safe on both:
    # - Existing databases (created via create_all, no clerk_user_id yet)
    # - Brand-new databases (create_all already added the column from the model)
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS clerk_user_id VARCHAR(255)
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_users_clerk_user_id
        ON users (clerk_user_id)
        WHERE clerk_user_id IS NOT NULL
    """)

    # DROP NOT NULL is idempotent — safe even if already nullable
    op.execute("""
        ALTER TABLE users
        ALTER COLUMN hashed_password DROP NOT NULL
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN hashed_password SET NOT NULL")
    op.execute("DROP INDEX IF EXISTS ix_users_clerk_user_id")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS clerk_user_id")
