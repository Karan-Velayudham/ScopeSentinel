import os
import json
import asyncio
from typing import Dict, Any, List, Tuple
from temporalio import activity
from temporalio.exceptions import ApplicationError

import agentscope
from agentscope.model import OpenAIChatModel
from tools.remote_registry import build_remote_tool_registry
from db_sync import sync_run_progress, get_agent, get_skills_for_agent, log_run_event, get_run_org_id
from knowledge.search import search_memory
from aiokafka import AIOKafkaProducer
from datetime import datetime, timezone

REDPANDA_BROKERS = os.environ.get("REDPANDA_BROKERS", "localhost:19092")

@activity.defn
async def get_agent_config_activity(agent_id: str) -> dict:
    """Fetch agent persona, tools, and skills from DB."""
    agent = await get_agent(agent_id)
    if not agent:
        raise ApplicationError(f"Agent {agent_id} not found")
    
    skills = await get_skills_for_agent(agent_id)
    return {
        "id": agent["id"],
        "name": agent["name"],
        "identity": agent["identity"],
        "model": agent["model"],
        "tools": agent["tools"],
        "skills": skills,
        "memory_mode": agent.get("memory_mode", "session")
    }

def _build_model(model_name: str) -> OpenAIChatModel:
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

@activity.defn
async def llm_reasoning_activity(args: dict) -> dict:
    """Single-step LLM call for reasoning/tool selection."""
    messages = args["messages"]
    model_name = args["model"]
    tools = args.get("tools", [])
    
    model = _build_model(model_name)
    
    kwargs = {}
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
        
    try:
        response = await model(messages, **kwargs)
        
        # Extract content
        content = ""
        if hasattr(response, "content") and isinstance(response.content, list):
            for block in response.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    content = block["text"]
                    break
        if not content:
            content = str(response)
            
        # Extract tool calls safely
        tool_calls = []
        
        from structlog import get_logger
        log = get_logger(__name__)
        log.debug("llm.response_type", type=str(type(response)), content=str(response)[:200])

        # AgentScope ModelResponse objects (like ChatResponse) may have tool_calls attribute
        tc_list = None
        try:
            # First try getattr directly to avoid magic hasattr that might throw KeyError
            tc_list = getattr(response, "tool_calls", None)
            
            # If still None, check if it is a dict
            if tc_list is None and isinstance(response, dict):
                tc_list = response.get("tool_calls")
        except Exception as e:
            log.warning("llm.extraction_failed_early", error=str(e))
            
        if tc_list:
            for tc in tc_list:
                try:
                    # Handle both object-like and dict-like tool call structures
                    tc_id = getattr(tc, "id", None) if not isinstance(tc, dict) else tc.get("id")
                    func = getattr(tc, "function", None) if not isinstance(tc, dict) else tc.get("function")
                    
                    if func:
                        fn_name = getattr(func, "name", None) if not isinstance(func, dict) else func.get("name")
                        fn_args = getattr(func, "arguments", None) if not isinstance(func, dict) else func.get("arguments")
                        
                        tool_calls.append({
                            "id": tc_id,
                            "function": {
                                "name": fn_name,
                                "arguments": fn_args
                            }
                        })
                except Exception as e:
                    log.warning("llm.tool_call_extraction_failed", error=str(e))
                
        # Extract usage safely
        usage = {}
        if hasattr(response, "usage"):
            usage = response.usage
        elif isinstance(response, dict):
            usage = response.get("usage", {})
        
        return {
            "content": content,
            "tool_calls": tool_calls,
            "usage": usage
        }
    except Exception as e:
        raise ApplicationError(f"LLM Reasoning failed: {e}")

@activity.defn
async def execute_tool_activity(args: dict) -> dict:
    """Execute a specific tool via the remote registry or platform native tools."""
    tool_name = args["tool_name"]
    tool_args = args["tool_args"]
    org_id = args["org_id"]
    
    # Platform Native Tools
    if tool_name == "platform:search_memory":
        try:
            if isinstance(tool_args, str):
                tool_args = json.loads(tool_args)
            query = tool_args.get("query")
            if not query:
                return {"error": "Missing 'query' argument"}
            result = await search_memory(query=query, org_id=org_id)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}

    # Remote MCP Tools
    tool_registry, _ = await build_remote_tool_registry(org_id)
    if tool_name not in tool_registry:
        return {"error": f"Tool {tool_name} not found"}
    
    try:
        callable_fn = tool_registry[tool_name]
        # tool_args is a JSON string from LLM, parse it
        if isinstance(tool_args, str):
            tool_args = json.loads(tool_args)
            
        result = await callable_fn(**tool_args)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}

@activity.defn
async def log_event_activity(args: dict):
    """Log a RunEvent to the database and publish to Redpanda."""
    run_id = args["run_id"]
    event_type = args["event_type"]
    payload = args["payload"]
    org_id = args.get("org_id")
    
    # 1. DB Log
    await log_run_event(run_id, event_type, payload)
    
    # 2. Redpanda Publish (for SSE)
    if not org_id:
        org_id = await get_run_org_id(run_id)
        
    if org_id:
        try:
            topic = f"t.{org_id}.run-events"
            event = {
                "run_id": run_id,
                "event_type": event_type,
                "payload": payload,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            producer = AIOKafkaProducer(bootstrap_servers=REDPANDA_BROKERS)
            await producer.start()
            try:
                await producer.send_and_wait(topic, json.dumps(event).encode("utf-8"))
            finally:
                await producer.stop()
        except Exception as e:
            # Don't fail the whole workflow if Redpanda is down
            from structlog import get_logger
            get_logger(__name__).error("redpanda.publish_failed", error=str(e), run_id=run_id)

@activity.defn
async def update_run_status_activity(args: dict):
    """Update WorkflowRun status and usage. Also publish to metering."""
    run_id = args["run_id"]
    status = args.get("status")
    p_tokens = args.get("prompt_tokens", 0)
    c_tokens = args.get("completion_tokens", 0)
    
    # 1. DB Update
    await sync_run_progress(
        run_id=run_id,
        status=status,
        prompt_tokens=p_tokens,
        completion_tokens=c_tokens
    )
    
    # 2. Metering Publish
    if p_tokens > 0 or c_tokens > 0:
        try:
            org_id = await get_run_org_id(run_id)
            if org_id:
                topic = f"t.{org_id}.metering"
                payload = {
                    "org_id": org_id,
                    "run_id": run_id,
                    "event_type": "llm_usage",
                    "prompt_tokens": p_tokens,
                    "completion_tokens": c_tokens,
                    "total_tokens": p_tokens + c_tokens,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                producer = AIOKafkaProducer(bootstrap_servers=REDPANDA_BROKERS)
                await producer.start()
                try:
                    await producer.send_and_wait(topic, json.dumps(payload).encode("utf-8"))
                finally:
                    await producer.stop()
        except Exception as e:
            from structlog import get_logger
            get_logger(__name__).error("metering.publish_failed", error=str(e), run_id=run_id)

@activity.defn
async def get_org_id_activity(run_id: str) -> str:
    """Helper to get org_id for a run."""
    return await get_run_org_id(run_id)
