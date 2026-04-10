"""Rename skills.content to instructions, add description column

Revision ID: 005
Revises: 004_add_trigger_definitions
Create Date: 2026-04-10
"""

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004_add_trigger_definitions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename content → instructions
    op.alter_column("skills", "content", new_column_name="instructions")

    # Add description column
    op.add_column("skills", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("skills", "description")
    op.alter_column("skills", "instructions", new_column_name="content")
