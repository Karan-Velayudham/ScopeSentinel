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

from sqlalchemy import DateTime, Enum, JSON, String
from sqlmodel import Field, Relationship, SQLModel, Column


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
    ADMIN = "ADMIN"
    DEVELOPER = "DEVELOPER"
    REVIEWER = "REVIEWER"
    VIEWER = "VIEWER"


class MemoryMode(str, enum.Enum):
    SESSION = "session"
    LONG_TERM = "long_term"


class RunEventType(str, enum.Enum):
    THOUGHT = "thought"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    LOG = "log"
    FINISH = "finish"


class TenantStatus(str, enum.Enum):
    PROVISIONING = "PROVISIONING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DEPROVISIONED = "DEPROVISIONED"


class TriggerType(str, enum.Enum):
    SCHEDULE = "schedule"   # Recurring cron expression
    ONE_TIME = "one_time"   # Fire once at a specific datetime
    EVENT = "event"         # Fire on matching Redpanda event (Jira, Slack, Teams, etc.)


class AgentStatus(str, enum.Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    ARCHIVED = "archived"


class AgentRunStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRunTriggeredBy(str, enum.Enum):
    MANUAL = "manual"
    WORKFLOW = "workflow"
    TRIGGER = "trigger"


class MessageRole(str, enum.Enum):
    USER = "user"
    AGENT = "agent"


class MessageType(str, enum.Enum):
    TEXT = "text"
    STRUCTURED = "structured"


# ---------------------------------------------------------------------------
# Organisation
# ---------------------------------------------------------------------------

class Org(SQLModel, table=True):
    __tablename__ = "orgs"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    name: str = Field(index=True, unique=True)
    slug: str = Field(index=True, unique=True)
    status: TenantStatus = Field(default=TenantStatus.PROVISIONING, index=True)
    tenant_config: Optional[str] = Field(default=None) # JSON string
    created_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))

    # Relationships
    users: list["User"] = Relationship(back_populates="org")
    runs: list["WorkflowRun"] = Relationship(back_populates="org")
    workflows: list["Workflow"] = Relationship(back_populates="org")
    agents: list["Agent"] = Relationship(back_populates="org")
    installed_connectors: list["InstalledConnector"] = Relationship(back_populates="org")
    oauth_connections: list["OAuthConnection"] = Relationship(back_populates="org")
    trigger_definitions: list["TriggerDefinition"] = Relationship(back_populates="org")
    chat_sessions: list["ChatSession"] = Relationship(back_populates="org")


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

class Workflow(SQLModel, table=True):
    __tablename__ = "workflows"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    org_id: str = Field(foreign_key="orgs.id", index=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    version: int = Field(default=1)
    status: str = Field(default="draft", index=True)  # draft | active | paused | archived
    yaml_content: str = Field(default="")
    created_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))

    # Relationships
    runs: list["WorkflowRun"] = Relationship(back_populates="workflow")
    org: Optional[Org] = Relationship(back_populates="workflows")


# ---------------------------------------------------------------------------
# Skill (Phase 1)
# ---------------------------------------------------------------------------

class AgentSkillLink(SQLModel, table=True):
    __tablename__ = "agent_skill_links"
    agent_id: str = Field(foreign_key="agents.id", primary_key=True)
    skill_id: str = Field(foreign_key="skills.id", primary_key=True)


class AgentAppConnectionLink(SQLModel, table=True):
    __tablename__ = "agent_app_connections"
    agent_id: str = Field(foreign_key="agents.id", primary_key=True)
    connection_id: str = Field(foreign_key="oauth_connections.id", primary_key=True)


class Skill(SQLModel, table=True):
    __tablename__ = "skills"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    org_id: str = Field(foreign_key="orgs.id", index=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    instructions: str = Field(description="The instructional text injected into the agent system prompt")
    version: int = Field(default=1)
    is_active: bool = Field(default=True, index=True)
    
    created_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))

    # Relationships
    agents: list["Agent"] = Relationship(back_populates="skills", link_model=AgentSkillLink)


# ---------------------------------------------------------------------------
# Agent (Epic 3.4)
# ---------------------------------------------------------------------------

