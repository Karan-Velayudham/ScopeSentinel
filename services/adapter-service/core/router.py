from typing import Any
import structlog
from fastapi import HTTPException
from core.connection_manager import connection_manager

logger = structlog.get_logger(__name__)

class ToolRouter:
    async def execute_tool(self, server_name: str, tool_name: str, arguments: dict) -> Any:
        if server_name.startswith("oauth_"):
            import httpx
            import os
            
            parts = server_name.split("_")
            provider = parts[1]
            org_id = parts[2]
            
            # Fetch token from internal API
            api_url = os.environ.get("API_URL", "http://localhost:8000")
            internal_token_url = f"{api_url}/api/oauth-connections/internal/{provider}/token"
            
            async with httpx.AsyncClient() as client:
                res = await client.get(internal_token_url, params={"org_id": org_id})
                if res.status_code != 200:
                    raise HTTPException(status_code=400, detail="Could not fetch tool capabilities, please reconnect")
                token_data = res.json()
                access_token = token_data["access_token"]
                import json
                provider_metadata = json.loads(token_data.get("provider_metadata", "{}"))
            
            # Find adapter and execute
            from routers.oauth import adapters_map
            adapter = adapters_map.get(provider)
            if not adapter:
                raise HTTPException(status_code=400, detail="Adapter not found")
                
            result = await adapter.execute_tool(tool_name, arguments, access_token, provider_metadata)
            
            # Send audit event
            import asyncio
            asyncio.create_task(self._send_audit(server_name, tool_name, arguments, org_id="oauth"))
            
            return result
            
            
        client = connection_manager.get_client(server_name)
        if not client:
            raise HTTPException(status_code=404, detail=f"Server '{server_name}' not connected")
        
        try:
            # We use the callable function mapped by agentscope.
            # StdIOStatefulClient automatically generates these callables and handles the JSONRPC.
            callable_fn = await client.get_callable_function(tool_name)
            result = await callable_fn(**arguments)
            
            # Send audit event
            import asyncio
            asyncio.create_task(self._send_audit(server_name, tool_name, arguments, org_id="global"))
            
            return result
        except Exception as exc:
            logger.error("router.tool_execution_failed", server=server_name, tool=tool_name, error=str(exc))
            raise HTTPException(status_code=500, detail=str(exc))

    async def _send_audit(self, server_name: str, tool_name: str, arguments: dict, org_id: str):
        try:
            import httpx
            import os
            api_url = os.environ.get("API_URL", "http://localhost:8000")
            
            actual_org = org_id
            if server_name.startswith("oauth_"):
                parts = server_name.split("_")
                if len(parts) > 2:
                    actual_org = parts[2]
            
            payload = {
                "org_id": actual_org,
                "user_id": "agent",  
                "action": f"execute_tool:{tool_name}",
                "resource_type": "tool_invocation",
                "payload": {"server": server_name, "arguments": arguments}
            }
            async with httpx.AsyncClient() as client:
                await client.post(f"{api_url}/api/audit", json=payload)
        except Exception as e:
            logger.warning("router.audit_log_failed", error=str(e), server=server_name)

tool_router = ToolRouter()
