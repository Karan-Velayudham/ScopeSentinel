from typing import Dict, List, Any, Optional
import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

class ToolSchema(BaseModel):
    server_name: str
    name: str
    description: str
    input_schema: dict

class ToolRegistry:
    def __init__(self):
        # server_name -> tool_name -> ToolSchema
        self._tools: Dict[str, Dict[str, ToolSchema]] = {}

    def register_tools(self, server_name: str, tools: List[Any]):
        if server_name not in self._tools:
            self._tools[server_name] = {}
            
        for t in tools:
            # Extract standard MCP attributes
            name = getattr(t, "name", str(t))
            description = getattr(t, "description", "")
            # agentscope often nested this or uses inputSchema
            input_schema = getattr(t, "inputSchema", {})
            if hasattr(t, "model_dump"):
                dump = t.model_dump()
                input_schema = dump.get("inputSchema", input_schema)
            
            self._tools[server_name][name] = ToolSchema(
                server_name=server_name,
                name=name,
                description=description,
                input_schema=input_schema
            )
            logger.debug("registry.tool_registered", server=server_name, tool=name)
        
        logger.info("registry.tools_registered_for_server", server=server_name, count=len(tools))

    def get_all_tools(self, org_id: Optional[str] = None) -> List[ToolSchema]:
        all_tools = []
        for server_name, server_tools in self._tools.items():
            if server_name.startswith("oauth_"):
                if org_id and not server_name.endswith(f"_{org_id}"):
                    continue
            all_tools.extend(server_tools.values())
        return all_tools

    def get_tool(self, server_name: str, tool_name: str) -> Optional[ToolSchema]:
        return self._tools.get(server_name, {}).get(tool_name)

tool_registry = ToolRegistry()
