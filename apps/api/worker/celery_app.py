"""
worker/celery_app.py — Celery task dispatcher stub for services/api/

The actual task implementation lives in services/agent-runtime/worker/celery_app.py.
This stub allows the FastAPI app to dispatch tasks by name without importing
the agent-runtime's heavy dependencies (agentscope, etc.).

Both services share the same Redis broker and task name, so Celery routes
the task to whichever worker is listening.
"""

import os
from celery import Celery

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
)

# ---------------------------------------------------------------------------
# Task signature stub — allows the API to call .delay() without importing
# the full implementation. Celery routes by task name to the real worker.
# ---------------------------------------------------------------------------

run_workflow_task = celery_app.signature("run_workflow_task")