class Agent(SQLModel, table=True):
    __tablename__ = "agents"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    org_id: str = Field(foreign_key="orgs.id", index=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    instructions: str = Field(description="The system prompt/instructions of the agent")
    model: str = Field(default="gpt-4o")
    timeout_seconds: int = Field(default=60)
    capabilities: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True)
    )
    status: AgentStatus = Field(
        default=AgentStatus.ACTIVE,
        sa_type=Enum(AgentStatus, native_enum=False),
        index=True
    )

    created_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))

    # Relationships
    org: Optional[Org] = Relationship(back_populates="agents")
    runs: list["WorkflowRun"] = Relationship(back_populates="agent")
    agent_runs: list["AgentRun"] = Relationship(back_populates="agent")
    skills: list[Skill] = Relationship(back_populates="agents", link_model=AgentSkillLink)
    app_connections: list["OAuthConnection"] = Relationship(back_populates="agents", link_model=AgentAppConnectionLink)
    chat_sessions: list["ChatSession"] = Relationship(back_populates="agent")


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
    created_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))

    # Relationships
    org: Optional[Org] = Relationship(back_populates="users")
    hitl_decisions: list["HitlEvent"] = Relationship(back_populates="decided_by_user")
    oauth_connections: list["OAuthConnection"] = Relationship(back_populates="user")

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
    agent_id: Optional[str] = Field(default=None, foreign_key="agents.id", index=True)
    
    ticket_id: Optional[str] = Field(default=None, index=True)
    inputs_json: Optional[str] = Field(default=None)
    output_json: Optional[str] = Field(default=None)
    
    status: RunStatus = Field(
        default=RunStatus.PENDING,
        index=True,
        sa_type=Enum(RunStatus, native_enum=False)
    )
    
    trigger_type: str = Field(default="manual", index=True) # manual | webhook | schedule | event
    temporal_workflow_id: Optional[str] = Field(default=None, index=True)
    
    dry_run: bool = Field(default=False)
    # JSON-encoded PlannerOutput (set after planning step completes)
    plan_json: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))

    # Token usage (Phase 4)
    total_tokens: Optional[int] = Field(default=None)
    prompt_tokens: Optional[int] = Field(default=None)
    completion_tokens: Optional[int] = Field(default=None)
    estimated_cost: Optional[float] = Field(default=None)

    # Relationships
    org: Optional[Org] = Relationship(back_populates="runs")
    workflow: Optional[Workflow] = Relationship(back_populates="runs")
    agent: Optional[Agent] = Relationship(back_populates="runs")
    steps: list["RunStep"] = Relationship(back_populates="run")
    events: list["RunEvent"] = Relationship(back_populates="run")
    hitl_events: list["HitlEvent"] = Relationship(back_populates="run")


# ---------------------------------------------------------------------------
# Run Step
# ---------------------------------------------------------------------------

class RunStep(SQLModel, table=True):
    __tablename__ = "run_steps"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    run_id: str = Field(foreign_key="workflow_runs.id", index=True)
    step_name: str  # e.g. "fetch_ticket", "plan", "hitl", "code", "git_push"
    status: StepStatus = Field(
        default=StepStatus.PENDING,
        index=True,
        sa_type=Enum(StepStatus, native_enum=False)
    )
    # Arbitrary JSON blobs for traceability
    input_json: Optional[str] = Field(default=None)
    output_json: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    started_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    finished_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))

    # Token usage (Phase 4)
    total_tokens: Optional[int] = Field(default=None)
    prompt_tokens: Optional[int] = Field(default=None)
    completion_tokens: Optional[int] = Field(default=None)
    estimated_cost: Optional[float] = Field(default=None)

    # Relationship
    run: Optional[WorkflowRun] = Relationship(back_populates="steps")


# ---------------------------------------------------------------------------
# HITL Event
# ---------------------------------------------------------------------------

class HitlEvent(SQLModel, table=True):
    __tablename__ = "hitl_events"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    run_id: str = Field(foreign_key="workflow_runs.id", index=True)
    action: HitlAction = Field(sa_type=Enum(HitlAction, native_enum=False))
    feedback: Optional[str] = Field(default=None)
    # Who made the decision (NULL = anonymous / pre-auth)
    decided_by_id: Optional[str] = Field(default=None, foreign_key="users.id")
    decided_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))

    # Relationships
    run: Optional[WorkflowRun] = Relationship(back_populates="hitl_events")
    decided_by_user: Optional[User] = Relationship(back_populates="hitl_decisions")


# ---------------------------------------------------------------------------
# Run Event (Phase 1)
# ---------------------------------------------------------------------------

class RunEvent(SQLModel, table=True):
    __tablename__ = "run_events"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    run_id: str = Field(foreign_key="workflow_runs.id", index=True)
    event_type: RunEventType = Field(sa_type=Enum(RunEventType, native_enum=False))
    # Arbitrary JSON data related to the event (thought text, tool call args, tool output)
    payload_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))

    # Relationship
    run: Optional[WorkflowRun] = Relationship(back_populates="events")


# ---------------------------------------------------------------------------
# Installed Connector
# ---------------------------------------------------------------------------

class InstalledConnector(SQLModel, table=True):
    __tablename__ = "installed_connectors"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    org_id: str = Field(foreign_key="orgs.id", index=True)
    connector_id: str = Field(index=True)
    config_json: str = Field(default="{}")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))

    # Relationship
    org: Optional[Org] = Relationship(back_populates="installed_connectors")


# ---------------------------------------------------------------------------
# OAuth Connection
# ---------------------------------------------------------------------------

