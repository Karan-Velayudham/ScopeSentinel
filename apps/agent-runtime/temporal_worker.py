import os
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from workflows.agent_workflow import AgentWorkflow
from workflows.react_workflow import AgentReActWorkflow
from activities.agent_activities import (
    fetch_ticket_activity,
    planning_activity,
    coder_activity,
    index_repo_activity,
    analyzer_activity,
)
from activities.react_activities import (
    get_agent_config_activity,
    llm_reasoning_activity,
    execute_tool_activity,
    log_event_activity,
    update_run_status_activity,
    get_org_id_activity,
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
        workflows=[AgentWorkflow, AgentReActWorkflow],
        activities=[
            fetch_ticket_activity,
            planning_activity,
            coder_activity,
            index_repo_activity,
            analyzer_activity,
            get_agent_config_activity,
            llm_reasoning_activity,
            execute_tool_activity,
            log_event_activity,
            update_run_status_activity,
            get_org_id_activity,
        ],
    )
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
