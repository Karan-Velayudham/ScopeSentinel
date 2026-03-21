"""
routers/health.py — GET /api/health liveness + dependency check (Epic 1.2.7)
"""

import os

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter
from sqlalchemy import text

from db.session import engine
from schemas import HealthResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Liveness + readiness check.

    Verifies connectivity to PostgreSQL and Redis.
    Returns 200 with status=`ok` if all dependencies are healthy,
    or status=`degraded` if any dependency is unreachable.
    """
    # --- PostgreSQL check ---
    postgres_status = "unreachable"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        postgres_status = "connected"
    except Exception as exc:
        logger.warning("health.postgres_unreachable", error=str(exc))

    # --- Redis check ---
    redis_status = "unreachable"
    try:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        r = aioredis.from_url(redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        redis_status = "connected"
    except Exception as exc:
        logger.warning("health.redis_unreachable", error=str(exc))

    overall = "ok" if postgres_status == "connected" and redis_status == "connected" else "degraded"
    return HealthResponse(
        status=overall,
        postgres=postgres_status,
        redis=redis_status,
    )
