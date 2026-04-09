"""
provisioner.py — Core provisioning logic for the Tenant Management Service

Handles:
  1. PostgreSQL schema creation + Alembic baseline migrations
  2. Redpanda topic creation per tenant
  3. Qdrant collection creation per tenant

Each step is logged to `tenant_provision_logs` for observability and retries.
"""

import json
import os
import asyncio
from typing import Optional

import structlog
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Org, TenantProvisionLog, TenantStatus

logger = structlog.get_logger(__name__)

# Vector dimension for bge-large embedding model (Phase 4 knowledge layer)
EMBEDDING_DIM = 1024

# Redpanda / Kafka settings
REDPANDA_BROKERS = os.environ.get("REDPANDA_BROKERS", "localhost:19092")

# Qdrant settings
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))

# Topic definitions created per tenant
TENANT_TOPICS = [
    "events",    # General inbound events from webhook-receiver
    "audit",     # Audit events consumed by the audit service
    "metering",  # Metering events consumed by the metering service
]


async def _log_step(
    session: AsyncSession,
    org_id: str,
    step: str,
    status: str,
    detail: Optional[str] = None,
) -> None:
    entry = TenantProvisionLog(org_id=org_id, step=step, status=status, detail=detail)
    session.add(entry)
    await session.commit()


async def provision_tenant(org: Org, session: AsyncSession) -> None:
    """
    Full provisioning sequence for a new tenant.
    Steps run in order; failures are logged but do not stop subsequent steps
    so partial state can be inspected and retried.
    """
    log = logger.bind(org_id=org.id, org_slug=org.slug)

    # --- Step 1: PostgreSQL schema ---
    try:
        await _create_pg_schema(org.id, session)
        await _log_step(session, org.id, "create_pg_schema", "ok")
        log.info("provisioner.pg_schema_created", schema=f"tenant_{org.id}")
    except Exception as exc:
        await _log_step(session, org.id, "create_pg_schema", "error", str(exc))
        log.error("provisioner.pg_schema_failed", error=str(exc))
        raise

    # --- Step 2: Redpanda topics ---
    try:
        await _create_redpanda_topics(org.id)
        await _log_step(session, org.id, "create_redpanda_topics", "ok")
        log.info("provisioner.redpanda_topics_created", org_id=org.id)
    except Exception as exc:
        await _log_step(session, org.id, "create_redpanda_topics", "error", str(exc))
        log.error("provisioner.redpanda_topics_failed", error=str(exc))
        # Non-fatal — continue provisioning

    # --- Step 3: Qdrant collection ---
    try:
        _create_qdrant_collection(org.id)
        await _log_step(session, org.id, "create_qdrant_collection", "ok")
        log.info("provisioner.qdrant_collection_created", collection=f"org_{org.id}_knowledge")
    except Exception as exc:
        await _log_step(session, org.id, "create_qdrant_collection", "error", str(exc))
        log.error("provisioner.qdrant_collection_failed", error=str(exc))
        # Non-fatal — continue provisioning

    # --- Mark org as active ---
    org.status = TenantStatus.ACTIVE
    session.add(org)
    await session.commit()
    log.info("provisioner.tenant_active")


