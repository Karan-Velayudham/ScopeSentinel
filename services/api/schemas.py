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
    ticket_id: str = Field(
        description="Jira ticket ID to process (e.g. SCRUM-8)",
        examples=["SCRUM-8"],
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
    ticket_id: str
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
    """Full run with steps and HITL history."""
    run_id: str
    workflow_id: Optional[str] = None
    ticket_id: str
    status: str
    dry_run: bool
    created_at: datetime
    updated_at: datetime
    steps: list[StepResponse]
    hitl_events: list[HitlEventResponse]
    total_tokens: Optional[int] = 0
    prompt_tokens: Optional[int] = 0
    completion_tokens: Optional[int] = 0
    estimated_cost: Optional[float] = 0.0
    analysis_passed: Optional[bool] = None
    analysis_feedback: Optional[str] = None


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
    type: Literal["trigger", "agent", "tool", "condition", "hitl", "delay"]
    name: str
    agent_id: Optional[str] = Field(default=None, description="Reference to a custom agent")
    inputs: dict[str, Any] = Field(default_factory=dict)
    next: Optional[list[str]] = Field(default_factory=list, description="IDs of next steps")

class WorkflowDSL(BaseModel):
    name: str = Field(description="Name of the workflow")
    description: Optional[str] = None
    trigger: dict[str, Any] = Field(description="Trigger configuration")
    steps: list[WorkflowStepDSL]

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

class AgentUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    identity: Optional[str] = None
    model: Optional[str] = None
    tools: Optional[list[str]] = None

class AgentResponse(BaseModel):
    id: str
    org_id: str
    name: str
    description: Optional[str]
    identity: str
    model: str
    tools: list[str]
    created_at: datetime
    updated_at: datetime

class AgentListResponse(BaseModel):
    items: list[AgentResponse]
    meta: PaginationMeta
