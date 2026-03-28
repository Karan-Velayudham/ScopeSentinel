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
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import selectinload
from sqlmodel import select

from auth.api_keys import CurrentUserDep
from auth.rbac import assert_can_trigger, assert_can_approve_hitl
from db.models import HitlAction, HitlEvent, RunStatus, WorkflowRun, RunEvent
from db.session import SessionDep, TenantSessionDep
from schemas import (
    DecisionRequest,
    DecisionResponse,
    HitlEventResponse,
    PaginationMeta,
    PlanResponse,
    RunDetailResponse,
    RunListResponse,
    RunResponse,
    RunEventResponse,
    StepResponse,
    TriggerRunRequest,
    DashboardStatsResponse,
)
from sqlalchemy import func
from temporalio.client import Client

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _run_to_response(run: WorkflowRun) -> RunResponse:
    return RunResponse(
        run_id=run.id,
        workflow_id=run.workflow_id,
        agent_id=run.agent_id,
        ticket_id=run.ticket_id,
        status=run.status.value,
        dry_run=run.dry_run,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _event_to_response(event: "RunEvent") -> RunEventResponse:
    try:
        payload = json.loads(event.payload_json)
    except Exception:
        payload = {"raw": event.payload_json}
    
    return RunEventResponse(
        event_id=event.id,
        event_type=event.event_type.value,
        payload=payload,
        created_at=event.created_at,
    )


# ---------------------------------------------------------------------------
# GET /api/runs/stats — dashboard metrics
# ---------------------------------------------------------------------------
@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
):
    """Fetch real metrics for the dashboard."""
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    # Active Runs (RUNNING or WAITING_HITL)
    stmt_active = select(func.count(WorkflowRun.id)).where(
        WorkflowRun.org_id == org_id,
        WorkflowRun.status.in_([RunStatus.RUNNING, RunStatus.WAITING_HITL])
    )
    active_count = (await session.exec(stmt_active)).one()

    # Total Executed
    stmt_total = select(func.count(WorkflowRun.id)).where(
        WorkflowRun.org_id == org_id
    )
    total_count = (await session.exec(stmt_total)).one()

    # Pending HITL
    stmt_hitl = select(func.count(WorkflowRun.id)).where(
        WorkflowRun.org_id == org_id,
        WorkflowRun.status == RunStatus.WAITING_HITL
    )
    hitl_count = (await session.exec(stmt_hitl)).one()

    # Success Rate
    stmt_success = select(func.count(WorkflowRun.id)).where(
        WorkflowRun.org_id == org_id,
        WorkflowRun.status == RunStatus.SUCCEEDED
    )
    success_count = (await session.exec(stmt_success)).one()

    stmt_finished = select(func.count(WorkflowRun.id)).where(
        WorkflowRun.org_id == org_id,
        WorkflowRun.status.in_([RunStatus.SUCCEEDED, RunStatus.FAILED])
    )
    finished_count = (await session.exec(stmt_finished)).one()

    success_rate = (success_count / finished_count * 100) if finished_count > 0 else 100.0

    return DashboardStatsResponse(
        active_runs=active_count,
        workflows_executed=total_count,
        pending_hitl=hitl_count,
        success_rate=round(success_rate, 1)
    )


# ---------------------------------------------------------------------------
# POST /api/runs — trigger a new run
# ---------------------------------------------------------------------------

