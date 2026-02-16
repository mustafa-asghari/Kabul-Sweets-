"""Add staff role to user enum

Revision ID: add_staff_role
Revises: 
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_staff_role'
down_revision = None  # Update this with the actual previous revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'staff' to the UserRole enum
    # PostgreSQL enum modification
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'staff'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # You would need to recreate the enum type if you want to remove 'staff'
    # For safety, we're leaving this as a no-op
    pass
