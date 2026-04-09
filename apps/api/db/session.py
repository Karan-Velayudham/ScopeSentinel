"""
db/session.py — Async SQLModel engine + session dependency (Epic 1.1.2)

Single session type used for all requests. Tenant isolation is enforced
exclusively via `org_id` columns and WHERE clauses in each router — no
per-tenant PostgreSQL schema switching is required at this stage.
"""

import os
from typing import AsyncGenerator, Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession


def _build_database_url() -> str:
    """
    Build the async PostgreSQL database URL from env vars.
    Falls back gracefully to a local default.
    """
    user = os.environ.get("DB_USER", "sentinel")
    password = os.environ.get("DB_PASSWORD", "sentinel_dev")
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "scopesentinel")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


DATABASE_URL = _build_database_url()

# pool_pre_ping=False to avoid MissingGreenlet in some async contexts
engine = create_async_engine(
    DATABASE_URL,
    echo=os.environ.get("DB_ECHO", "false").lower() == "true",
    pool_size=10,
    max_overflow=20,
)


async def create_db_and_tables() -> None:
    """Create all tables (called on startup). Migrations via Alembic in prod."""
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        # Lightweight column migrations — safe to re-run (idempotent)
        await conn.execute(text(
            "ALTER TABLE workflows ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'draft'"
        ))
        await conn.execute(text(
            "ALTER TABLE workflow_runs ALTER COLUMN ticket_id DROP NOT NULL"
        ))
        await conn.execute(text(
            "ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS inputs_json VARCHAR"
        ))


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


# Annotated type aliases for clean dependency declarations.
# TenantSessionDep is intentionally identical to SessionDep — tenant isolation
# is enforced by org_id WHERE clauses in each router, not by schema switching.
SessionDep = Annotated[AsyncSession, Depends(get_session)]
TenantSessionDep = Annotated[AsyncSession, Depends(get_session)]
