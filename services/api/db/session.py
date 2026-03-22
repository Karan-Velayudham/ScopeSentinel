"""
db/session.py — Async SQLModel engine + session dependency (Epic 1.1.2)

Uses asyncpg as the driver.  Pass the async session via FastAPI's
dependency injection system using the `SessionDep` type alias.
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

# pool_pre_ping=True: validate connections before use (handles DB restarts)
engine = create_async_engine(
    DATABASE_URL,
    echo=os.environ.get("DB_ECHO", "false").lower() == "true",
    pool_pre_ping=True,
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


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


# Annotated type alias for clean dependency declarations
SessionDep = Annotated[AsyncSession, Depends(get_session)]
