from fastapi import APIRouter, Body, HTTPException
from typing import List, Dict, Any
import os
import httpx
from core.registry import tool_registry, ToolSchema
from core.router import tool_router
from adapters.factory import adapter_factory
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/tools", tags=["tools"])

@router.get("", response_model=Dict[str, List[ToolSchema]])
async def list_tools(org_id: str = None):
    """Returns a list of all discovered tools, with lazy discovery for OAuth connectors."""
    if org_id:
        await _lazy_discover_oauth_tools(org_id)
        
    tools = tool_registry.get_all_tools(org_id)
    return { "tools": tools }

async def _lazy_discover_oauth_tools(org_id: str):
    """Fetches active OAuth connections from API and ensures their tools are registered."""
    api_url = os.environ.get("API_URL", "http://localhost:8000")
    internal_list_url = f"{api_url}/api/oauth-connections/internal/list?org_id={org_id}"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.get(internal_list_url)
            res.raise_for_status()
            connections = res.json()
            
            for conn in connections:
                provider = conn["provider"]
                server_id = f"oauth_{provider}_{org_id}"
                
                # If these tools are not in the registry yet, discover them
                if not tool_registry.get_tools_for_server(server_id):
                    logger.info("tools.lazy_discovery_triggered", provider=provider, org_id=org_id)
                    try:
                        adapter = adapter_factory.get_adapter(provider)
                        token_url = f"{api_url}/api/oauth-connections/internal/{provider}/token?org_id={org_id}"
                        token_res = await client.get(token_url)
                        token_res.raise_for_status()
                        token_data = token_res.json()
                        
                        capabilities = await adapter.discover_capabilities(token_data["access_token"])
                        
                        schemas = [
                            ToolSchema(
                                server_name=server_id,
                                name=f"{provider}.{cap.name}",
                                description=cap.description or "",
                                input_schema=cap.input_schema or {}
                            )
                            for cap in capabilities
                        ]
                        
                        tool_registry.register_tool_schemas(server_id, schemas)
                        logger.info("tools.lazy_discovery_success", provider=provider, count=len(schemas))
                    except Exception as e:
                        logger.error("tools.lazy_discovery_failed", provider=provider, error=str(e))
    except Exception as e:
        logger.error("tools.lazy_discovery_list_failed", error=str(e))

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
