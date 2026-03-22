from typing import Any
import structlog
from fastapi import HTTPException
from core.connection_manager import connection_manager

logger = structlog.get_logger(__name__)

class ToolRouter:
    async def execute_tool(self, server_name: str, tool_name: str, arguments: dict) -> Any:
        client = connection_manager.get_client(server_name)
        if not client:
            raise HTTPException(status_code=404, detail=f"Server '{server_name}' not connected")
        
        try:
            # We use the callable function mapped by agentscope.
            # StdIOStatefulClient automatically generates these callables and handles the JSONRPC.
            callable_fn = await client.get_callable_function(tool_name)
            result = await callable_fn(**arguments)
            return result
        except Exception as exc:
            logger.error("router.tool_execution_failed", server=server_name, tool=tool_name, error=str(exc))
            raise HTTPException(status_code=500, detail=str(exc))

tool_router = ToolRouter()
