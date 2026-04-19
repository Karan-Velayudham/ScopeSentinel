"""
agent_utils.py — Shared helpers for building agentic prompts and executing tools.

Used by:
  - routers/chats.py   (agentic chat with tool loop)
  - routers/agents.py  (execute endpoint)
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional, Callable

import httpx
import structlog
from db.models import Agent, Skill

logger = structlog.get_logger(__name__)

ADAPTER_SERVICE_URL = os.getenv("ADAPTER_SERVICE_URL", "http://localhost:8005")


def sanitize_tool_name(name: str) -> str:
    """Ensure tool name complies with Anthropic/OpenAI constraints: ^[a-zA-Z0-9_-]+$"""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)


# ---------------------------------------------------------------------------
# Prompt Building
# ---------------------------------------------------------------------------

def build_system_prompt(agent: Agent, skills: list[Skill]) -> str:
    """
    Build a system prompt from agent instructions + attached skill instructions.
    Skills are injected in labelled sections so the LLM can distinguish them.
    """
    parts = [f"[System Instructions]\n{agent.instructions}"]
    for skill in skills:
        parts.append(f"[Skill: {skill.name}]\n{skill.instructions}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Capability-Gated Tool Definitions
# ---------------------------------------------------------------------------

# LiteLLM / OpenAI-compatible tool specification format
_TOOL_WEB_SEARCH = {
    "type": "function",
    "function": {
        "name": "platform_web_search",
        "description": "Search the web for up-to-date information on any topic.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query string.",
                }
            },
            "required": ["query"],
        },
    },
}

_TOOL_SEARCH_MEMORY = {
    "type": "function",
    "function": {
        "name": "platform_search_memory",
        "description": (
            "Search past conversations and the organisation knowledge base "
            "for relevant context, previous decisions, or historical information."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up in memory.",
                }
            },
            "required": ["query"],
        },
    },
}

_TOOL_WEB_FETCH = {
    "type": "function",
    "function": {
        "name": "platform_web_fetch",
        "description": "Fetch the content of a specific web page URL.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL of the page to fetch.",
                }
            },
            "required": ["url"],
        },
    },
}


def get_tools_for_agent(agent: Agent) -> list[dict]:
    """
    Return a list of LiteLLM-compatible tool definitions for the agent,
    gated by the capabilities dict stored on the Agent record.
    """
    caps: dict = agent.capabilities or {}
    tools = []

    if caps.get("web_search"):
        tools.append(_TOOL_WEB_SEARCH)

    if caps.get("web_fetch"):
        tools.append(_TOOL_WEB_FETCH)

    if caps.get("search_past_conversations"):
        tools.append(_TOOL_SEARCH_MEMORY)

    return tools


# ---------------------------------------------------------------------------
# Inline Tool Executors
# ---------------------------------------------------------------------------

async def execute_platform_tool(tool_name: str, tool_args: dict | str, org_id: str) -> str:
    """
    Execute a platform-native tool for the chat ReAct loop.
    Returns a string result suitable for appending to the messages list.

    Deliberately excludes MCP tools (Jira, GitHub) — those stay in
    the Temporal workflow execution path.
    """
    if isinstance(tool_args, str):
        try:
            tool_args = json.loads(tool_args)
        except json.JSONDecodeError:
            return f"Error: could not parse tool arguments: {tool_args}"

    if tool_name == "platform_web_search":
        return await _web_search(tool_args.get("query", ""))

    if tool_name == "platform_web_fetch":
        return await _web_fetch(tool_args.get("url", ""))

    if tool_name == "platform_search_memory":
        return await _search_memory(tool_args.get("query", ""), org_id)

    return f"Error: unknown tool '{tool_name}'"


# ---------------------------------------------------------------------------
# Remote MCP Tool Loader (from Adapter Service)
# ---------------------------------------------------------------------------

async def build_remote_tools_for_chat(
    org_id: str,
) -> tuple[list[dict], dict[str, Callable]]:
    """
    Fetch all MCP tools for the org from the adapter-service.

    Returns:
      - tool_definitions: OpenAI-format list to pass to the LLM
      - tool_registry:    dict of tool_name -> async callable for execution
    """
    tool_definitions: list[dict] = []
    tool_registry: dict[str, Callable] = {}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{ADAPTER_SERVICE_URL}/api/tools",
                params={"org_id": org_id},
            )
            resp.raise_for_status()
            tools_list = resp.json().get("tools", [])

        for tool in tools_list:
            server_name = tool.get("server_name", "")
            raw_tool_name = tool.get("name", "")
            tool_name = sanitize_tool_name(raw_tool_name)
            description = tool.get("description", "")
            input_schema = tool.get("input_schema") or {
                "type": "object", "properties": {}
            }

            tool_definitions.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": description,
                    "parameters": input_schema,
                },
            })

            # Capture loop variables in closure
            def _make_callable(s_name: str, t_name: str) -> Callable:
                async def _call(**kwargs) -> str:
                    url = f"{ADAPTER_SERVICE_URL}/api/tools/{s_name}/{t_name}/execute"
                    async with httpx.AsyncClient(timeout=60.0) as c:
                        r = await c.post(url, json={"arguments": kwargs})
                        r.raise_for_status()
                        return str(r.json().get("result", ""))
                return _call

            tool_registry[tool_name] = _make_callable(server_name, raw_tool_name)
            logger.debug("chat_mcp_tool_registered", tool=tool_name, original=raw_tool_name)

        logger.info("chat_mcp_tools_loaded", count=len(tool_definitions), org_id=org_id)

    except Exception as e:
        logger.error("chat_mcp_tools_load_failed", error=str(e), org_id=org_id)

    return tool_definitions, tool_registry


async def execute_remote_tool(
    tool_name: str,
    tool_args: dict | str,
    tool_registry: dict[str, Callable],
    org_id: str,
) -> str:
    """
    Execute a tool:
    1. Try the MCP remote registry (Jira, GitHub, etc.)
    2. Fall back to platform-native tools (web_search, web_fetch, search_memory)
    """
    if isinstance(tool_args, str):
        try:
            tool_args = json.loads(tool_args)
        except json.JSONDecodeError:
            return f"Error: could not parse tool arguments: {tool_args}"

    # 1. Remote MCP tool
    if tool_name in tool_registry:
        try:
            result = await tool_registry[tool_name](**tool_args)
            return str(result)
        except Exception as e:
            logger.error("chat_remote_tool_failed", tool=tool_name, error=str(e))
            return f"Error executing tool '{tool_name}': {e}"

    # 2. Platform-native fallback
    return await execute_platform_tool(tool_name, tool_args, org_id)



async def _web_search(query: str) -> str:
    """Perform a web search using the SerpAPI (or fallback stub)."""
    if not query:
        return "Error: empty search query."

    api_key = os.getenv("SERPAPI_KEY") or os.getenv("SERP_API_KEY")
    if not api_key:
        logger.warning("agent_utils.web_search_no_key", query=query)
        return f"[Web search not configured — no SERPAPI_KEY set. Query was: {query}]"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://serpapi.com/search",
                params={"q": query, "api_key": api_key, "engine": "google", "num": 5},
            )
            resp.raise_for_status()
            data = resp.json()

        results = data.get("organic_results", [])
        if not results:
            return "No web search results found."

        lines = []
        for r in results[:5]:
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            link = r.get("link", "")
            lines.append(f"- **{title}** ({link})\n  {snippet}")

        return "\n".join(lines)

    except Exception as e:
        logger.error("agent_utils.web_search_failed", error=str(e))
        return f"Web search failed: {e}"


async def _web_fetch(url: str) -> str:
    """Fetch and return the text content of a web page."""
    if not url:
        return "Error: empty URL."

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "ScopeSentinel/1.0"})
            resp.raise_for_status()
            # Return first 4000 chars to stay within context limits
            return resp.text[:4000]
    except Exception as e:
        logger.error("agent_utils.web_fetch_failed", url=url, error=str(e))
        return f"Failed to fetch URL '{url}': {e}"


async def _search_memory(query: str, org_id: str) -> str:
    """Search the organisation memory/knowledge base."""
    if not query:
        return "Error: empty search query."

    # Import here to avoid circular dependencies
    try:
        from knowledge.search import search_memory  # type: ignore
        result = await search_memory(query=query, org_id=org_id)
        return str(result) if result else "No relevant memories found."
    except ImportError:
        # Fallback: search chat messages directly via DB
        logger.warning("agent_utils.knowledge_not_available")
        return "[Memory search not available in this environment]"
    except Exception as e:
        logger.error("agent_utils.search_memory_failed", error=str(e))
        return f"Memory search failed: {e}"
