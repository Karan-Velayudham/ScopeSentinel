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
    api_url: str = os.getenv("API_URL", "http://api:8000")

settings = Settings()

async def process_event(event_data: dict):
    source = event_data.get("source")
    event_type = event_data.get("event_type")
    
    if source == "github":
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.api_url}/api/runs",
                    json={"ticket_id": "SCRUM-8"}
                )
                print(f"Triggered run for github event: {response.status_code}")
        except Exception as e:
            print(f"Failed to trigger run: {e}")
    elif source == "system" and event_type == "cron.tick":
        print("Received cron.tick event. Evaluating scheduled workflows...")

async def consume():
    consumer = AIOKafkaConsumer(
        settings.webhook_topic,
        bootstrap_servers=settings.redpanda_brokers,
        group_id="trigger-engine-group"
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
        async for msg in consumer:
            print(f"Received message on {msg.topic}")
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
    # Start APScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(cron_job, 'interval', minutes=1)
    scheduler.start()
    print("Started APScheduler for cron triggers")
    
    # Start Consumer
    await consume()

if __name__ == "__main__":
    asyncio.run(main())
