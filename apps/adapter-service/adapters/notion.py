import os
import httpx
from typing import Dict, Any, List
from adapters.base import BaseOAuthAdapter, Capability
import structlog
import base64

logger = structlog.get_logger(__name__)

class NotionAdapter(BaseOAuthAdapter):
    provider_name = "notion"

    def __init__(self):
        self.client_id = os.environ.get("NOTION_CLIENT_ID")
        self.client_secret = os.environ.get("NOTION_CLIENT_SECRET")
        self.mcp_url = os.environ.get("NOTION_MCP_URL")

    def info(self) -> Dict[str, Any]:
        return {
            "id": "notion",
            "name": "Notion",
            "description": "Productivity integration for pages and databases.",
            "category": "Productivity",
            "icon_url": "https://upload.wikimedia.org/wikipedia/commons/4/45/Notion_app_logo.png",
            "auth_type": "oauth"
        }

    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        import urllib.parse
        redirect_encoded = urllib.parse.quote(redirect_uri)
        client_id_encoded = urllib.parse.quote(self.client_id or "")
        
        return (
            f"https://api.notion.com/v1/oauth/authorize"
            f"?client_id={client_id_encoded}"
            f"&response_type=code"
            f"&owner=user"
            f"&redirect_uri={redirect_encoded}"
            f"&state={urllib.parse.quote(state)}"
        )

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        auth_bytes = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        auth_header = base64.b64encode(auth_bytes).decode("utf-8")

        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.notion.com/v1/oauth/token",
                json={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri
                },
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/json"
                }
            )
            res.raise_for_status()
            data = res.json()
            
            return {
                "access_token": data["access_token"],
                "refresh_token": "", # Notion tokens typically don't expire/refresh yet
                "expires_in": 0,
                "scopes": []
            }

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        # Notion doesn't standardly use refresh tokens, simply return an empty result securely.
        return {}

    async def discover_capabilities(self, access_token: str) -> List[Capability]:
        if not self.mcp_url:
            logger.warning("notion_adapter.no_mcp_url_configured")
            return []
            
        from mcp.client.streamable_http import streamablehttp_client
        from mcp.client.session import ClientSession
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            logger.info("notion_adapter.discover_capabilities_started", url=self.mcp_url)
            async with streamablehttp_client(self.mcp_url, headers=headers) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    
                    capabilities = []
                    for t in tools_result.tools:
                        capabilities.append(
                            Capability(
                                name=t.name,
                                description=t.description or "",
                                input_schema=t.inputSchema or {},
                                scopes_required=[]
                            )
                        )
                    logger.info("notion_adapter.discover_capabilities_success", count=len(capabilities))
                    return capabilities
        except Exception as e:
            import traceback
            logger.error("notion_adapter.discover_capabilities_failed", 
                         error=str(e), traceback=traceback.format_exc())
            return []

    async def execute_tool(self, tool_name: str, arguments: dict, access_token: str, provider_metadata: dict) -> Any:
        if not self.mcp_url:
            raise ValueError("NOTION_MCP_URL is not configured for this environment.")
            
        from mcp.client.streamable_http import streamablehttp_client
        from mcp.client.session import ClientSession
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with streamablehttp_client(self.mcp_url, headers=headers) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                actual_tool_name = tool_name
                if tool_name.startswith(f"{self.provider_name}."):
                    actual_tool_name = tool_name[len(self.provider_name)+1:]
                
                logger.info("notion_adapter.calling_tool", tool=actual_tool_name, args_keys=list(arguments.keys()))
                
                result = await session.call_tool(actual_tool_name, arguments)
                dump = result.model_dump()
                logger.info("notion_adapter.tool_result", is_error=dump.get("isError"))

                return dump
