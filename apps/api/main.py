"""
main.py — FastAPI application entry point (Epic 1.2)

Lifecycle:
  - On startup: create DB tables + run seed (idempotent)
  - Routers: /api/runs, /api/health
  - CORS: allow all in dev (tighten in production via ALLOWED_ORIGINS env var)
"""

from otel import configure_otel
# Configure OTEL before other imports
configure_otel()

# Load environment variables from .env file before any config is read
from dotenv import load_dotenv
load_dotenv()

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.seed import run_seed
from db.session import SessionDep, create_db_and_tables, get_session
from middleware import TenantMiddleware, AuditMiddleware
from routers import agents, connectors, health, runs, workflows, users, oauth_connections, audit, auth, skills, triggers, chats

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _configure_logging() -> None:
    log_format = os.environ.get("LOG_FORMAT", "console").lower()
    renderer = (
        structlog.processors.JSONRenderer()
        if log_format == "json"
        else structlog.dev.ConsoleRenderer(colors=True)
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            structlog.stdlib.NAME_TO_LEVEL.get(
                os.environ.get("LOG_LEVEL", "info"),
                structlog.stdlib.NAME_TO_LEVEL["info"],
            )
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


_configure_logging()
logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup tasks before yielding to the app, then cleanup on shutdown."""
    logger.info("api.startup")
    await create_db_and_tables()
    logger.info("api.db_tables_ready")

    # Run seeder (idempotent)
    async for session in get_session():
        await run_seed(session)
        break

    logger.info("api.seed_complete")
    yield
    logger.info("api.shutdown")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ScopeSentinel API",
    description="Control plane for the ScopeSentinel autonomous software delivery platform.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — restrict in production via ALLOWED_ORIGINS env var
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantMiddleware)
app.add_middleware(AuditMiddleware)

# Routers
app.include_router(runs.router)
app.include_router(health.router)
app.include_router(workflows.router)
app.include_router(connectors.router)
app.include_router(agents.router)
app.include_router(users.router)
app.include_router(oauth_connections.router)
app.include_router(audit.router)
app.include_router(auth.router)
app.include_router(skills.router)
app.include_router(triggers.router)
app.include_router(chats.router)


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"service": "ScopeSentinel API", "version": "1.0.0", "docs": "/docs"}
