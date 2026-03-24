import os
import json
import asyncio
from typing import Dict, Any
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
    payload: Dict[str, Any]

async def publish_to_redpanda(event: EventPayload):
    if not producer:
        print("Kafka producer is not initialized.")
        return
    
    try:
        message = event.model_dump_json().encode("utf-8")
        await producer.send_and_wait(settings.webhook_topic, message)
        print(f"Published event from {event.source} to topic {settings.webhook_topic}")
    except Exception as e:
        print(f"Error publishing to Redpanda: {e}")

@app.post("/webhook/{source}")
async def receive_webhook(source: str, request: Request, background_tasks: BackgroundTasks):
    """
    Generic webhook receiver.
    In a real implementation, you would validate the signature here based on the 'source'.
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
        event_type = payload.get("webhookEvent", "jira:issue_updated")

    event = EventPayload(
        source=source,
        event_type=event_type,
        payload=payload
    )

    background_tasks.add_task(publish_to_redpanda, event)

    return {"status": "accepted", "source": source, "event_type": event_type}

@app.get("/health")
def health_check():
    return {"status": "ok", "producer_active": producer is not None}
