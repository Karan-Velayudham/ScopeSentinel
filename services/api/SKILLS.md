# Control Plane API — Skills & Knowledge

**Location**: `services/api/`

## Purpose
This directory houses the **FastAPI Control Plane**, which is the central brain of ScopeSentinel. It acts as the backend for the soon-to-be-built Next.js frontend and coordinates all workflows. It handles HTTP requests, persists data to PostgreSQL, and pushes execution tasks to the Celery worker (`services/agent-runtime`). No AI inference logic runs directly in this service.

## Tech Stack & Standards
- Python 3.12+
- **Framework**: `FastAPI` + `Uvicorn`
- **Database ORM**: `SQLModel` + `asyncpg` (PostgreSQL)
- **Migrations**: `Alembic`
- **Async Execution**: `Celery` (with Redis as broker)
- **Logging**: `structlog`

## Key Patterns
- **API First**: Features implemented here must have a corresponding REST endpoint or WebSocket.
- **Async Required**: All database operations (`session.exec()`) and external calls must be fully async.
- **Database Modeling**: Models are defined in `db/models.py`. Use `sa_type=sqlalchemy.DateTime(timezone=True)` for all timestamps to ensure compatibility with `asyncpg`.
- **Relationship Loading**: When using `select()`, always explicitly eagerly load relationships via `selectinload` from `sqlalchemy.orm` to prevent `MissingGreenlet` errors in async contexts.
- **Testing**: Tests must use `aiosqlite` connected to an in-memory SQLite database (`conftest.py`) so tests run blazingly fast without requiring a live Postgres instance.

## Execution Flow Example
1. Endpoint `POST /api/runs` is invoked.
2. Endpoint creates a `WorkflowRun` row in Postgres.
3. Endpoint delegates work by calling `run_workflow_task.delay(run_id)`.
4. Endpoint returns the `RunResponse` to the user immediately.