class OAuthConnection(SQLModel, table=True):
    __tablename__ = "oauth_connections"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    org_id: str = Field(foreign_key="orgs.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    provider: str = Field(index=True)
    access_token_encrypted: str
    refresh_token_encrypted: str
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))
    scopes: str = Field(default="[]", description="JSON-encoded list of scopes")
    provider_metadata: str = Field(default="{}", description="JSON-encoded provider-specific metadata (e.g., cloud_id)")
    created_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))

    # Relationships
    org: Optional[Org] = Relationship(back_populates="oauth_connections")
    user: Optional[User] = Relationship(back_populates="oauth_connections")
    agents: list["Agent"] = Relationship(back_populates="app_connections", link_model=AgentAppConnectionLink)


# ---------------------------------------------------------------------------
# Trigger Definition (Trigger Engine)
# ---------------------------------------------------------------------------

class TriggerDefinition(SQLModel, table=True):
    """
    Persisted trigger rule created by a user.

    trigger_type governs which source in the Trigger Engine handles this trigger:
      - schedule  → cron.py (recurring, APScheduler)
      - one_time  → one_time.py (fires once at run_at datetime, then deactivates)
      - event     → redpanda.py (matches incoming events by event_filter_json)
    """
    __tablename__ = "trigger_definitions"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    org_id: str = Field(foreign_key="orgs.id", index=True)
    agent_id: str = Field(foreign_key="agents.id", index=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True, index=True)

    trigger_type: TriggerType = Field(
        sa_type=Enum(TriggerType, native_enum=False),
        index=True,
    )

    # --- Schedule (trigger_type = "schedule") ---
    # Standard cron expression, e.g. "0 9 * * 1-5" = 9am weekdays
    cron_expr: Optional[str] = Field(default=None)

    # --- One-time (trigger_type = "one_time") ---
    # UTC datetime to fire the run. Engine deactivates this trigger after firing.
    run_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))

    # --- Event (trigger_type = "event") ---
    # JSON object with keys to match against incoming Redpanda events.
    # e.g. {"source": "jira", "event_type": "jira:issue_created"}
    # Future: {"source": "slack", "event_type": "app_mention"}
    event_filter_json: Optional[str] = Field(default=None)

    # Static inputs passed to the run (JSON). Merged with event-extracted data.
    inputs_json: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))

    # Relationships
    org: Optional[Org] = Relationship(back_populates="trigger_definitions")
    agent: Optional["Agent"] = Relationship()


# ---------------------------------------------------------------------------
# Agent Run
# ---------------------------------------------------------------------------

class AgentRun(SQLModel, table=True):
    __tablename__ = "agent_runs"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    org_id: str = Field(foreign_key="orgs.id", index=True)
    agent_id: str = Field(foreign_key="agents.id", index=True)
    
    triggered_by: AgentRunTriggeredBy = Field(sa_type=Enum(AgentRunTriggeredBy, native_enum=False))
    source_id: Optional[str] = Field(default=None) # workflow_run_id or trigger_id (nullable)
    skill_ids: Optional[str] = Field(default=None, description="JSON array of skill IDs")
    
    input_json: str = Field(default="{}")
    prompt_used: Optional[str] = Field(default=None)
    output: Optional[str] = Field(default=None)
    
    status: AgentRunStatus = Field(
        default=AgentRunStatus.RUNNING,
        sa_type=Enum(AgentRunStatus, native_enum=False),
        index=True
    )
    error_message: Optional[str] = Field(default=None)
    
    started_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))
    completed_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))

    # Relationships
    agent: Optional[Agent] = Relationship(back_populates="agent_runs")


# ---------------------------------------------------------------------------
# AI Agent Chat Interface
# ---------------------------------------------------------------------------

class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_sessions"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    org_id: str = Field(foreign_key="orgs.id", index=True)
    agent_id: str = Field(foreign_key="agents.id", index=True)
    title: str = Field(index=True)
    
    created_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))

    # Relationships
    org: Optional[Org] = Relationship(back_populates="chat_sessions")
    agent: Optional["Agent"] = Relationship(back_populates="chat_sessions")
    messages: list["ChatMessage"] = Relationship(back_populates="session")
    files: list["GeneratedFile"] = Relationship(back_populates="session")


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    org_id: str = Field(foreign_key="orgs.id", index=True)
    chat_session_id: str = Field(foreign_key="chat_sessions.id", index=True)
    role: MessageRole = Field(sa_type=Enum(MessageRole, native_enum=False))
    content: str
    message_type: MessageType = Field(default=MessageType.TEXT, sa_type=Enum(MessageType, native_enum=False))
    
    created_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))

    # Relationships
    session: Optional[ChatSession] = Relationship(back_populates="messages")
    generated_files: list["GeneratedFile"] = Relationship(back_populates="message")


class GeneratedFile(SQLModel, table=True):
    __tablename__ = "generated_files"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    org_id: str = Field(foreign_key="orgs.id", index=True)
    chat_session_id: str = Field(foreign_key="chat_sessions.id", index=True)
    message_id: Optional[str] = Field(default=None, foreign_key="chat_messages.id", index=True)
    
    filename: str
    content: str
    file_type: str = Field(default="text/markdown")
    
    created_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))

    # Relationships
    session: Optional[ChatSession] = Relationship(back_populates="files")
    message: Optional[ChatMessage] = Relationship(back_populates="generated_files")
