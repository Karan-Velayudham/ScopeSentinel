"""
schemas.py — Pydantic request/response schemas for the Tenant Management API
"""

import json
from typing import Optional
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Request Bodies
# ---------------------------------------------------------------------------

class TenantCreate(BaseModel):
    name: str
    slug: str
    tenant_config: Optional[dict] = None


class TenantConfigUpdate(BaseModel):
    llm_model: Optional[str] = None
    token_quota_per_month: Optional[int] = None
    features: Optional[dict] = None


# ---------------------------------------------------------------------------
# Response Bodies
# ---------------------------------------------------------------------------

class TenantConfigOut(BaseModel):
    llm_model: str = "gpt-4o"
    token_quota_per_month: int = 1_000_000
    features: dict = {}


class TenantOut(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    tenant_config: Optional[TenantConfigOut] = None

    @classmethod
    def from_orm(cls, org) -> "TenantOut":
        config = None
        if org.tenant_config:
            raw = json.loads(org.tenant_config)
            config = TenantConfigOut(**raw)
        return cls(
            id=org.id,
            name=org.name,
            slug=org.slug,
            status=org.status,
            tenant_config=config,
        )


class ProvisionLogOut(BaseModel):
    id: str
    org_id: str
    step: str
    status: str
    detail: Optional[str]
    occurred_at: str
