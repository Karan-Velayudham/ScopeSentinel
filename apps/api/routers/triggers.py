"""
routers/triggers.py — /api/triggers CRUD endpoints

Manages TriggerDefinition records. These are consumed by the Trigger Engine
to schedule cron jobs, one-time runs, or match inbound events.

Endpoints:
  GET    /api/triggers/         - list triggers (paginated)
  POST   /api/triggers/         - create a trigger
  GET    /api/triggers/{id}     - get trigger details
  PATCH  /api/triggers/{id}     - update / enable / disable
  DELETE /api/triggers/{id}     - delete
"""

import json
from datetime import datetime, timezone
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlmodel import select

from auth.api_keys import CurrentUserDep
from db.models import TriggerDefinition, TriggerType
from db.session import TenantSessionDep
from schemas import (
    PaginationMeta,
    TriggerCreateRequest,
    TriggerListResponse,
    TriggerResponse,
    TriggerUpdateRequest,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/triggers", tags=["triggers"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_response(t: TriggerDefinition) -> TriggerResponse:
    event_filter = None
    if t.event_filter_json:
        try:
            event_filter = json.loads(t.event_filter_json)
        except Exception:
            event_filter = None

    inputs = None
    if t.inputs_json:
        try:
            inputs = json.loads(t.inputs_json)
        except Exception:
            inputs = None

    return TriggerResponse(
        id=t.id,
        org_id=t.org_id,
        agent_id=t.agent_id,
        name=t.name,
        description=t.description,
        is_active=t.is_active,
        trigger_type=t.trigger_type.value,
        cron_expr=t.cron_expr,
        run_at=t.run_at,
        event_filter=event_filter,
        inputs=inputs,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


# ---------------------------------------------------------------------------
# GET /api/triggers/ — list
# ---------------------------------------------------------------------------

@router.get("/", response_model=TriggerListResponse)
async def list_triggers(
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    active_only: bool = True,
) -> TriggerListResponse:
    """List trigger definitions for the current org."""
    from sqlalchemy import func

    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    query = select(TriggerDefinition).where(TriggerDefinition.org_id == org_id)
    if active_only:
        query = query.where(TriggerDefinition.is_active == True)  # noqa: E712

    query = query.order_by(TriggerDefinition.created_at.desc())  # type: ignore[attr-defined]

    count_q = select(func.count()).select_from(
        select(TriggerDefinition).where(TriggerDefinition.org_id == org_id).subquery()
    )
    total = (await session.exec(count_q)).one()

    offset = (page - 1) * page_size
    result = await session.exec(query.offset(offset).limit(page_size))
    items = result.all()

    return TriggerListResponse(
        items=[_to_response(t) for t in items],
        meta=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            has_next=(offset + page_size) < total,
        ),
    )


# ---------------------------------------------------------------------------
# POST /api/triggers/ — create
# ---------------------------------------------------------------------------

@router.post("/", response_model=TriggerResponse, status_code=status.HTTP_201_CREATED)
async def create_trigger(
    body: TriggerCreateRequest,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> TriggerResponse:
    """Create a new trigger definition."""
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    log = logger.bind(org_id=org_id, trigger_type=body.trigger_type)

    # Validate trigger-type-specific fields
    if body.trigger_type == "schedule" and not body.cron_expr:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="cron_expr is required for 'schedule' triggers.",
        )
    if body.trigger_type == "one_time" and not body.run_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="run_at is required for 'one_time' triggers.",
        )
    if body.trigger_type == "event" and not body.event_filter:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="event_filter is required for 'event' triggers.",
        )

    trigger = TriggerDefinition(
        org_id=org_id,
        agent_id=body.agent_id,
        name=body.name,
        description=body.description,
        trigger_type=TriggerType(body.trigger_type),
        cron_expr=body.cron_expr,
        run_at=body.run_at,
        event_filter_json=json.dumps(body.event_filter) if body.event_filter else None,
        inputs_json=json.dumps(body.inputs) if body.inputs else None,
        is_active=True,
    )
    session.add(trigger)
    await session.commit()
    await session.refresh(trigger)

    log.info("triggers.created", trigger_id=trigger.id)
    return _to_response(trigger)


# ---------------------------------------------------------------------------
# GET /api/triggers/{id} — detail
# ---------------------------------------------------------------------------

@router.get("/{trigger_id}", response_model=TriggerResponse)
async def get_trigger(
    trigger_id: str,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> TriggerResponse:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    t = await _get_or_404(trigger_id, org_id, session)
    return _to_response(t)


# ---------------------------------------------------------------------------
# PATCH /api/triggers/{id} — update / enable / disable
# ---------------------------------------------------------------------------

@router.patch("/{trigger_id}", response_model=TriggerResponse)
async def update_trigger(
    trigger_id: str,
    body: TriggerUpdateRequest,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> TriggerResponse:
    """Update a trigger. Pass is_active=false to disable."""
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    t = await _get_or_404(trigger_id, org_id, session)

    if body.name is not None:
        t.name = body.name
    if body.description is not None:
        t.description = body.description
    if body.is_active is not None:
        t.is_active = body.is_active
    if body.cron_expr is not None:
        t.cron_expr = body.cron_expr
    if body.run_at is not None:
        t.run_at = body.run_at
    if body.event_filter is not None:
        t.event_filter_json = json.dumps(body.event_filter)
    if body.inputs is not None:
        t.inputs_json = json.dumps(body.inputs)

    t.updated_at = _utcnow()
    session.add(t)
    await session.commit()
    await session.refresh(t)

    logger.bind(org_id=org_id).info("triggers.updated", trigger_id=t.id)
    return _to_response(t)


# ---------------------------------------------------------------------------
# DELETE /api/triggers/{id}
# ---------------------------------------------------------------------------

@router.delete("/{trigger_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trigger(
    trigger_id: str,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> None:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    t = await _get_or_404(trigger_id, org_id, session)
    await session.delete(t)
    await session.commit()
    logger.bind(org_id=org_id).info("triggers.deleted", trigger_id=trigger_id)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _get_or_404(trigger_id: str, org_id: str, session: TenantSessionDep) -> TriggerDefinition:
    result = await session.exec(
        select(TriggerDefinition).where(
            TriggerDefinition.id == trigger_id,
            TriggerDefinition.org_id == org_id,
        )
    )
    t = result.first()
    if not t:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trigger '{trigger_id}' not found.",
        )
    return t
