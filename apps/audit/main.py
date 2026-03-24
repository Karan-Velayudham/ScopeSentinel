"""
main.py — Audit Service (Epic 5.3)

Dual-purpose service:
  1. Redpanda consumer: subscribes to `t.*.audit` topics, writes AuditEvent rows
  2. FastAPI query API: `GET /audit/events` for the audit log viewer UI

AuditEvent rows are append-only — no UPDATE or DELETE paths exposed.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import structlog
from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import AuditEvent

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REDPANDA_BROKERS = os.environ.get("REDPANDA_BROKERS", "localhost:19092")

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
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


# ---------------------------------------------------------------------------
# Redpanda consumer — subscribes to all t.*.audit topics
# ---------------------------------------------------------------------------

async def consume_audit_events() -> None:
    """Long-running Kafka consumer that writes audit events to the DB."""
    consumer = AIOKafkaConsumer(
        bootstrap_servers=REDPANDA_BROKERS,
        group_id="audit-service-group",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    # Wait for Redpanda to be ready
    while True:
        try:
            await consumer.start()
            logger.info("audit.consumer_started", brokers=REDPANDA_BROKERS)
            break
        except Exception as exc:
            logger.warning("audit.consumer_waiting", error=str(exc))
            await asyncio.sleep(5)

    # Subscribe to all tenant audit topics via regex pattern
    consumer.subscribe(pattern=r"t\..+\.audit")
    logger.info("audit.subscribed", pattern="t.*.audit")

    try:
        async for msg in consumer:
            try:
                data = json.loads(msg.value.decode("utf-8"))
                event = AuditEvent(
                    org_id=data.get("org_id", ""),
                    user_id=data.get("user_id"),
                    action=data.get("action", "unknown"),
                    resource_type=data.get("resource_type"),
                    resource_id=data.get("resource_id"),
                    payload_json=json.dumps(data.get("payload", {})),
                )
                async with AsyncSession(engine, expire_on_commit=False) as session:
                    session.add(event)
                    await session.commit()
                logger.debug("audit.event_written", action=event.action, org_id=event.org_id)
            except Exception as exc:
                logger.error("audit.consumer_error", error=str(exc))
    finally:
        await consumer.stop()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

_consumer_task: asyncio.Task = None  # type: ignore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await create_tables()
    logger.info("audit.db_ready")
    global _consumer_task
    _consumer_task = asyncio.create_task(consume_audit_events())
    yield
    _consumer_task.cancel()
    logger.info("audit.shutdown")


app = FastAPI(
    title="ScopeSentinel Audit Service",
    description="Append-only audit log consumer and query API.",
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


@app.get("/audit/events")
async def list_audit_events(
    org_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    Query the audit log. Supports filter by org_id, user_id, action, and resource_type.
    Results are newest-first.
    """
    async for session in get_session():
        query = select(AuditEvent)
        if org_id:
            query = query.where(AuditEvent.org_id == org_id)
        if user_id:
            query = query.where(AuditEvent.user_id == user_id)
        if action:
            query = query.where(AuditEvent.action == action)
        if resource_type:
            query = query.where(AuditEvent.resource_type == resource_type)
        query = query.order_by(AuditEvent.occurred_at.desc()).offset(offset).limit(limit)  # type: ignore
        result = await session.exec(query)
        events = result.all()
        return [
            {
                "id": e.id,
                "org_id": e.org_id,
                "user_id": e.user_id,
                "action": e.action,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "payload": json.loads(e.payload_json) if e.payload_json else {},
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in events
        ]


@app.get("/health")
async def health():
    return {"service": "audit", "status": "ok", "consumer": "running" if _consumer_task and not _consumer_task.done() else "stopped"}


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "ScopeSentinel Audit Service", "version": "1.0.0"}
