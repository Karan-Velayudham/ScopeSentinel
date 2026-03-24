import os
import httpx
import structlog
from typing import Dict, Callable, Any

logger = structlog.get_logger(__name__)

ADAPTER_SERVICE_URL = os.environ.get("ADAPTER_SERVICE_URL", "http://localhost:8002")

def _make_tool_callable(server_name: str, tool_name: str, schema: dict) -> Callable:
    """Creates an async callable that routes to the adapter service."""
    async def _execute_tool(**kwargs) -> Any:
        url = f"{ADAPTER_SERVICE_URL}/api/tools/{server_name}/{tool_name}/execute"
        payload = {"arguments": kwargs}
        logger.debug("remote_tool.executing", tool=tool_name, url=url)
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=60.0)
            resp.raise_for_status()
            return resp.json().get("result")
    
    # Attach schema metadata
    _execute_tool.__name__ = tool_name
    _execute_tool.__doc__ = schema.get("description", "")
    return _execute_tool

async def build_remote_tool_registry(org_id: str = None) -> Dict[str, Callable[..., Any]]:
    """
    Fetches all available tools from the generic Adapter Service 
    and returns a flat dictionary of tool_name -> Callable.
    """
    registry: Dict[str, Callable[..., Any]] = {}
    try:
        url = f"{ADAPTER_SERVICE_URL}/api/tools"
        params = {}
        if org_id:
            params["org_id"] = org_id
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            tools_list = data.get("tools", [])
            
            for tool in tools_list:
                server_name = tool.get("server_name")
                tool_name = tool.get("name")
                schema = tool.get("input_schema", {})
                
                if tool_name in registry:
                    logger.warning("remote_registry.tool_collision", tool=tool_name, server=server_name)
                    
                callable_fn = _make_tool_callable(server_name, tool_name, schema)
                registry[tool_name] = callable_fn
                logger.debug("remote_registry.registered", tool=tool_name)
                
            logger.info("remote_registry.loaded", count=len(registry))
            
    except Exception as exc:
        logger.error("remote_registry.fetch_failed", error=str(exc))
        
    return registry
