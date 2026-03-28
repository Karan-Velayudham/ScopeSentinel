import os
import json
import asyncio
import httpx
from datetime import datetime
from pydantic_settings import BaseSettings
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class Settings(BaseSettings):
    redpanda_brokers: str = os.getenv("REDPANDA_BROKERS", "localhost:19092")
    webhook_topic: str = os.getenv("WEBHOOK_TOPIC", "incoming-events")
    api_url: str = os.getenv("API_URL", "http://172.25.0.17:8000")
    internal_auth_token: str = os.getenv("INTERNAL_AUTH_TOKEN", "")

settings = Settings()
client: httpx.AsyncClient = None # type: ignore

async def process_event(event_data: dict):
    print(f"DEBUG: Processing event from {event_data.get('source')} - API_URL is {settings.api_url}")
    source = event_data.get("source")
    event_type = event_data.get("event_type")
    org_id = event_data.get("org_id")
    
    if source == "jira" and event_type == "jira:issue_created":
        # Extract Jira Key (e.g., SCRUM-10)
        issue = event_data.get("payload", {}).get("issue", {})
        ticket_id = issue.get("key")
        
        if ticket_id and org_id:
            try:
                print(f"Detected new Jira issue {ticket_id} for org {org_id}. Triggering agent...")
                # 1. Find a default agent for this org
                agents_resp = await client.get(
                    f"{settings.api_url}/api/agents/",
                    headers={
                        "X-ScopeSentinel-Org-ID": org_id,
                        "Authorization": f"Bearer {settings.internal_auth_token}"
                    }
                )
                agents_resp.raise_for_status()
                agents = agents_resp.json().get("items", [])
                if not agents:
                    print(f"No agents found for org {org_id}. Skipping trigger.")
                    return
                
                agent_id = agents[0]["id"]
                
                # 2. Trigger the run
                response = await client.post(
                    f"{settings.api_url}/api/runs/",
                    headers={
                        "X-ScopeSentinel-Org-ID": org_id,
                        "Authorization": f"Bearer {settings.internal_auth_token}"
                    },
                    json={
                        "ticket_id": ticket_id,
                        "workflow_id": "auto-jira-trigger",
                        "inputs": {"agent_id": agent_id}
                    }
                )
                response.raise_for_status()
                print(f"Triggered run {response.json().get('run_id')} for {ticket_id}")
            except Exception as e:
                print(f"Failed to trigger run: {e}")
    elif source == "system" and event_type == "cron.tick":
        print("Received cron.tick event. Evaluating scheduled workflows...")

async def consume():
    consumer = AIOKafkaConsumer(
        settings.webhook_topic,
        bootstrap_servers=settings.redpanda_brokers,
        auto_offset_reset="latest"
    )
    
    while True:
        try:
            await consumer.start()
            print(f"Connected to Redpanda at {settings.redpanda_brokers}")
            break
        except Exception as e:
            print(f"Waiting for Redpanda... {e}")
            await asyncio.sleep(5)

    try:
        while True:
            # Poll for messages
            messages = await consumer.getmany(timeout_ms=100)
            
            if not messages:
                continue

            for tp, msgs in messages.items():
                for msg in msgs:
                    print(f"Received message on {msg.topic} at offset {msg.offset}")
                    try:
                        event_data = json.loads(msg.value.decode("utf-8"))
                        await process_event(event_data)
                    except json.JSONDecodeError:
                        print("Failed to decode message as JSON")
                    except Exception as e:
                        print(f"Error processing message: {e}")
    finally:
        await consumer.stop()

async def cron_job():
    producer = AIOKafkaProducer(bootstrap_servers=settings.redpanda_brokers)
    try:
        await producer.start()
        event = {
            "source": "system",
            "event_type": "cron.tick",
            "payload": {"timestamp": datetime.utcnow().isoformat()}
        }
        await producer.send_and_wait(
            settings.webhook_topic,
            json.dumps(event).encode("utf-8")
        )
        print("Emitted cron.tick event")
    except Exception as e:
        print(f"Error emitting cron job: {e}")
    finally:
        await producer.stop()

async def main():
    global client
    client = httpx.AsyncClient(follow_redirects=True)
    
    # Start APScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(cron_job, 'interval', minutes=1)
    scheduler.start()
    print("Started APScheduler for cron triggers")
    
    # Start Consumer
    await consume()
    
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
