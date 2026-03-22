from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import structlog
from core.connection_manager import connection_manager
from core.registry import tool_registry

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/connections", tags=["connections"])

class StdioConnectRequest(BaseModel):
    server_name: str
    command: str
    args: List[str] = []
    env: Optional[Dict[str, str]] = None

@router.post("/stdio")
async def connect_stdio_server(req: StdioConnectRequest):
    """Connects a new MCP Server via stdio and discovers its tools."""
    try:
        client = await connection_manager.connect_stdio(
            server_name=req.server_name,
            command=req.command,
            args=req.args,
            env=req.env or {}
        )
        
        # Discover tools
        tool_list = await client.list_tools()
        
        # Register them
        tool_registry.register_tools(req.server_name, tool_list)
        
        return {
            "status": "connected",
            "server_name": req.server_name,
            "tools_discovered": len(tool_list)
        }
    except Exception as exc:
        logger.error("api.connect_stdio_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("")
async def list_connections():
    """List actively connected servers."""
    return {"servers": list(connection_manager.clients.keys())}
