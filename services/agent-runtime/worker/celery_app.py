"""
worker/celery_app.py — Celery application + `run_workflow_task` (Epic 1.3.1-1.3.4)

Architecture:
  - Broker:  Redis (redis://redis:6379/0)
  - Backend: Redis (task results)
  - Task:    `run_workflow_task` — dispatched by POST /api/runs,
             runs the full agent workflow, persists state to PostgreSQL.

HITL Pause/Resume:
  The task reaches the HITL gate, sets run status = WAITING_HITL,
  then subscribes to `Redis SUBSCRIBE hitl:{run_id}` and blocks.
  When POST /api/runs/{id}/decision is called, the API publishes to
  that channel and the task resumes with the decision payload.
"""

import asyncio
import json
import os
from datetime import datetime, timezone

import structlog
from celery import Celery

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Celery app
# ---------------------------------------------------------------------------

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "scopesentinel",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,           # Re-queue task if worker dies
    worker_prefetch_multiplier=1,  # Process one task at a time (long-running)
    task_track_started=True,
    timezone="UTC",
)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_db_url() -> str:
    user = os.environ.get("DB_USER", "sentinel")
    password = os.environ.get("DB_PASSWORD", "sentinel_dev")
    host = os.environ.get("DB_HOST", "postgres")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "scopesentinel")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@celery_app.task(name="run_workflow_task", bind=True, max_retries=0)
def run_workflow_task(self, *, run_id: str, ticket_id: str, dry_run: bool = False) -> dict:
    """
    Main Celery task: runs the ScopeSentinel agent workflow.

    This is a *sync* Celery task that internally drives an asyncio event loop
    so we can reuse the existing async agent code.
    """
    return asyncio.get_event_loop().run_until_complete(
        _run_workflow_async(run_id=run_id, ticket_id=ticket_id, dry_run=dry_run)
    )


