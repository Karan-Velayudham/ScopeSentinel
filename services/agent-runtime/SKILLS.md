# Agent Runtime & Celery Worker — Skills & Knowledge

**Location**: `services/agent-runtime/`

## Purpose
This directory houses the **Agentic Execution Engine** of ScopeSentinel. It is designed to run asynchronously in the background as a Celery worker. It consumes tasks dispatched by the `services/api` and handles the heavy lifting of autonomous software delivery: interacting with LLMs, managing multi-agent loops, writing code in the sandbox, and calling integration tools.

## Tech Stack & Standards
- Python 3.12+
- **Execution Runner**: `Celery`
- **Agent Framework**: `AgentScope`
- **Database ORM**: `SQLModel` + `asyncpg` (PostgreSQL - imports from `services.api.db`)
- **Memory/Pub-Sub**: `Redis`
- **Logging**: `structlog`

## Key Patterns
- **No HTTP Servers**: This service is a background worker. It should not open ports or run FastAPI.
- **Celery Tasks**: The entry point for execution is `worker/celery_app.py`, which defines the `run_workflow_task`. 
- **Human-in-the-loop (HITL)**: Workflow pauses are implemented via blocking Redis `pubsub.listen()` calls. The task waits on a specific channel (e.g., `hitl:{run_id}`) until the API service pushes a decision (approve/modify/reject).
- **Asynchronous Flow Management**: The worker must manage DB connection sessions explicitly when updating `run_steps` or `workflow_runs` states.
- **Tools & MCP**: The runtime interacts with tools via the Model Context Protocol (MCP) or custom Python tools defined in the `tools/` directory.

## Execution Flow Example
1. Celery receives `run_workflow_task(run_id)`.
2. Worker fetches the `WorkflowRun` state from Postgres.
3. `PlannerAgent` outlines the steps.
4. `CoderAgent` executes the steps iteratively.
5. If a step requires approval, worker publishes to `logs:{run_id}` and blocks on `hitl:{run_id}`.
6. Once unblocked, worker finishes execution and sets status to `SUCCEEDED`.
