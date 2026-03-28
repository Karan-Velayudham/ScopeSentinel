import os
import json
import structlog
from typing import List, Optional
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from datetime import datetime, timezone

logger = structlog.get_logger(__name__)

def _build_url():
    user = os.environ.get("DB_USER", "sentinel")
    password = os.environ.get("DB_PASSWORD", "sentinel_dev")
    host = os.environ.get("DB_HOST", "postgres")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "scopesentinel")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"

engine = create_async_engine(_build_url())

async def sync_run_progress(
    run_id: str, 
    status: str = None, 
    prompt_tokens: int = 0, 
    completion_tokens: int = 0,
    analysis_passed: bool = None,
    analysis_feedback: str = None
):
    """
    Update WorkflowRun status, token usage, and/or audit results in the database.
    """
    try:
        async with engine.begin() as conn:
            updates = []
            params = {"id": run_id, "now": datetime.now(timezone.utc)}
            
            if status:
                updates.append("status = :status")
                params["status"] = status
            
            if prompt_tokens > 0 or completion_tokens > 0:
                updates.append("prompt_tokens = COALESCE(prompt_tokens, 0) + :p")
                updates.append("completion_tokens = COALESCE(completion_tokens, 0) + :c")
                updates.append("total_tokens = COALESCE(total_tokens, 0) + :p + :c")
                params["p"] = prompt_tokens
                params["c"] = completion_tokens
            
            if analysis_passed is not None:
                updates.append("analysis_passed = :ap")
                params["ap"] = analysis_passed
            
            if analysis_feedback is not None:
                updates.append("analysis_feedback = :af")
                params["af"] = analysis_feedback
            
            if not updates:
                return

            updates.append("updated_at = :now")
            sql = f"UPDATE workflow_runs SET {', '.join(updates)} WHERE id = :id"
            await conn.execute(text(sql), params)
            
            logger.info("db.sync_success", run_id=run_id, status=status, total_tokens=prompt_tokens+completion_tokens)
    except Exception as e:
        logger.error("db.sync_failed", error=str(e), run_id=run_id)

async def get_agent(agent_id: str) -> dict:
    """
    Fetch agent details from the database.
    """
    try:
        async with engine.connect() as conn:
            sql = "SELECT id, name, identity, model, tools_json FROM agents WHERE id = :id"
            result = await conn.execute(text(sql), {"id": agent_id})
            row = result.fetchone()
            if not row:
                return {}
            
            # Use column names to build a dict
            return {
                "id": row[0],
                "name": row[1],
                "identity": row[2],
                "model": row[3],
                "tools": json.loads(row[4]) if row[4] else []
            }
    except Exception as e:
        logger.error("db.get_agent_failed", error=str(e), agent_id=agent_id)
        return {}


async def get_skills_for_agent(agent_id: str) -> List[dict]:
    """
    Fetch all skills associated with an agent.
    """
    try:
        async with engine.connect() as conn:
            sql = """
                SELECT s.id, s.name, s.content, s.version 
                FROM skills s
                JOIN agent_skill_links asl ON s.id = asl.skill_id
                WHERE asl.agent_id = :id AND s.is_active = true
            """
            result = await conn.execute(text(sql), {"id": agent_id})
            return [
                {"id": r[0], "name": r[1], "content": r[2], "version": r[3]}
                for r in result.fetchall()
            ]
    except Exception as e:
        logger.error("db.get_skills_failed", error=str(e), agent_id=agent_id)
        return []


async def log_run_event(
    run_id: str,
    event_type: str,
    payload: dict
):
    """
    Create a new RunEvent in the database.
    """
    try:
        async with engine.begin() as conn:
            sql = """
                INSERT INTO run_events (id, run_id, event_type, payload_json, created_at)
                VALUES (:id, :run_id, :type, :payload, :now)
            """
            import uuid
            params = {
                "id": str(uuid.uuid4()),
                "run_id": run_id,
                "type": event_type.upper(),
                "payload": json.dumps(payload),
                "now": datetime.now(timezone.utc)
            }
            await conn.execute(text(sql), params)
            logger.info("db.event_logged", run_id=run_id, type=event_type)
    except Exception as e:
        logger.error("db.log_event_failed", error=str(e), run_id=run_id)

async def get_run_org_id(run_id: str) -> str:
    """Fetch the org_id for a given workflow run."""
    try:
        async with engine.connect() as conn:
            sql = "SELECT org_id FROM workflow_runs WHERE id = :id"
            result = await conn.execute(text(sql), {"id": run_id})
            row = result.fetchone()
            if row:
                return row[0]
            return None
    except Exception as e:
        logger.error("db.get_run_org_id_failed", error=str(e), run_id=run_id)
        return None
