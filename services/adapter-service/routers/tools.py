from fastapi import APIRouter, Body, HTTPException
from typing import List, Dict, Any
from core.registry import tool_registry, ToolSchema
from core.router import tool_router

router = APIRouter(prefix="/api/tools", tags=["tools"])

@router.get("", response_model=Dict[str, List[ToolSchema]])
async def list_tools():
    """Returns a list of all discovered tools from all connected MCP Servers."""
    tools = tool_registry.get_all_tools()
    return {"tools": tools}

@router.post("/{server_name}/{tool_name}/execute")
async def execute_tool(
    server_name: str, 
    tool_name: str, 
    payload: Dict[str, Any] = Body(...)
):
    """Executes a specific tool on a specific MCP Server."""
    arguments = payload.get("arguments", {})
    result = await tool_router.execute_tool(server_name, tool_name, arguments)
    return {"result": result}
