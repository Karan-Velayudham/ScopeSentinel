"""Add trigger_definitions table

Revision ID: 004_add_trigger_definitions
Revises: e42dc3df3b12
Create Date: 2026-04-09
"""

from alembic import op
import sqlalchemy as sa

revision = "004_add_trigger_definitions"
down_revision = "e42dc3df3b12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trigger_definitions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("agent_id", sa.String(), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("trigger_type", sa.String(), nullable=False),
        sa.Column("cron_expr", sa.String(), nullable=True),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_filter_json", sa.Text(), nullable=True),
        sa.Column("inputs_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_trigger_definitions_org_id", "trigger_definitions", ["org_id"])
    op.create_index("ix_trigger_definitions_agent_id", "trigger_definitions", ["agent_id"])
    op.create_index("ix_trigger_definitions_is_active", "trigger_definitions", ["is_active"])
    op.create_index("ix_trigger_definitions_trigger_type", "trigger_definitions", ["trigger_type"])
    op.create_index("ix_trigger_definitions_name", "trigger_definitions", ["name"])


def downgrade() -> None:
    op.drop_table("trigger_definitions")
