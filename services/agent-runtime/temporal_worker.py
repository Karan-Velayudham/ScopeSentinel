import os
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from workflows.agent_workflow import AgentWorkflow
from activities.agent_activities import (
    fetch_ticket_activity,
    planning_activity,
    coder_activity,
)

async def main():
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    print(f"Connecting to Temporal server at {temporal_address}...")
    
    # Wait for Temporal server to be ready
    while True:
        try:
            client = await Client.connect(temporal_address)
            break
        except Exception as e:
            print(f"Waiting for Temporal server... {e}")
            await asyncio.sleep(5)

    print("Connected! Starting worker...")
    worker = Worker(
        client,
        task_queue="agent-task-queue",
        workflows=[AgentWorkflow],
        activities=[
            fetch_ticket_activity,
            planning_activity,
            coder_activity,
        ],
    )
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
