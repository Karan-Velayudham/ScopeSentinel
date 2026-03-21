"""
db/models.py — SQLModel table definitions for ScopeSentinel (Epic 1.1.1)

Tables:
  - Org             — organisation record
  - User            — users; support API-key auth and JWT (Keycloak) auth
  - WorkflowRun     — a single agent-runtime run, one ticket → one run
  - RunStep         — individual step within a run (plan, code, git, …)
  - HitlEvent       — human-in-the-loop decision log
"""

import enum
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_HITL = "WAITING_HITL"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


class StepStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class HitlAction(str, enum.Enum):
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


# ---------------------------------------------------------------------------
# Organisation
# ---------------------------------------------------------------------------

class Org(SQLModel, table=True):
    __tablename__ = "orgs"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    name: str = Field(index=True, unique=True)
    slug: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=_utcnow)

    # Relationships
    users: list["User"] = Relationship(back_populates="org")
    runs: list["WorkflowRun"] = Relationship(back_populates="org")
    workflows: list["Workflow"] = Relationship(back_populates="org")


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

class Workflow(SQLModel, table=True):
    __tablename__ = "workflows"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    org_id: str = Field(foreign_key="orgs.id", index=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    # Relationships
    runs: list["WorkflowRun"] = Relationship(back_populates="workflow")
    org: Optional[Org] = Relationship(back_populates="workflows")


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    org_id: str = Field(foreign_key="orgs.id", index=True)
    email: str = Field(index=True, unique=True)
    role: UserRole = Field(default=UserRole.DEVELOPER)
    # SHA-256 hex of the raw API key. NULL means JWT-only user.
    hashed_api_key: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=_utcnow)

    # Relationships
    org: Optional[Org] = Relationship(back_populates="users")
    hitl_decisions: list["HitlEvent"] = Relationship(back_populates="decided_by_user")

    @staticmethod
    def hash_api_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Workflow Run
# ---------------------------------------------------------------------------

class WorkflowRun(SQLModel, table=True):
    __tablename__ = "workflow_runs"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    org_id: str = Field(foreign_key="orgs.id", index=True)
    workflow_id: Optional[str] = Field(default=None, foreign_key="workflows.id", index=True)
    ticket_id: str = Field(index=True)
    status: RunStatus = Field(default=RunStatus.PENDING, index=True)
    dry_run: bool = Field(default=False)
    # JSON-encoded PlannerOutput (set after planning step completes)
    plan_json: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    # Relationships
    org: Optional[Org] = Relationship(back_populates="runs")
    workflow: Optional[Workflow] = Relationship(back_populates="runs")
    steps: list["RunStep"] = Relationship(back_populates="run")
    hitl_events: list["HitlEvent"] = Relationship(back_populates="run")


# ---------------------------------------------------------------------------
# Run Step
# ---------------------------------------------------------------------------

class RunStep(SQLModel, table=True):
    __tablename__ = "run_steps"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    run_id: str = Field(foreign_key="workflow_runs.id", index=True)
    step_name: str  # e.g. "fetch_ticket", "plan", "hitl", "code", "git_push"
    status: StepStatus = Field(default=StepStatus.PENDING, index=True)
    # Arbitrary JSON blobs for traceability
    input_json: Optional[str] = Field(default=None)
    output_json: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    started_at: Optional[datetime] = Field(default=None)
    finished_at: Optional[datetime] = Field(default=None)

    # Relationship
    run: Optional[WorkflowRun] = Relationship(back_populates="steps")


# ---------------------------------------------------------------------------
# HITL Event
# ---------------------------------------------------------------------------

class HitlEvent(SQLModel, table=True):
    __tablename__ = "hitl_events"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    run_id: str = Field(foreign_key="workflow_runs.id", index=True)
    action: HitlAction
    feedback: Optional[str] = Field(default=None)
    # Who made the decision (NULL = anonymous / pre-auth)
    decided_by_id: Optional[str] = Field(default=None, foreign_key="users.id")
    decided_at: datetime = Field(default_factory=_utcnow)

    # Relationships
    run: Optional[WorkflowRun] = Relationship(back_populates="hitl_events")
    decided_by_user: Optional[User] = Relationship(back_populates="hitl_decisions")
