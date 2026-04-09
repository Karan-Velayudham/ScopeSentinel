"""
provisioner.py — Core provisioning logic for the Tenant Management Service

Handles:
  1. Redpanda topic creation per tenant
  2. Qdrant collection creation per tenant

All tenant data lives in the shared `public` PostgreSQL schema, isolated
by the `org_id` column on every table. No per-tenant PG schema is created.

Each step is logged to `tenant_provision_logs` for observability and retries.
"""

import os
from typing import Optional

import structlog
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
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
    "events",    # General inbound events
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

    # --- Step 1: Redpanda topics ---
    try:
        await _create_redpanda_topics(org.id)
        await _log_step(session, org.id, "create_redpanda_topics", "ok")
        log.info("provisioner.redpanda_topics_created", org_id=org.id)
    except Exception as exc:
        await _log_step(session, org.id, "create_redpanda_topics", "error", str(exc))
        log.error("provisioner.redpanda_topics_failed", error=str(exc))
        # Non-fatal — continue provisioning

    # --- Step 2: Qdrant collection ---
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
    Soft deprovision: marks org as deprovisioned. Does NOT delete Redpanda
    topics or Qdrant collections immediately (preserve for audit / data recovery).
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
