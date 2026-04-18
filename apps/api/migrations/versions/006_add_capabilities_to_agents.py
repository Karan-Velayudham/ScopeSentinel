"""Add capabilities JSON column to agents table

Revision ID: 006_add_capabilities_to_agents
Revises: 4914389497a3
Create Date: 2026-04-19
"""
from alembic import op
import sqlalchemy as sa

revision = "006_add_capabilities_to_agents"
down_revision = "4914389497a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("capabilities", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agents", "capabilities")
