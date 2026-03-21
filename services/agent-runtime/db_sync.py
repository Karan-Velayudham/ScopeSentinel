import os
import structlog
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

async def sync_run_progress(run_id: str, status: str = None, prompt_tokens: int = 0, completion_tokens: int = 0):
    """
    Update WorkflowRun status and/or token usage in the database.
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
            
            if not updates:
                return

            updates.append("updated_at = :now")
            sql = f"UPDATE workflow_runs SET {', '.join(updates)} WHERE id = :id"
            await conn.execute(text(sql), params)
            
            logger.info("db.sync_success", run_id=run_id, status=status, total_tokens=prompt_tokens+completion_tokens)
    except Exception as e:
        logger.error("db.sync_failed", error=str(e), run_id=run_id)
