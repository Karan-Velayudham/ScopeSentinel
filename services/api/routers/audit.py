import os
import json
import structlog
from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/audit", tags=["audit"])

REDPANDA_BROKERS = os.environ.get("REDPANDA_BROKERS", "localhost:19092")

class AuditEvent(BaseModel):
    org_id: str
    user_id: str
    action: str
    resource_type: str
    payload: dict

async def _publish_event(topic: str, event: dict):
    try:
        producer = AIOKafkaProducer(bootstrap_servers=REDPANDA_BROKERS)
        await producer.start()
        try:
            await producer.send_and_wait(topic, json.dumps(event).encode("utf-8"))
        finally:
            await producer.stop()
    except Exception as exc:
        logger.error("audit_router.publish_failed", error=str(exc))

@router.post("")
async def submit_audit_event(event: AuditEvent, background_tasks: BackgroundTasks):
    """Allows internal services (like adapter-service) to publish audit events."""
    topic = f"t.{event.org_id}.audit"
    background_tasks.add_task(_publish_event, topic, event.model_dump())
    return {"status": "ok"}
