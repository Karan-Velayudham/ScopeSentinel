import os
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

# Workflows
from workflows.react_workflow import AgentReActWorkflow
from workflows.workflow_yaml_workflow import WorkflowYamlWorkflow

# Activities — ReAct agent loop
from activities.react_activities import (
    get_agent_config_activity,
    llm_reasoning_activity,
    execute_tool_activity,
    log_event_activity,
    update_run_status_activity,
    get_org_id_activity,
)

# Activities — YAML workflow execution
from activities.workflow_activities import get_workflow_config_activity

# Activities — legacy / specialist (kept for backward compatibility)
from activities.agent_activities import (
    fetch_ticket_activity,
    planning_activity,
    coder_activity,
    index_repo_activity,
    analyzer_activity,
)


async def main():
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    print(f"Connecting to Temporal server at {temporal_address}...")

    # Retry loop: wait for Temporal server to be reachable
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
        # Registered workflow types:
        #   AgentReActWorkflow  — drives any Agent created in the UI (fully data-driven)
        #   WorkflowYamlWorkflow — drives any YAML Workflow created in the UI
        workflows=[AgentReActWorkflow, WorkflowYamlWorkflow],
        activities=[
            # ReAct loop
            get_agent_config_activity,
            llm_reasoning_activity,
            execute_tool_activity,
            log_event_activity,
            update_run_status_activity,
            get_org_id_activity,
            # YAML workflow
            get_workflow_config_activity,
            # Legacy / specialist activities
            fetch_ticket_activity,
            planning_activity,
            coder_activity,
            index_repo_activity,
            analyzer_activity,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
