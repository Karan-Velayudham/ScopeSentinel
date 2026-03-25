"""
main.py — Tenant Management Service FastAPI application

Endpoints:
  POST   /tenants              — Create a new org + provision all infra
  GET    /tenants              — List all organisations
  GET    /tenants/{id}         — Get a single tenant by ID or slug
  PATCH  /tenants/{id}/config  — Update per-tenant config (LLM model, quota, features)
  DELETE /tenants/{id}         — Soft deprovision a tenant
  GET    /tenants/{id}/logs    — View provisioning log for a tenant
  GET    /health               — Liveness check
"""

import json
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select

from db.session import SessionDep, create_db_and_tables
from models import Org, TenantProvisionLog, TenantStatus
from provisioner import provision_tenant, deprovision_tenant
from schemas import TenantCreate, TenantConfigUpdate, TenantOut, ProvisionLogOut


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
    logger.info("tenant-mgmt.startup")
    await create_db_and_tables()
    logger.info("tenant-mgmt.db_ready")
    yield
    logger.info("tenant-mgmt.shutdown")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ScopeSentinel Tenant Management Service",
    description="Manages org lifecycle: schema provisioning, Redpanda topics, Qdrant collections.",
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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/tenants", response_model=TenantOut, status_code=201)
async def create_tenant(
    body: TenantCreate,
    background_tasks: BackgroundTasks,
    session: SessionDep,
):
    """
    Create a new organisation and kick off background provisioning.
    Provisioning (PG schema, Redpanda topics, Qdrant collection) runs async;
    the org is immediately returned with status=PROVISIONING.
    """
    # Check for duplicate slug
    result = await session.exec(select(Org).where(Org.slug == body.slug))
    org = result.first()
    if org:
        if org.status == TenantStatus.ACTIVE:
            raise HTTPException(status_code=409, detail=f"Org with slug '{body.slug}' is already active")
        # If still provisioning, we allow re-triggering the provisioner (retry)
        logger.info("tenant.retry_provisioning", org_id=org.id, slug=org.slug)
    else:
        config_json = json.dumps(body.tenant_config) if body.tenant_config else None
        org = Org(name=body.name, slug=body.slug, tenant_config=config_json)
        session.add(org)
        await session.commit()
        await session.refresh(org)
        logger.info("tenant.created", org_id=org.id, slug=org.slug)

    # Provision infra in the background so the API responds immediately
    background_tasks.add_task(provision_tenant, org, session)

    from fastapi import Response
    response = Response()
    response.status_code = 200 if org.id else 201
    return TenantOut.from_orm(org)


@app.get("/tenants", response_model=list[TenantOut])
async def list_tenants(session: SessionDep):
    result = await session.exec(select(Org))
    return [TenantOut.from_orm(o) for o in result.all()]


@app.get("/tenants/{tenant_id}", response_model=TenantOut)
async def get_tenant(tenant_id: str, session: SessionDep):
    # Try by ID first, then by slug
    result = await session.exec(select(Org).where(Org.id == tenant_id))
    org = result.first()
    if not org:
        result = await session.exec(select(Org).where(Org.slug == tenant_id))
        org = result.first()
    if not org:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantOut.from_orm(org)


@app.patch("/tenants/{tenant_id}/config", response_model=TenantOut)
async def update_tenant_config(tenant_id: str, body: TenantConfigUpdate, session: SessionDep):
    """Update per-tenant LLM model, token quota, or feature flags."""
    result = await session.exec(select(Org).where(Org.id == tenant_id))
    org = result.first()
    if not org:
        raise HTTPException(status_code=404, detail="Tenant not found")

    current = json.loads(org.tenant_config) if org.tenant_config else {}
    if body.llm_model is not None:
        current["llm_model"] = body.llm_model
    if body.token_quota_per_month is not None:
        current["token_quota_per_month"] = body.token_quota_per_month
    if body.features is not None:
        current["features"] = {**current.get("features", {}), **body.features}

    org.tenant_config = json.dumps(current)
    session.add(org)
    await session.commit()
    await session.refresh(org)

    logger.info("tenant.config_updated", org_id=org.id)
    return TenantOut.from_orm(org)


@app.delete("/tenants/{tenant_id}", status_code=204)
async def delete_tenant(tenant_id: str, session: SessionDep):
    """Soft-deprovision: marks org as deprovisioned. Data is retained."""
    result = await session.exec(select(Org).where(Org.id == tenant_id))
    org = result.first()
    if not org:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if org.status == TenantStatus.DEPROVISIONED:
        raise HTTPException(status_code=409, detail="Tenant is already deprovisioned")

    await deprovision_tenant(org, session)
    logger.info("tenant.deprovisioned", org_id=org.id)


@app.get("/tenants/{tenant_id}/logs", response_model=list[ProvisionLogOut])
async def get_tenant_logs(tenant_id: str, session: SessionDep):
    """View the provisioning log for a tenant (useful for debugging failed provisioning)."""
    result = await session.exec(
        select(TenantProvisionLog)
        .where(TenantProvisionLog.org_id == tenant_id)
        .order_by(TenantProvisionLog.occurred_at)
    )
    logs = result.all()
    return [
        ProvisionLogOut(
            id=l.id,
            org_id=l.org_id,
            step=l.step,
            status=l.status,
            detail=l.detail,
            occurred_at=l.occurred_at.isoformat(),
        )
        for l in logs
    ]


@app.get("/health")
async def health():
    return {"service": "tenant-mgmt", "status": "ok"}


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "ScopeSentinel Tenant Management", "version": "1.0.0", "docs": "/docs"}