async def deprovision_tenant(org: Org, session: AsyncSession) -> None:
    """
    Soft deprovision: marks org as deprovisioned. Does NOT drop the PG schema
    or delete Redpanda topics immediately (preserve for audit / data recovery).
    Those are separate admin operations.
    """
    log = logger.bind(org_id=org.id)
    org.status = TenantStatus.DEPROVISIONED
    session.add(org)
    await session.commit()
    await _log_step(session, org.id, "deprovision", "ok", "Org deprovisioned (data retained)")
    log.info("provisioner.deprovisioned")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _create_pg_schema(org_id: str, session: AsyncSession) -> None:
    """
    Create a dedicated PostgreSQL schema for the tenant and run base DDL.
    The schema name is `tenant_<org_id>` (UUID, so safe for identifiers after stripping dashes).
    """
    # PostgreSQL identifiers can't use hyphens so we strip them
    safe_id = org_id.replace("-", "_")
    schema_name = f"tenant_{safe_id}"

    # Use raw connection to run schema-level DDL
    await session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
    await session.commit()

    # Set search path and create tenant-specific tables
    await session.execute(text(f"SET LOCAL search_path TO {schema_name}, public"))

    tenant_ddl = [
        f"""CREATE TABLE IF NOT EXISTS {schema_name}.workflows (
            id VARCHAR PRIMARY KEY,
            org_id VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            description VARCHAR,
            version INT DEFAULT 1,
            status VARCHAR DEFAULT 'draft',
            yaml_content TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );""",

        f"""CREATE TABLE IF NOT EXISTS {schema_name}.workflow_runs (
            id VARCHAR PRIMARY KEY,
            org_id VARCHAR NOT NULL,
            workflow_id VARCHAR,
            agent_id VARCHAR,
            ticket_id VARCHAR,
            inputs_json TEXT,
            output_json TEXT,
            status VARCHAR DEFAULT 'PENDING',
            trigger_type VARCHAR DEFAULT 'manual',
            temporal_workflow_id VARCHAR,
            dry_run BOOLEAN DEFAULT FALSE,
            plan_json TEXT,
            error_message TEXT,
            total_tokens INT,
            prompt_tokens INT,
            completion_tokens INT,
            estimated_cost FLOAT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );""",

        f"""CREATE TABLE IF NOT EXISTS {schema_name}.run_steps (
            id VARCHAR PRIMARY KEY,
            run_id VARCHAR NOT NULL,
            step_name VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'PENDING',
            input_json TEXT,
            output_json TEXT,
            error_message TEXT,
            started_at TIMESTAMPTZ,
            finished_at TIMESTAMPTZ,
            total_tokens INT,
            prompt_tokens INT,
            completion_tokens INT,
            estimated_cost FLOAT
        );""",

        f"""CREATE TABLE IF NOT EXISTS {schema_name}.hitl_events (
            id VARCHAR PRIMARY KEY,
            run_id VARCHAR NOT NULL,
            action VARCHAR NOT NULL,
            feedback TEXT,
            decided_by_id VARCHAR,
            decided_at TIMESTAMPTZ DEFAULT NOW()
        );""",

        f"""CREATE TABLE IF NOT EXISTS {schema_name}.agents (
            id VARCHAR PRIMARY KEY,
            org_id VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            description TEXT,
            identity TEXT NOT NULL,
            model VARCHAR DEFAULT 'gpt-4o',
            tools_json TEXT DEFAULT '[]',
            max_iterations INT DEFAULT 10,
            memory_mode VARCHAR DEFAULT 'SESSION',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );""",

        f"""CREATE TABLE IF NOT EXISTS {schema_name}.installed_connectors (
            id VARCHAR PRIMARY KEY,
            org_id VARCHAR NOT NULL,
            connector_id VARCHAR NOT NULL,
            config_json TEXT DEFAULT '{{}}',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );"""
    ]

    for stmt in tenant_ddl:
        await session.execute(text(stmt))
    
    await session.commit()


async def _create_redpanda_topics(org_id: str) -> None:
    """Create per-tenant Redpanda topics: t.<org_id>.events, .audit, .metering"""
    admin = AIOKafkaAdminClient(bootstrap_servers=REDPANDA_BROKERS)
    await admin.start()
    try:
        # Check existing topics to be idempotent
        existing_topics = await admin.list_topics()
        
        new_topics = []
        for suffix in TENANT_TOPICS:
            topic_name = f"t.{org_id}.{suffix}"
            if topic_name not in existing_topics:
                new_topics.append(
                    NewTopic(
                        name=topic_name,
                        num_partitions=3,
                        replication_factor=1,
                    )
                )
        
        if new_topics:
            await admin.create_topics(new_topics)
            logger.info("provisioner.redpanda_topics_created", org_id=org_id, count=len(new_topics))
        else:
            logger.info("provisioner.redpanda_topics_already_exist", org_id=org_id)
    finally:
        await admin.close()


def _create_qdrant_collection(org_id: str) -> None:
    """Create a dedicated Qdrant collection for the tenant's knowledge base."""
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    collection_name = f"org_{org_id}_knowledge"

    # Check if it already exists (idempotent)
    existing = [c.name for c in client.get_collections().collections]
    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )
