"""
models.py — AuditEvent table for the Audit Service (Epic 5.3.1)

Append-only: no UPDATE or DELETE on this table ever.
Rows are written by the Redpanda consumer in main.py.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class AuditEvent(SQLModel, table=True):
    """
    Immutable record of a platform action.
    
    Fields:
      org_id        — which tenant this event belongs to
      user_id       — who performed the action (None = system)
      action        — verb: create_run, approve_hitl, invite_user, etc.
      resource_type — what kind of thing was acted on: run, user, workflow, etc.
      resource_id   — the ID of the specific resource
      payload_json  — full request/event payload for forensic detail
      occurred_at   — when the event happened (immutable)
    """
    __tablename__ = "audit_events"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    org_id: str = Field(index=True)
    user_id: Optional[str] = Field(default=None, index=True)
    action: str = Field(index=True)
    resource_type: Optional[str] = Field(default=None, index=True)
    resource_id: Optional[str] = Field(default=None, index=True)
    payload_json: Optional[str] = Field(default=None)
    occurred_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True), index=True)
