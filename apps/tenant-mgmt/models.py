"""
models.py — SQLModel tables owned by the Tenant Management Service

Tables live in the `public` schema (shared across the platform):
  - Org          — organisation record + per-tenant config
  - TenantSchema — tracks which tenant schemas have been provisioned
"""

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, JSON
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class TenantStatus(str, enum.Enum):
    PROVISIONING = "PROVISIONING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DEPROVISIONED = "DEPROVISIONED"


class Org(SQLModel, table=True):
    """Organisation record — one row per tenant."""
    __tablename__ = "orgs"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    name: str = Field(index=True, unique=True)
    slug: str = Field(index=True, unique=True)
    status: TenantStatus = Field(default=TenantStatus.PROVISIONING, index=True)

    # Per-org config stored as JSON (Epic 5.1.5)
    # Example: {"llm_model": "gpt-4o", "token_quota_per_month": 1000000, "features": {"rag": true}}
    tenant_config: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))


class TenantProvisionLog(SQLModel, table=True):
    """Tracks provisioning steps for each tenant — useful for debugging and retries."""
    __tablename__ = "tenant_provision_logs"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    org_id: str = Field(foreign_key="orgs.id", index=True)
    step: str  # e.g. "create_pg_schema", "create_redpanda_topic", "create_qdrant_collection"
    status: str  # "ok" | "error"
    detail: Optional[str] = Field(default=None)
    occurred_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))