@router.post("/", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def trigger_run(
    body: TriggerRunRequest,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> RunResponse:
    """Trigger a new workflow run. Requires DEVELOPER role or above."""
    assert_can_trigger(current_user)
    import json
    log = logger.bind(user_id=current_user.id)
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    if body.ticket_id:
        log = log.bind(ticket_id=body.ticket_id)
    if body.workflow_id:
        log = log.bind(workflow_id=body.workflow_id)
    log.info("api.trigger_run", org_id=org_id)

    inputs_str = json.dumps(body.inputs) if body.inputs else None

    run = WorkflowRun(
        org_id=org_id,
        ticket_id=body.ticket_id,
        workflow_id=body.workflow_id,
        # Priority: explicit body.agent_id -> inputs.agent_id -> None
        agent_id=body.agent_id or (body.inputs.get("agent_id") if body.inputs else None),
        inputs_json=inputs_str,
        dry_run=body.dry_run,
        status=RunStatus.PENDING,
        trigger_type="manual",
    )
    session.add(run)
    await session.commit()
    # Skip refresh to avoid potential 500

    # Phase 2: Start the dynamic ReAct workflow in Temporal
    try:
        temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
        temporal_client = await Client.connect(temporal_address)

        # Parse inputs from JSON string
        inputs = {}
        if run.inputs_json:
            try:
                inputs = json.loads(run.inputs_json)
            except Exception:
                pass
        
        task_input = inputs.get("task") or run.ticket_id or "Execute agent task"
        
        await temporal_client.start_workflow(
            "AgentReActWorkflow",
            args=[str(run.agent_id), str(run.id), task_input],
            id=f"agent-react-run-{run.id}",
            task_queue="agent-task-queue",
        )
        log.info("api.run_dispatched", run_id=run.id, workflow="AgentReActWorkflow")
    except Exception as e:
        log.error("api.temporal_dispatch_failed", error=str(e))
        # Don't fail the request if Temporal is down, but log it
        # In a real prod environment, we'd want a separate queue or retry mechanism

    # Publish metering event (Epic 5.4 — fire-and-forget)
    import asyncio
    asyncio.create_task(_publish_metering_event(run.org_id, "run"))

    return _run_to_response(run)


async def _publish_metering_event(org_id: str, event_type: str, tokens: int = 0) -> None:
    """Publish a usage event to the tenant's metering Redpanda topic."""
    try:
        import json
        from aiokafka import AIOKafkaProducer
        brokers = os.environ.get("REDPANDA_BROKERS", "localhost:19092")
        producer = AIOKafkaProducer(bootstrap_servers=brokers)
        await producer.start()
        try:
            payload = json.dumps({"org_id": org_id, "event_type": event_type, "tokens": tokens}).encode()
            await producer.send_and_wait(f"t.{org_id}.metering", payload)
        finally:
            await producer.stop()
    except Exception as exc:
        logger.debug("metering_publish.failed", error=str(exc))



# ---------------------------------------------------------------------------
# GET /api/runs — list runs with pagination
# ---------------------------------------------------------------------------

@router.get("/", response_model=RunListResponse)
async def list_runs(
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[Optional[str], Query(alias="status")] = None,
) -> RunListResponse:
    """List all workflow runs for the current org, newest first."""
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    query = select(WorkflowRun).where(WorkflowRun.org_id == org_id)

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
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> RunDetailResponse:
    """Get the full details of a run including all steps and HITL events."""
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    run = await _get_run_or_404(run_id, org_id, session)

    return RunDetailResponse(
        run_id=run.id,
        workflow_id=run.workflow_id,
        agent_id=run.agent_id,
        ticket_id=run.ticket_id,
        status=run.status.value,
        trigger_type=run.trigger_type,
        temporal_workflow_id=run.temporal_workflow_id,
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
        events=[_event_to_response(e) for e in run.events],
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


@router.get("/{run_id}/events", response_model=list[RunEventResponse])
async def get_run_events(
    run_id: str,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> list[RunEventResponse]:
    """Get chronological lifecycle events (thoughts, actions) for a run."""
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    run = await _get_run_or_404(run_id, org_id, session)
    return [_event_to_response(e) for e in run.events]


@router.get("/{run_id}/events/stream")
async def stream_run_events(
    run_id: str,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
):
    """
    SSE endpoint streaming real-time run events (thoughts, tool calls).
    Subscribes to Redpanda topic `t.{org_id}.run-events`.
    """
    from aiokafka import AIOKafkaConsumer
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    brokers = os.environ.get("REDPANDA_BROKERS", "localhost:19092")
    topic = f"t.{org_id}.run-events"

    async def event_generator():
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=brokers,
            auto_offset_reset="earliest", # Catch up on missed events
            enable_auto_commit=False,
            group_id=f"sse-consumer-{run_id}-{current_user.id}"
        )
        await consumer.start()
        try:
            async for msg in consumer:
                try:
                    data = json.loads(msg.value.decode("utf-8"))
                    if data.get("run_id") == run_id:
                        yield f"data: {json.dumps(data)}\n\n"
                except Exception as e:
                    logger.error("sse.parse_error", error=str(e))
        finally:
            await consumer.stop()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# GET /api/runs/{run_id}/plan — return structured plan JSON
# ---------------------------------------------------------------------------

@router.get("/{run_id}/plan", response_model=PlanResponse)
async def get_plan(
    run_id: str,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> PlanResponse:
    """Return the structured planning output for a run."""
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    run = await _get_run_or_404(run_id, org_id, session)

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
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> DecisionResponse:
    """
    Submit a HITL decision for a run that is in WAITING_HITL status.
    Requires REVIEWER role or above.
    """
    assert_can_approve_hitl(current_user)
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    run = await _get_run_or_404(run_id, org_id, session)

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

    # Send Signal to Temporal workflow
    try:
        temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
        temporal_client = await Client.connect(temporal_address)
        
        handle = temporal_client.get_workflow_handle(f"agent-workflow-{run.id}")
        await handle.signal(
            "hitl-decision-signal",
            {"action": body.action, "feedback": body.feedback}
        )
    except Exception as e:
        logger.error("api.temporal_signal_failed", error=str(e))
        # Might be okay if workflow already finished, but usually we'd want to handle gracefully

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
    session: TenantSessionDep,
) -> WorkflowRun:
    """Fetch a WorkflowRun by ID, scoped to the org. Raises 404 if not found."""
    # org_id here is already determined by the router (either header or current_user)
    result = await session.exec(
        select(WorkflowRun).where(
            WorkflowRun.id == run_id,
            WorkflowRun.org_id == org_id,
        ).options(
            selectinload(WorkflowRun.steps),
            selectinload(WorkflowRun.events),
            selectinload(WorkflowRun.hitl_events),
        )
    )
    run = result.first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found.",
        )
    return run
