"""
models.py — UsageEvent and UsageBucket tables for the Metering Service (Epic 5.4)
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


class UsageEvent(SQLModel, table=True):
    """
    Raw usage event — one row per billable action.
    Written by the Redpanda consumer in main.py.
    """
    __tablename__ = "usage_events"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    org_id: str = Field(index=True)
    event_type: str = Field(index=True)  # run | step | llm_call
    tokens: int = Field(default=0)
    occurred_at: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True), index=True)


class UsageBucket(SQLModel, table=True):
    """
    Hourly pre-aggregated usage — for fast dashboard queries.
    Populated by a separate background job (future Phase 5 cleanup).
    """
    __tablename__ = "usage_buckets"

    id: str = Field(default_factory=_new_uuid, primary_key=True)
    org_id: str = Field(index=True)
    period_start: datetime = Field(sa_type=DateTime(timezone=True), index=True)
    runs_count: int = Field(default=0)
    steps_count: int = Field(default=0)
    tokens_used: int = Field(default=0)
    llm_calls_count: int = Field(default=0)
