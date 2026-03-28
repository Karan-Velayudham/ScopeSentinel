"""
db/session.py — Async SQLModel engine + session dependency (Epic 1.1.2)

Two session types:
  SessionDep        — plain session, always on the `public` schema.
  TenantSessionDep  — sets `search_path=tenant_{id}, public` per request (Epic 5.1.2).
"""

import os
from typing import AsyncGenerator, Annotated

from fastapi import Depends, Request
from sqlalchemy import text
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
    """FastAPI dependency that yields an async DB session (public schema)."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        await session.execute(text("SET search_path TO public"))
        yield session


async def get_tenant_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a tenant-scoped DB session.

    Reads `request.state.tenant_id` (set by TenantMiddleware) and executes
    `SET search_path TO tenant_{id}, public` so all queries within the
    session are automatically scoped to the tenant's schema.
    """
    async with AsyncSession(engine, expire_on_commit=False) as session:
        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id:
            # Use SET instead of SET LOCAL to persist across transactions in the same session/connection
            await session.execute(text(f"SET search_path TO tenant_{tenant_id}, public"))
        else:
            await session.execute(text("SET search_path TO public"))
        yield session


# Annotated type aliases for clean dependency declarations
SessionDep = Annotated[AsyncSession, Depends(get_session)]
TenantSessionDep = Annotated[AsyncSession, Depends(get_tenant_session)]
