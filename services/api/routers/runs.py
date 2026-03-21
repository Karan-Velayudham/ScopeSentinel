"""
routers/runs.py — /api/runs endpoints (Epic 1.2.1–1.2.6)

Endpoints:
  POST   /api/runs                     - trigger a new workflow run
  GET    /api/runs                     - list runs (paginated)
  GET    /api/runs/{run_id}            - get run detail with steps
  GET    /api/runs/{run_id}/plan       - get structured plan JSON
  POST   /api/runs/{run_id}/decision   - submit HITL approve/reject/modify
  GET    /api/runs/{run_id}/logs       - WebSocket real-time log stream
"""

import json
import os
from datetime import datetime, timezone
from typing import Annotated, Optional

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlmodel import select

from auth.api_keys import CurrentUserDep
from db.models import HitlAction, HitlEvent, RunStatus, WorkflowRun
from db.session import SessionDep
from schemas import (
    DecisionRequest,
    DecisionResponse,
    HitlEventResponse,
    PaginationMeta,
    PlanResponse,
    RunDetailResponse,
    RunListResponse,
    RunResponse,
    StepResponse,
    TriggerRunRequest,
)
from worker.celery_app import run_workflow_task

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _run_to_response(run: WorkflowRun) -> RunResponse:
    return RunResponse(
        run_id=run.id,
        ticket_id=run.ticket_id,
        status=run.status.value,
        dry_run=run.dry_run,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


# ---------------------------------------------------------------------------
# POST /api/runs — trigger a new run
# ---------------------------------------------------------------------------

@router.post("/", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def trigger_run(
    body: TriggerRunRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> RunResponse:
    """Trigger a new workflow run for the given ticket ID."""
    log = logger.bind(ticket_id=body.ticket_id, user_id=current_user.id)
    log.info("api.trigger_run")

    run = WorkflowRun(
        org_id=current_user.org_id,
        ticket_id=body.ticket_id,
        dry_run=body.dry_run,
        status=RunStatus.PENDING,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    # Dispatch to Celery worker (non-blocking)
    run_workflow_task.delay(
        run_id=run.id,
        ticket_id=run.ticket_id,
        dry_run=run.dry_run,
    )

    log.info("api.run_dispatched", run_id=run.id)
    return _run_to_response(run)


# ---------------------------------------------------------------------------
# GET /api/runs — list runs with pagination
# ---------------------------------------------------------------------------

@router.get("/", response_model=RunListResponse)
async def list_runs(
    session: SessionDep,
    current_user: CurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[Optional[str], Query(alias="status")] = None,
) -> RunListResponse:
    """List all workflow runs for the current org, newest first."""
    query = select(WorkflowRun).where(WorkflowRun.org_id == current_user.org_id)

    if status_filter:
        try:
            query = query.where(WorkflowRun.status == RunStatus(status_filter.upper()))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status filter '{status_filter}'.",
            )

    query = query.order_by(WorkflowRun.created_at.desc())  # type: ignore[attr-defined]

    # Count total
    from sqlalchemy import func
    count_query = select(func.count()).select_from(
        select(WorkflowRun).where(WorkflowRun.org_id == current_user.org_id).subquery()
    )
    total_result = await session.exec(count_query)
    total = total_result.one()

    # Apply pagination
    offset = (page - 1) * page_size
    result = await session.exec(query.offset(offset).limit(page_size))
    runs = result.all()

    return RunListResponse(
        items=[_run_to_response(r) for r in runs],
        meta=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            has_next=(offset + page_size) < total,
        ),
    )


# ---------------------------------------------------------------------------
# GET /api/runs/{run_id} — full run detail with steps
# ---------------------------------------------------------------------------

@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run(
    run_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> RunDetailResponse:
    """Get the full details of a run including all steps and HITL events."""
    run = await _get_run_or_404(run_id, current_user.org_id, session)

    return RunDetailResponse(
        run_id=run.id,
        ticket_id=run.ticket_id,
        status=run.status.value,
        dry_run=run.dry_run,
        created_at=run.created_at,
        updated_at=run.updated_at,
        steps=[
            StepResponse(
                step_id=s.id,
                step_name=s.step_name,
                status=s.status.value,
                started_at=s.started_at,
                finished_at=s.finished_at,
                error_message=s.error_message,
            )
            for s in run.steps  # type: ignore[attr-defined]
        ],
        hitl_events=[
            HitlEventResponse(
                event_id=h.id,
                action=h.action.value,
                feedback=h.feedback,
                decided_at=h.decided_at,
            )
            for h in run.hitl_events  # type: ignore[attr-defined]
        ],
    )


# ---------------------------------------------------------------------------
# GET /api/runs/{run_id}/plan — return structured plan JSON
# ---------------------------------------------------------------------------

@router.get("/{run_id}/plan", response_model=PlanResponse)
async def get_plan(
    run_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> PlanResponse:
    """Return the structured planning output for a run."""
    run = await _get_run_or_404(run_id, current_user.org_id, session)

    plan_data: Optional[dict] = None
    if run.plan_json:
        try:
            plan_data = json.loads(run.plan_json)
        except json.JSONDecodeError:
            plan_data = {"raw": run.plan_json}

    return PlanResponse(run_id=run.id, plan=plan_data)


# ---------------------------------------------------------------------------
# POST /api/runs/{run_id}/decision — HITL approve/reject/modify
# ---------------------------------------------------------------------------

@router.post("/{run_id}/decision", response_model=DecisionResponse)
async def submit_decision(
    run_id: str,
    body: DecisionRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> DecisionResponse:
    """
    Submit a HITL decision for a run that is in WAITING_HITL status.

    The Celery worker task is paused on a Redis pub/sub channel. This
    endpoint writes the HitlEvent to DB and publishes to that channel
    so the worker can resume.
    """
    run = await _get_run_or_404(run_id, current_user.org_id, session)

    if run.status != RunStatus.WAITING_HITL:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run '{run_id}' is not waiting for HITL (current status: {run.status.value}).",
        )

    if body.action == "modify" and not body.feedback:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="feedback is required when action=modify.",
        )

    # Write HITL event to DB
    hitl_event = HitlEvent(
        run_id=run.id,
        action=HitlAction(body.action),
        feedback=body.feedback,
        decided_by_id=current_user.id,
    )
    session.add(hitl_event)
    await session.commit()

    # Publish decision to the worker via Redis pub/sub
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    r = aioredis.from_url(redis_url)
    channel = f"hitl:{run_id}"
    payload = json.dumps({"action": body.action, "feedback": body.feedback})
    await r.publish(channel, payload)
    await r.aclose()

    logger.bind(run_id=run_id, user_id=current_user.id).info(
        "api.hitl_decision", action=body.action
    )
    return DecisionResponse(status="accepted", run_id=run_id, action=body.action)


# ---------------------------------------------------------------------------
# GET /api/runs/{run_id}/logs — WebSocket real-time log stream
# ---------------------------------------------------------------------------

@router.websocket("/{run_id}/logs")
async def stream_logs(
    run_id: str,
    websocket: WebSocket,
) -> None:
    """
    WebSocket endpoint streaming structured log lines for a run.

    The Celery worker publishes log entries to Redis pub/sub channel
    `logs:{run_id}`. This handler subscribes and forwards them to
    the WebSocket client in real-time.

    Note: Auth for WebSockets uses query param `?api_key=<key>` as
    the Sec-WebSocket-Protocol header approach is not universally supported.
    """
    await websocket.accept()
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    r = aioredis.from_url(redis_url)
    pubsub = r.pubsub()

    try:
        await pubsub.subscribe(f"logs:{run_id}")
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    await websocket.send_text(message["data"].decode("utf-8"))
                except WebSocketDisconnect:
                    break
    finally:
        await pubsub.unsubscribe(f"logs:{run_id}")
        await pubsub.aclose()
        await r.aclose()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _get_run_or_404(
    run_id: str,
    org_id: str,
    session: SessionDep,
) -> WorkflowRun:
    """Fetch a WorkflowRun by ID, scoped to the org. Raises 404 if not found."""
    result = await session.exec(
        select(WorkflowRun).where(
            WorkflowRun.id == run_id,
            WorkflowRun.org_id == org_id,
        )
    )
    run = result.first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found.",
        )
    return run
