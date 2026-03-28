import os
import json
import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from aiokafka import AIOKafkaProducer

class Settings(BaseSettings):
    redpanda_brokers: str = os.getenv("REDPANDA_BROKERS", "localhost:19092")
    webhook_topic: str = os.getenv("WEBHOOK_TOPIC", "incoming-events")

settings = Settings()

app = FastAPI(
    title="ScopeSentinel Webhook Receiver",
    description="Ingests external webhooks and publishes them to Redpanda",
    version="0.1.0"
)

# Global producer instance
producer: AIOKafkaProducer = None # type: ignore

@app.on_event("startup")
async def startup_event():
    global producer
    try:
        producer = AIOKafkaProducer(
            bootstrap_servers=settings.redpanda_brokers
        )
        await producer.start()
        print(f"Connected to Redpanda at {settings.redpanda_brokers}")
    except Exception as e:
        print(f"Failed to connect to Redpanda: {e}")
        # Not raising an exception here to allow the service to start,
        # but in production we might want to crash if we can't connect.

@app.on_event("shutdown")
async def shutdown_event():
    global producer
    if producer:
        await producer.stop()

class EventPayload(BaseModel):
    source: str
    event_type: str
    org_id: Optional[str] = None
    payload: Dict[str, Any]

async def publish_to_redpanda(event: EventPayload):
    if not producer:
        print("Kafka producer is not initialized.")
        return
    
    try:
        print(f"Publishing to {settings.webhook_topic}...")
        message = event.model_dump_json().encode("utf-8")
        await producer.send_and_wait(settings.webhook_topic, message)
        print(f"Successfully published event from {event.source} to topic {settings.webhook_topic}")
    except Exception as e:
        print(f"Error publishing to Redpanda: {e}")

@app.post("/webhook/{source}/{org_id}")
async def receive_webhook(source: str, org_id: str, request: Request, background_tasks: BackgroundTasks):
    """
    Generic webhook receiver with org scoping.
    URL: /webhook/jira/org-123
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Extract event type if possible
    event_type = "unknown"
    if source.lower() == "github":
        event_type = request.headers.get("X-GitHub-Event", "push")
    elif source.lower() == "jira":
        event_type = payload.get("webhookEvent", "jira:issue_created")

    event = EventPayload(
        source=source,
        event_type=event_type,
        org_id=org_id,
        payload=payload
    )

    try:
        await publish_to_redpanda(event)
    except Exception as e:
        print(f"FAILED TO PUBLISH: {e}")
        raise HTTPException(status_code=500, detail=f"Publish failed: {e}")

    return {"status": "accepted", "source": source, "event_type": event_type, "org_id": org_id}

@app.get("/health")
def health_check():
    return {"status": "ok", "producer_active": producer is not None}
