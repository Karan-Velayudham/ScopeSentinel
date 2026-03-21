import os
import asyncio
from typing import Dict, Any, List
from temporalio import activity

with activity.unsafe.imports_passed_through():
    import agentscope
    from agentscope.model import OpenAIChatModel
    from mcp_pool import load_client_pool
    from agents.planner_agent import PlannerAgent, Plan, Task
    from agents.coder_agent import CoderAgent
    from exceptions import ConfigurationError
    from io_capture import save_step_io_sync

def _build_model() -> OpenAIChatModel:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ConfigurationError("OPENAI_API_KEY is not set.")
    return OpenAIChatModel(
        model_name="gpt-4o",
        api_key=api_key,
        stream=False,
    )

async def _save_io(step_name: str, payload: dict, is_input: bool):
    run_id = activity.info().workflow_id
    await asyncio.to_thread(save_step_io_sync, run_id, step_name, payload, is_input)

@activity.defn
async def fetch_ticket_activity(ticket_id: str) -> str:
    await _save_io("fetch_ticket", {"ticket_id": ticket_id}, True)
    
    clients, tool_registry = await load_client_pool("mcp_servers.yaml")
    try:
        fetch_func = tool_registry["fetch_jira_ticket"]
        res = await fetch_func(ticket_id=ticket_id)
        result = res.content[0]["text"] if hasattr(res, "content") else str(res)
        
        await _save_io("fetch_ticket", {"content": result}, False)
        return result
    finally:
        for client in clients:
            await client.close()

@activity.defn
async def planning_activity(args: dict) -> dict:
    await _save_io("planning", args, True)
    ticket_id = args["ticket_id"]
    agentscope.init(project="ScopeSentinel", name="PlannerRun")
    model = _build_model()
    
    clients, tool_registry = await load_client_pool("mcp_servers.yaml")
    try:
        planner = PlannerAgent(model=model)
        plan = await planner.plan(ticket_id, tool_registry)
        
        result = {
            "raw_plan": plan.raw_plan,
            "tasks": [{"id": t.id, "description": t.description} for t in plan.tasks]
        }
        await _save_io("planning", result, False)
        return result
    finally:
        for client in clients:
            await client.close()

@activity.defn
async def coder_activity(args: dict) -> List[str]:
    await _save_io("coder", {"ticket_id": args["ticket_id"], "plan_tasks": args["plan_dict"]["tasks"]}, True)
    
    ticket_id = args["ticket_id"]
    ticket_content = args["ticket_content"]
    plan_dict = args["plan_dict"]
    
    agentscope.init(project="ScopeSentinel", name="CoderRun")
    model = _build_model()
    
    clients, tool_registry = await load_client_pool("mcp_servers.yaml")
    try:
        reconstructed_plan = Plan(
            raw_plan=plan_dict["raw_plan"],
            tasks=[Task(**t) for t in plan_dict["tasks"]]
        )
        
        coder = CoderAgent(model=model)
        coder_res = await coder.code_with_validation(
            ticket_id=ticket_id,
            ticket_content=ticket_content,
            plan=reconstructed_plan,
            tool_registry=tool_registry,
        )
        result = coder_res.files_written if coder_res.files_written else []
        
        await _save_io("coder", {"files_written": result}, False)
        return result
    finally:
        for client in clients:
            await client.close()
