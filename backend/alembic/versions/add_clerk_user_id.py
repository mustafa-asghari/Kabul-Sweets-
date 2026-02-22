"""Add clerk_user_id column and make hashed_password nullable

Revision ID: add_clerk_user_id
Revises: add_staff_role
Create Date: 2026-02-22

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_clerk_user_id'
down_revision = 'add_staff_role'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add clerk_user_id column
    op.add_column(
        'users',
        sa.Column('clerk_user_id', sa.String(255), nullable=True),
    )
    op.create_unique_constraint('uq_users_clerk_user_id', 'users', ['clerk_user_id'])
    op.create_index('ix_users_clerk_user_id', 'users', ['clerk_user_id'], unique=True)

    # Make hashed_password nullable (existing rows keep their values)
    op.alter_column('users', 'hashed_password', nullable=True)


def downgrade() -> None:
    # Restore hashed_password as non-nullable
    # NOTE: rows with NULL hashed_password must be removed first or given a placeholder
    op.execute("UPDATE users SET hashed_password = '' WHERE hashed_password IS NULL")
    op.alter_column('users', 'hashed_password', nullable=False)

    op.drop_index('ix_users_clerk_user_id', table_name='users')
    op.drop_constraint('uq_users_clerk_user_id', 'users', type_='unique')
    op.drop_column('users', 'clerk_user_id')