async def _run_workflow_async(
    run_id: str,
    ticket_id: str,
    dry_run: bool,
) -> dict:
    """
    Async implementation of the workflow task.

    Writes run status and step records to PostgreSQL at each transition.
    At the HITL gate, publishes status=WAITING_HITL and blocks on Redis
    pub/sub until a decision arrives.
    """
    import redis.asyncio as aioredis
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlmodel import select
    from sqlmodel.ext.asyncio.session import AsyncSession

    from db.models import HitlAction, RunStatus, RunStep, StepStatus, WorkflowRun

    log = structlog.get_logger(__name__).bind(run_id=run_id, ticket_id=ticket_id)
    log.info("worker.task_started", dry_run=dry_run)

    engine = create_async_engine(_get_db_url(), pool_pre_ping=True)

    async def _update_run(status: RunStatus, plan_json: str | None = None, error: str | None = None) -> None:
        async with AsyncSession(engine, expire_on_commit=False) as s:
            result = await s.exec(select(WorkflowRun).where(WorkflowRun.id == run_id))
            run = result.first()
            if run:
                run.status = status
                run.updated_at = _utcnow()
                if plan_json is not None:
                    run.plan_json = plan_json
                if error is not None:
                    run.error_message = error
                s.add(run)
                await s.commit()

    async def _add_step(
        step_name: str,
        status: StepStatus = StepStatus.RUNNING,
        input_json: str | None = None,
        output_json: str | None = None,
        error_message: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> RunStep:
        async with AsyncSession(engine, expire_on_commit=False) as s:
            step = RunStep(
                run_id=run_id,
                step_name=step_name,
                status=status,
                input_json=input_json,
                output_json=output_json,
                error_message=error_message,
                started_at=started_at or _utcnow(),
                finished_at=finished_at,
            )
            s.add(step)
            await s.commit()
            await s.refresh(step)
            return step

    async def _finish_step(step: RunStep, status: StepStatus, output: str | None = None, error: str | None = None) -> None:
        async with AsyncSession(engine, expire_on_commit=False) as s:
            result = await s.exec(select(RunStep).where(RunStep.id == step.id))
            db_step = result.first()
            if db_step:
                db_step.status = status
                db_step.finished_at = _utcnow()
                if output is not None:
                    db_step.output_json = output
                if error is not None:
                    db_step.error_message = error
                s.add(db_step)
                await s.commit()

    async def _wait_for_hitl_decision() -> dict:
        """Block on Redis pub/sub until a HITL decision is published."""
        r = aioredis.from_url(REDIS_URL)
        pubsub = r.pubsub()
        channel = f"hitl:{run_id}"
        try:
            await pubsub.subscribe(channel)
            log.info("worker.hitl_waiting", channel=channel)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    decision = json.loads(message["data"])
                    log.info("worker.hitl_decision_received", action=decision.get("action"))
                    return decision
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
            await r.aclose()
        return {"action": "reject"}  # fallback (should never reach here)

    async def _publish_log(message: str) -> None:
        """Publish a log line to the WebSocket stream channel."""
        r = aioredis.from_url(REDIS_URL)
        try:
            await r.publish(f"logs:{run_id}", json.dumps({"message": message, "ts": _utcnow().isoformat()}))
        finally:
            await r.aclose()

    # ------------------------------------------------------------------
    # Main workflow
    # ------------------------------------------------------------------
    try:
        await _update_run(RunStatus.RUNNING)
        await _publish_log("Workflow started")

        # Import agent-runtime components (same Docker image)
        from dotenv import load_dotenv
        load_dotenv()

        import agentscope
        from agentscope.model import OpenAIChatModel
        import os as _os
        from main import _build_model  # reuse from agent-runtime main
        from mcp_pool import load_client_pool
        from agents.planner_agent import PlannerAgent
        from agents.coder_agent import CoderAgent
        from hitl.hitl_gateway import HITLGateway

        # Step 1: Init model
        step = await _add_step("init_model")
        try:
            agentscope.init(project="ScopeSentinel", name=f"Run-{run_id[:8]}")
            model = _build_model()
            await _finish_step(step, StepStatus.SUCCEEDED)
            await _publish_log("Model initialized")
        except Exception as exc:
            await _finish_step(step, StepStatus.FAILED, error=str(exc))
            await _update_run(RunStatus.FAILED, error=str(exc))
            log.error("worker.init_model_failed", error=str(exc))
            return {"status": "FAILED", "error": str(exc)}

        # Step 2: Load MCP pool
        step = await _add_step("load_mcp_pool")
        try:
            clients, tool_registry = await load_client_pool("mcp_servers.yaml")
            await _finish_step(step, StepStatus.SUCCEEDED)
            await _publish_log(f"MCP pool ready ({len(tool_registry)} tools)")
        except Exception as exc:
            await _finish_step(step, StepStatus.FAILED, error=str(exc))
            await _update_run(RunStatus.FAILED, error=str(exc))
            return {"status": "FAILED", "error": str(exc)}

        MAX_REVISIONS = 3
        plan = None

        try:
            # Step 3: Fetch ticket
            step = await _add_step("fetch_ticket", input_json=json.dumps({"ticket_id": ticket_id}))
            try:
                fetch_func = tool_registry["fetch_jira_ticket"]
                res = await fetch_func(ticket_id=ticket_id)
                ticket_content = res.content[0]["text"] if hasattr(res, "content") else str(res)
                await _finish_step(step, StepStatus.SUCCEEDED, output_json=json.dumps({"length": len(ticket_content)}))
                await _publish_log(f"Ticket {ticket_id} fetched")
            except Exception as exc:
                await _finish_step(step, StepStatus.FAILED, error=str(exc))
                await _update_run(RunStatus.FAILED, error=str(exc))
                return {"status": "FAILED", "error": str(exc)}

            # Step 4: Generate plan
            step = await _add_step("plan")
            planner = PlannerAgent(model=model)
            try:
                plan = await planner.plan(ticket_id, tool_registry)
                plan_json = json.dumps({
                    "steps": plan.steps,
                    "architecture_notes": plan.architecture_notes,
                    "raw_plan": plan.raw_plan,
                })
                await _finish_step(step, StepStatus.SUCCEEDED, output_json=plan_json)
                await _update_run(RunStatus.WAITING_HITL, plan_json=plan_json)
                await _publish_log(f"Plan ready ({len(plan.steps)} steps). Waiting for HITL approval.")
            except Exception as exc:
                await _finish_step(step, StepStatus.FAILED, error=str(exc))
                await _update_run(RunStatus.FAILED, error=str(exc))
                return {"status": "FAILED", "error": str(exc)}

            # Step 5: HITL approval loop
            for revision in range(MAX_REVISIONS + 1):
                step = await _add_step("hitl", input_json=json.dumps({"revision": revision}))

                # Block here until API publishes a decision
                decision = await _wait_for_hitl_decision()

                if decision["action"] == "approve":
                    await _finish_step(step, StepStatus.SUCCEEDED, output_json=json.dumps(decision))
                    await _publish_log(f"Plan approved (revision {revision})")

                    if dry_run:
                        await _update_run(RunStatus.SUCCEEDED)
                        await _publish_log("Dry-run mode: skipping code generation.")
                        return {"status": "SUCCEEDED", "dry_run": True}

                    # Step 6: Code generation
                    step = await _add_step("code_generation")
                    coder = CoderAgent(model=model)
                    try:
                        result = await coder.code_with_validation(
                            ticket_id=ticket_id,
                            ticket_content=ticket_content,
                            plan=plan,
                            tool_registry=tool_registry,
                        )
                        output = {
                            "files_written": result.files_written,
                            "workspace_path": str(result.workspace_path),
                        }
                        await _finish_step(step, StepStatus.SUCCEEDED, output_json=json.dumps(output))
                        await _update_run(RunStatus.SUCCEEDED)
                        await _publish_log(f"Code generation complete. {len(result.files_written)} files written.")
                        return {"status": "SUCCEEDED", "files_written": result.files_written}
                    except Exception as exc:
                        await _finish_step(step, StepStatus.FAILED, error=str(exc))
                        await _update_run(RunStatus.FAILED, error=str(exc))
                        return {"status": "FAILED", "error": str(exc)}

                elif decision["action"] == "reject":
                    await _finish_step(step, StepStatus.SUCCEEDED, output_json=json.dumps(decision))
                    await _update_run(RunStatus.ABORTED)
                    await _publish_log("Workflow aborted by reviewer.")
                    return {"status": "ABORTED"}

                elif decision["action"] == "modify":
                    await _finish_step(step, StepStatus.SUCCEEDED, output_json=json.dumps(decision))
                    if revision >= MAX_REVISIONS:
                        await _update_run(RunStatus.FAILED, error="Max HITL revisions reached")
                        return {"status": "FAILED", "error": "Max revisions reached"}
                    feedback = decision.get("feedback", "")
                    await _publish_log(f"Replanning with feedback (revision {revision + 1})...")
                    await _update_run(RunStatus.RUNNING)

                    # Replan
                    plan = await planner.replan(ticket_id, tool_registry, feedback, plan)
                    plan_json = json.dumps({
                        "steps": plan.steps,
                        "architecture_notes": plan.architecture_notes,
                        "raw_plan": plan.raw_plan,
                    })
                    await _update_run(RunStatus.WAITING_HITL, plan_json=plan_json)
                    await _publish_log(f"New plan ready (revision {revision + 1}).")

        finally:
            for client in clients:
                await client.close()
            log.info("worker.mcp_clients_closed")

    except Exception as exc:
        log.error("worker.unexpected_error", error=str(exc))
        await _update_run(RunStatus.FAILED, error=str(exc))
        return {"status": "FAILED", "error": str(exc)}
    finally:
        await engine.dispose()

    return {"status": "SUCCEEDED"}
