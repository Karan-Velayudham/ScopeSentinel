"""
schemas.py — Pydantic request/response models for the ScopeSentinel API (Epic 1.2)

All models use strict types; datetimes are always UTC-aware.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional, Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    has_next: bool


# ---------------------------------------------------------------------------
# Runs — Request bodies
# ---------------------------------------------------------------------------

class TriggerRunRequest(BaseModel):
    agent_id: Optional[str] = Field(
        default=None,
        description="ID of the agent to run (Phase 3+)",
    )
    ticket_id: Optional[str] = Field(
        default=None,
        description="Jira ticket ID to process (legacy Phase 1)",
    )
    workflow_id: Optional[str] = Field(
        default=None,
        description="ID of the visual workflow to run (Phase 2+)",
    )
    inputs: Optional[dict[str, Any]] = Field(
        default=None,
        description="Dynamic inputs matching the workflow's Input node schema",
    )
    dry_run: bool = Field(
        default=False,
        description="If true, run planner + HITL only; skip code generation and git push",
    )
    model: Optional[str] = Field(
        default="gpt-4o",
        description="LLM model to use for this run (passed to LiteLLM)",
    )


class DecisionRequest(BaseModel):
    action: Literal["approve", "reject", "modify"] = Field(
        description="HITL decision action"
    )
    feedback: Optional[str] = Field(
        default=None,
        description="Required when action=modify; ignored for approve/reject",
    )


# ---------------------------------------------------------------------------
# Runs — Response bodies
# ---------------------------------------------------------------------------

class RunResponse(BaseModel):
    """Compact run summary — used in list and POST response."""
    run_id: str
    workflow_id: Optional[str] = None
    ticket_id: Optional[str] = None
    status: str
    dry_run: bool
    created_at: datetime
    updated_at: datetime
    total_tokens: Optional[int] = 0
    estimated_cost: Optional[float] = 0.0


class StepResponse(BaseModel):
    step_id: str
    step_name: str
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None
    total_tokens: Optional[int] = 0
    estimated_cost: Optional[float] = 0.0


class HitlEventResponse(BaseModel):
    event_id: str
    action: str
    feedback: Optional[str] = None
    decided_at: datetime


class RunDetailResponse(BaseModel):
    """Full run with steps and events history."""
    run_id: str
    workflow_id: Optional[str] = None
    agent_id: Optional[str] = None
    ticket_id: Optional[str] = None
    status: str
    trigger_type: str = "manual"
    temporal_workflow_id: Optional[str] = None
    dry_run: bool
    created_at: datetime
    updated_at: datetime
    steps: list[StepResponse]
    events: list[RunEventResponse]
    hitl_events: list[HitlEventResponse]
    total_tokens: Optional[int] = 0
    prompt_tokens: Optional[int] = 0
    completion_tokens: Optional[int] = 0
    estimated_cost: Optional[float] = 0.0
    analysis_passed: Optional[bool] = None
    analysis_feedback: Optional[str] = None


class RunEventResponse(BaseModel):
    event_id: str
    event_type: str
    payload: dict[str, Any]
    created_at: datetime


class PlanResponse(BaseModel):
    """Structured plan JSON for a run."""
    run_id: str
    plan: Optional[dict] = Field(
        default=None,
        description="Parsed plan from the PlannerAgent; null if planning not yet complete",
    )


class RunListResponse(BaseModel):
    items: list[RunResponse]
    meta: PaginationMeta


class DecisionResponse(BaseModel):
    status: Literal["accepted"]
    run_id: str
    action: str


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    postgres: Literal["connected", "unreachable"]
    redis: Literal["connected", "unreachable"]
    version: str = "1.0.0"

# ---------------------------------------------------------------------------
# Workflows (Epic 3.3)
# ---------------------------------------------------------------------------

class WorkflowStepDSL(BaseModel):
    id: str = Field(description="Unique step ID within this workflow")
    type: str = Field(description="Step type: agent | tool | condition | hitl | delay | input | output | etc.")
    name: str
    agent_id: Optional[str] = Field(default=None, description="Reference to a custom agent")
    inputs: dict[str, Any] = Field(default_factory=dict)
    next: Optional[list[str]] = Field(default_factory=list, description="IDs of next steps")

class WorkflowDSL(BaseModel):
    name: str = Field(description="Name of the workflow")
    description: Optional[str] = None
    trigger: dict[str, Any] = Field(default_factory=dict, description="Trigger configuration")
    steps: list[WorkflowStepDSL] = Field(default_factory=list)

class WorkflowCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    yaml_content: str = Field(description="The YAML DSL content")

class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    yaml_content: Optional[str] = Field(None, description="The YAML DSL content")

class WorkflowResponse(BaseModel):
    id: str
    org_id: str
    name: str
    description: Optional[str]
    version: int
    status: str = "draft"  # draft | active | paused | archived
    yaml_content: str
    created_at: datetime
    updated_at: datetime

class WorkflowActivateResponse(BaseModel):
    id: str
    status: str

class WorkflowListResponse(BaseModel):
    items: list[WorkflowResponse]
    meta: PaginationMeta

# ---------------------------------------------------------------------------
# Connector DSL & APIs
# ---------------------------------------------------------------------------

class ConnectorInfo(BaseModel):
    id: str
    name: str
    description: str
    category: str
    icon_url: str
    auth_type: str = "none"  # "oauth" | "api_key" | "none"

class ConnectorTool(BaseModel):
    name: str
    description: str
    inputs: list[dict[str, Any]] = Field(default_factory=list)

class ConnectorInfoExtended(ConnectorInfo):
    tools: list[ConnectorTool] = Field(default_factory=list)
    oauth_scopes: list[str] = Field(default_factory=list)
    api_key_fields: list[dict[str, Any]] = Field(default_factory=list)

class ConnectorInstallRequest(BaseModel):
    config: dict[str, Any]

class InstalledConnectorResponse(BaseModel):
    id: str
    connector_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

class InstalledConnectorDetailResponse(BaseModel):
    id: str
    connector_id: str
    connector_name: str
    icon_url: str
    auth_type: str
    is_active: bool
    tools: list[ConnectorTool] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

class OAuthInitResponse(BaseModel):
    authorization_url: str
    state: str
    connector_id: str

class OAuthConnectionCreate(BaseModel):
    provider: str
    access_token: str
    refresh_token: str
    expires_at: datetime
    scopes: str = "[]"
    provider_metadata: str = "{}"

class OAuthConnectionResponse(BaseModel):
    id: str
    org_id: str
    user_id: str
    provider: str
    expires_at: datetime
    scopes: str
    provider_metadata: str
    created_at: datetime
    updated_at: datetime

class DashboardStatsResponse(BaseModel):
    active_runs: int
    workflows_executed: int
    pending_hitl: int
    success_rate: float


# ---------------------------------------------------------------------------
# Agents (Epic 3.4)
# ---------------------------------------------------------------------------

class AgentCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    identity: str
    model: str = "gpt-4o"
    tools: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    max_iterations: int = 10
    memory_mode: Literal["session", "long_term"] = "session"

class AgentUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    identity: Optional[str] = None
    model: Optional[str] = None
    tools: Optional[list[str]] = None
    skills: Optional[list[str]] = None
    max_iterations: Optional[int] = None
    memory_mode: Optional[Literal["session", "long_term"]] = None
    is_active: Optional[bool] = None

class AgentResponse(BaseModel):
    id: str
    org_id: str
    name: str
    description: Optional[str]
    identity: str
    model: str
    tools: list[str]
    skills: list[str] = Field(default_factory=list)
    max_iterations: int
    memory_mode: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

class AgentListResponse(BaseModel):
    items: list[AgentResponse]
    meta: PaginationMeta


# ---------------------------------------------------------------------------
# Skills (Phase 1)
# ---------------------------------------------------------------------------

class SkillCreateRequest(BaseModel):
    name: str
    content: str
    is_active: bool = True

class SkillUpdateRequest(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None

class SkillResponse(BaseModel):
    id: str
    org_id: str
    name: str
    content: str
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

class SkillListResponse(BaseModel):
    items: list[SkillResponse]
    meta: PaginationMeta


# ---------------------------------------------------------------------------
# Trigger Definitions
# ---------------------------------------------------------------------------

class TriggerCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    agent_id: str = Field(description="Agent to invoke when this trigger fires")
    trigger_type: Literal["schedule", "one_time", "event"]
    # For schedule triggers
    cron_expr: Optional[str] = Field(
        default=None,
        description="Standard cron expression, e.g. '0 9 * * 1-5'",
        examples=["0 9 * * 1-5"]
    )
    # For one_time triggers
    run_at: Optional[datetime] = Field(
        default=None,
        description="UTC datetime to fire the run (one_time only)"
    )
    # For event triggers
    event_filter: Optional[dict] = Field(
        default=None,
        description="Key/value pairs to match against incoming events, e.g. {\"source\": \"jira\", \"event_type\": \"jira:issue_created\"}"
    )
    inputs: Optional[dict] = Field(
        default=None,
        description="Static inputs to pass to the run"
    )


class TriggerUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    cron_expr: Optional[str] = None
    run_at: Optional[datetime] = None
    event_filter: Optional[dict] = None
    inputs: Optional[dict] = None


class TriggerResponse(BaseModel):
    id: str
    org_id: str
    agent_id: str
    name: str
    description: Optional[str]
    is_active: bool
    trigger_type: str
    cron_expr: Optional[str]
    run_at: Optional[datetime]
    event_filter: Optional[dict]
    inputs: Optional[dict]
    created_at: datetime
    updated_at: datetime


class TriggerListResponse(BaseModel):
    items: list[TriggerResponse]
    meta: PaginationMeta
