"""
main.py — Metering & Quota Service (Epic 5.4)

Dual-purpose service:
  1. Redpanda consumer: subscribes to `t.*.metering` topics, aggregates usage into `usage_buckets`
  2. FastAPI API:
     - GET  /metering/usage           — usage summary per org + billing period
     - GET  /metering/quota/{org_id}/check — Redis sliding window quota check

Usage events published by services/api on every run start, step complete, and LLM call.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator, Optional

import redis.asyncio as aioredis
import structlog
from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import func

from models import UsageEvent, UsageBucket

# ---------------------------------------------------------------------------
# Config & Setup
# ---------------------------------------------------------------------------

REDPANDA_BROKERS = os.environ.get("REDPANDA_BROKERS", "localhost:19092")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/1")


def _build_db_url() -> str:
    u = os.environ.get("DB_USER", "sentinel")
    p = os.environ.get("DB_PASSWORD", "sentinel_dev")
    h = os.environ.get("DB_HOST", "localhost")
    pt = os.environ.get("DB_PORT", "5432")
    n = os.environ.get("DB_NAME", "scopesentinel")
    return f"postgresql+asyncpg://{u}:{p}@{h}:{pt}/{n}"


engine = create_async_engine(_build_db_url(), pool_pre_ping=True, pool_size=5, max_overflow=10)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=True)
        if os.environ.get("LOG_FORMAT", "console") != "json"
        else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger(__name__)


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


# ---------------------------------------------------------------------------
# Quota enforcement (Redis sliding window counter)
# ---------------------------------------------------------------------------

DEFAULT_QUOTA = int(os.environ.get("DEFAULT_RUN_QUOTA_PER_MONTH", "1000"))


async def get_redis() -> aioredis.Redis:
    return aioredis.from_url(REDIS_URL, decode_responses=True)


async def increment_quota_counter(org_id: str, event_type: str) -> int:
    """Increment and return the current month's counter for the org."""
    r = await get_redis()
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    key = f"quota:{org_id}:{event_type}:{period}"
    count = await r.incr(key)
    # Expire at the end of the current month (32 days max)
    await r.expire(key, 32 * 24 * 3600)
    await r.aclose()
    return count


async def get_quota_count(org_id: str, event_type: str) -> int:
    """Read the current month's counter without incrementing."""
    r = await get_redis()
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    key = f"quota:{org_id}:{event_type}:{period}"
    val = await r.get(key)
    await r.aclose()
    return int(val) if val else 0


# ---------------------------------------------------------------------------
# Redpanda consumer
# ---------------------------------------------------------------------------

async def consume_metering_events() -> None:
    consumer = AIOKafkaConsumer(
        bootstrap_servers=REDPANDA_BROKERS,
        group_id="metering-service-group",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    while True:
        try:
            await consumer.start()
            logger.info("metering.consumer_started")
            break
        except Exception as exc:
            logger.warning("metering.consumer_waiting", error=str(exc))
            await asyncio.sleep(5)

    consumer.subscribe(pattern=r"t\..+\.metering")
    logger.info("metering.subscribed", pattern="t.*.metering")

    try:
        async for msg in consumer:
            try:
                data = json.loads(msg.value.decode("utf-8"))
                org_id = data.get("org_id", "unknown")
                event_type = data.get("event_type", "run")
                tokens = data.get("tokens", 0)

                # Write raw event
                event = UsageEvent(
                    org_id=org_id,
                    event_type=event_type,
                    tokens=tokens,
                )
                async with AsyncSession(engine, expire_on_commit=False) as session:
                    session.add(event)
                    await session.commit()

                # Update quota counter in Redis
                await increment_quota_counter(org_id, event_type)
                logger.debug("metering.event_recorded", org_id=org_id, event_type=event_type)
            except Exception as exc:
                logger.error("metering.consumer_error", error=str(exc))
    finally:
        await consumer.stop()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

_consumer_task: asyncio.Task = None  # type: ignore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await create_tables()
    logger.info("metering.db_ready")
    global _consumer_task
    _consumer_task = asyncio.create_task(consume_metering_events())
    yield
    _consumer_task.cancel()
    logger.info("metering.shutdown")


app = FastAPI(
    title="ScopeSentinel Metering Service",
    description="Usage ingestion, quota enforcement, and billing API.",
    version="1.0.0",
    lifespan=lifespan,
)

_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/metering/usage")
async def get_usage(
    org_id: str = Query(...),
    period: Optional[str] = Query(None, description="YYYY-MM format, defaults to current month"),
):
    """Return usage summary for an org in a given billing period."""
    if not period:
        period = datetime.now(timezone.utc).strftime("%Y-%m")

    async for session in get_session():
        # Parse period
        year, month = map(int, period.split("-"))
        period_start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            period_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            period_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        stmt = select(
            UsageEvent.event_type,
            func.count(UsageEvent.id).label("count"),
            func.sum(UsageEvent.tokens).label("total_tokens"),
        ).where(
            UsageEvent.org_id == org_id,
            UsageEvent.occurred_at >= period_start,
            UsageEvent.occurred_at < period_end,
        ).group_by(UsageEvent.event_type)

        result = await session.exec(stmt)
        rows = result.all()

        return {
            "org_id": org_id,
            "period": period,
            "breakdown": [
                {"event_type": r[0], "count": r[1], "total_tokens": r[2] or 0}
                for r in rows
            ],
            "quota": {
                "runs_this_month": await get_quota_count(org_id, "run"),
                "limit": DEFAULT_QUOTA,
            },
        }


@app.get("/metering/quota/{org_id}/check")
async def check_quota(org_id: str, event_type: str = "run"):
    """
    Check whether the org has exceeded its monthly quota.
    Returns 200 if within quota, 429 if exceeded.
    Used as a Kong pre-request plugin for quota enforcement.
    """
    count = await get_quota_count(org_id, event_type)
    if count >= DEFAULT_QUOTA:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly quota exceeded: {count}/{DEFAULT_QUOTA} {event_type} events",
        )
    return {"allowed": True, "current": count, "limit": DEFAULT_QUOTA, "remaining": DEFAULT_QUOTA - count}


@app.get("/health")
async def health():
    return {"service": "metering", "status": "ok"}


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "ScopeSentinel Metering Service", "version": "1.0.0"}
