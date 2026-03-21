from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.agent_activities import (
        fetch_ticket_activity,
        planning_activity,
        coder_activity,
    )

default_retry_policy = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(seconds=5),
    maximum_interval=timedelta(minutes=1),
)

@workflow.defn
class AgentWorkflow:
    def __init__(self) -> None:
        self.hitl_decision = None

    @workflow.signal(name="hitl-decision-signal")
    async def hitl_signal(self, decision: dict) -> None:
        self.hitl_decision = decision

    @workflow.run
    async def run(self, ticket_id: str, model_name: str = "gpt-4o") -> dict:
        # Step 1: Fetch Ticket
        ticket_content = await workflow.execute_activity(
            fetch_ticket_activity,
            ticket_id,
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=default_retry_policy,
        )

        # Step 2: Plan
        plan_dict = await workflow.execute_activity(
            planning_activity,
            {"ticket_id": ticket_id, "ticket_content": ticket_content, "model_name": model_name},
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=default_retry_policy,
        )

        # Step 3: HITL verification
        # Wait until a signal updates hitl_decision
        await workflow.wait_condition(lambda: self.hitl_decision is not None)

        if self.hitl_decision.get("action") == "reject":
            return {"ticket_id": ticket_id, "status": "rejected"}

        # Step 4: Code
        coder_res = await workflow.execute_activity(
            coder_activity,
            {
                "ticket_id": ticket_id,
                "ticket_content": ticket_content,
                "plan_dict": plan_dict,
                "model_name": model_name
            },
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=default_retry_policy,
        )

        return {
            "ticket_id": ticket_id,
            "status": "completed",
            "files_written": coder_res.get("files_written", []),
            "usage": {
                "planning": plan_dict.get("usage"),
                "coder": coder_res.get("usage")
            }
        }
