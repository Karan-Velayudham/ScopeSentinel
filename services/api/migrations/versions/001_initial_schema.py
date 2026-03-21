"""Initial schema — Phase 1 (Epic 1.1.1)

Revision ID: 001
Create Date: 2026-03-21
"""

from alembic import op
import sqlalchemy as sa
import sqlmodel

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # orgs
    op.create_table(
        "orgs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_orgs_name", "orgs", ["name"], unique=True)
    op.create_index("ix_orgs_slug", "orgs", ["slug"], unique=True)

    # users
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="developer"),
        sa.Column("hashed_api_key", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_hashed_api_key", "users", ["hashed_api_key"])

    # workflow_runs
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("ticket_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("plan_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workflow_runs_org_id", "workflow_runs", ["org_id"])
    op.create_index("ix_workflow_runs_ticket_id", "workflow_runs", ["ticket_id"])
    op.create_index("ix_workflow_runs_status", "workflow_runs", ["status"])

    # run_steps
    op.create_table(
        "run_steps",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("workflow_runs.id"), nullable=False),
        sa.Column("step_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("input_json", sa.Text(), nullable=True),
        sa.Column("output_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_run_steps_run_id", "run_steps", ["run_id"])
    op.create_index("ix_run_steps_status", "run_steps", ["status"])

    # hitl_events
    op.create_table(
        "hitl_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("workflow_runs.id"), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("decided_by_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_hitl_events_run_id", "hitl_events", ["run_id"])


def downgrade() -> None:
    op.drop_table("hitl_events")
    op.drop_table("run_steps")
    op.drop_table("workflow_runs")
    op.drop_table("users")
    op.drop_table("orgs")
