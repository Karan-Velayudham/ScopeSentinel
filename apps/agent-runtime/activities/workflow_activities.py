"""
activities/workflow_activities.py — Temporal activities for YAML workflow execution.

Provides:
  - get_workflow_config_activity: Fetches a Workflow record (yaml_content, org_id)
    from the database so WorkflowYamlWorkflow can execute its steps dynamically.
"""

import json
import structlog
from temporalio import activity
from temporalio.exceptions import ApplicationError

from db_sync import engine
from sqlalchemy import text

logger = structlog.get_logger(__name__)


@activity.defn
async def get_workflow_config_activity(workflow_id: str) -> dict:
    """
    Fetch a Workflow record from the DB and return it as a dict.

    Returns:
        {
            "id":           str,
            "org_id":       str,
            "name":         str,
            "yaml_content": str,   # raw YAML string
            "status":       str,
        }

    Raises:
        ApplicationError if the workflow is not found.
    """
    try:
        async with engine.connect() as conn:
            sql = """
                SELECT id, org_id, name, yaml_content, status
                FROM workflows
                WHERE id = :id
            """
            result = await conn.execute(text(sql), {"id": workflow_id})
            row = result.fetchone()

        if not row:
            raise ApplicationError(
                f"Workflow '{workflow_id}' not found in database.",
                non_retryable=True,
            )

        return {
            "id":           row[0],
            "org_id":       row[1],
            "name":         row[2],
            "yaml_content": row[3] or "",
            "status":       row[4],
        }

    except ApplicationError:
        raise
    except Exception as exc:
        logger.error("db.get_workflow_config_failed", workflow_id=workflow_id, error=str(exc))
        raise ApplicationError(f"Failed to fetch workflow config: {exc}") from exc
