import os
import asyncio
from typing import Dict, Any, List
from temporalio import activity, workflow
from temporalio.exceptions import ApplicationError

import agentscope
from agentscope.model import OpenAIChatModel
from mcp_pool import load_client_pool
from agents.planner_agent import PlannerAgent, PlannerOutput
from agents.coder_agent import CoderAgent, CoderOutput
from agents.analyzer_agent import AnalyzerAgent, AnalyzerOutput
from exceptions import ConfigurationError
from io_capture import save_step_io_sync
from db_sync import sync_run_progress, get_agent
from tools.mcp_server import index_repository

@activity.defn
async def index_repo_activity(directory: str, repo_id: str) -> str:
    """Index a repository for semantic search."""
    return await index_repository(directory, repo_id)

def _get_run_id() -> str:
    wf_id = activity.info().workflow_id
    if wf_id.startswith("agent-workflow-"):
        return wf_id[len("agent-workflow-"):]
    return wf_id

def _build_model(model_name: str = "gpt-4o") -> OpenAIChatModel:
    """Initialize OpenAIChatModel via LiteLLM proxy if configured."""
    api_key = os.environ.get("LITELLM_MASTER_KEY", "sk-1234")
    base_url = os.environ.get("LITELLM_URL")
    
    client_kwargs = {}
    if base_url:
        client_kwargs["base_url"] = base_url
    
    return OpenAIChatModel(
        model_name=model_name,
        api_key=api_key if base_url else os.environ.get("OPENAI_API_KEY"),
        client_kwargs=client_kwargs,
        stream=False,
    )

async def _save_io(step_name: str, payload: dict, is_input: bool):
    run_id = activity.info().workflow_id
    await asyncio.to_thread(save_step_io_sync, run_id, step_name, payload, is_input)

@activity.defn
async def fetch_ticket_activity(ticket_id: str) -> str:
    run_id = _get_run_id()
    await sync_run_progress(run_id, status="RUNNING")
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
    run_id = _get_run_id()
    await _save_io("planning", args, True)
    ticket_id = args["ticket_id"]
    model_name = args.get("model_name", "gpt-4o")
    agentscope.init(project="ScopeSentinel", name="PlannerRun")
    model = _build_model(model_name)
    
    clients, tool_registry = await load_client_pool("mcp_servers.yaml")
    try:
        agent_id = args.get("agent_id")
        custom_prompt = None
        if agent_id:
            agent_data = await get_agent(agent_id)
            if agent_data:
                custom_prompt = agent_data.get("identity")
                model_name = agent_data.get("model", model_name)
        
        planner = PlannerAgent(model=model, system_prompt=custom_prompt)
        plan: PlannerOutput = await planner.plan(ticket_id, tool_registry)
        
        usage = {
            "prompt_tokens": plan.prompt_tokens,
            "completion_tokens": plan.completion_tokens,
            "total_tokens": plan.total_tokens
        }
        
        result = {
            "raw_plan": plan.raw_plan,
            "architecture_notes": plan.architecture_notes,
            "steps": plan.steps,
            "usage": usage
        }
        
        await sync_run_progress(
            run_id, 
            status="WAITING_HITL", 
            prompt_tokens=plan.prompt_tokens, 
            completion_tokens=plan.completion_tokens
        )
        await _save_io("planning", result, False)
        return result
    finally:
        for client in clients:
            await client.close()

@activity.defn
async def coder_activity(args: dict) -> dict:
    run_id = _get_run_id()
    await sync_run_progress(run_id, status="RUNNING")
    await _save_io("coder", {"ticket_id": args["ticket_id"], "plan_steps": args["plan_dict"]["steps"]}, True)
    
    ticket_id = args["ticket_id"]
    ticket_content = args["ticket_content"]
    plan_dict = args["plan_dict"]
    model_name = args.get("model_name", "gpt-4o")
    
    agentscope.init(project="ScopeSentinel", name="CoderRun")
    model = _build_model(model_name)
    
    clients, tool_registry = await load_client_pool("mcp_servers.yaml")
    try:
        reconstructed_plan = PlannerOutput(
            ticket_id=ticket_id,
            summary="Approved",
            steps=plan_dict["steps"],
            architecture_notes=plan_dict.get("architecture_notes", ""),
            raw_plan=plan_dict["raw_plan"]
        )
        
        agent_id = args.get("agent_id")
        custom_prompt = None
        if agent_id:
            agent_data = await get_agent(agent_id)
            if agent_data:
                custom_prompt = agent_data.get("identity")
                model_name = agent_data.get("model", model_name)

        coder = CoderAgent(model=model, system_prompt=custom_prompt)
        coder_res: CoderOutput = await coder.code_with_validation(
            ticket_id=ticket_id,
            ticket_content=ticket_content,
            plan=reconstructed_plan,
            tool_registry=tool_registry,
        )
        
        usage = {
            "prompt_tokens": coder_res.prompt_tokens,
            "completion_tokens": coder_res.completion_tokens,
            "total_tokens": coder_res.total_tokens
        }
        
        result = {
            "files_written": coder_res.files_written if coder_res.files_written else [],
            "usage": usage
        }
        
        await sync_run_progress(
            run_id, 
            status="SUCCEEDED", 
            prompt_tokens=coder_res.prompt_tokens, 
            completion_tokens=coder_res.completion_tokens
        )
        await _save_io("coder", result, False)
        return result
    finally:
        for client in clients:
            await client.close()

@activity.defn
async def analyzer_activity(args: dict) -> dict:
    run_id = _get_run_id()
    await sync_run_progress(run_id, status="RUNNING")
    await _save_io("analyzer", args, True)
    
    ticket_id = args["ticket_id"]
    ticket_content = args["ticket_content"]
    plan_dict = args["plan_dict"]
    files_written = args["files_written"]
    workspace_path = args["workspace_path"]
    model_name = args.get("model_name", "gpt-4o")
    
    agentscope.init(project="ScopeSentinel", name="AnalyzerRun")
    model = _build_model(model_name)
    
    try:
        agent_id = args.get("agent_id")
        custom_prompt = None
        if agent_id:
            agent_data = await get_agent(agent_id)
            if agent_data:
                custom_prompt = agent_data.get("identity")
                model_name = agent_data.get("model", model_name)

        reconstructed_plan = PlannerOutput(
            ticket_id=ticket_id,
            summary="Approved",
            steps=plan_dict["steps"],
            architecture_notes=plan_dict.get("architecture_notes", ""),
            raw_plan=plan_dict["raw_plan"]
        )
        
        analyzer = AnalyzerAgent(model=model, system_prompt=custom_prompt)
        res = await analyzer.analyze(
            ticket_id=ticket_id,
            ticket_content=ticket_content,
            plan=reconstructed_plan,
            files_written=files_written,
            workspace_path=workspace_path
        )
        
        result = {
            "passed": res.passed,
            "feedback": res.feedback,
            "usage": {
                "prompt_tokens": res.prompt_tokens,
                "completion_tokens": res.completion_tokens,
                "total_tokens": res.total_tokens
            }
        }
        
        await sync_run_progress(
            run_id, 
            status="SUCCEEDED",
            prompt_tokens=res.prompt_tokens, 
            completion_tokens=res.completion_tokens,
            analysis_passed=res.passed,
            analysis_feedback=res.feedback
        )
        await _save_io("analyzer", result, False)
        return result
    finally:
        pass
