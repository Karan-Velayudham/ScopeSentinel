import os
import httpx
from typing import Dict, Any, List
from adapters.base import BaseOAuthAdapter, Capability
import structlog

logger = structlog.get_logger(__name__)

class GmailAdapter(BaseOAuthAdapter):
    provider_name = "gmail"

    def __init__(self):
        self.client_id = os.environ.get("GMAIL_CLIENT_ID")
        self.client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
        self.mcp_url = os.environ.get("GMAIL_MCP_URL")

    def info(self) -> Dict[str, Any]:
        return {
            "id": "gmail",
            "name": "Gmail",
            "description": "Email integration for managing and sending mail via Google.",
            "category": "Communication",
            "icon_url": "https://upload.wikimedia.org/wikipedia/commons/4/4e/Gmail_Icon.png",
            "auth_type": "oauth"
        }

    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        scopes = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send"
        import urllib.parse
        scopes_encoded = urllib.parse.quote(scopes)
        redirect_encoded = urllib.parse.quote(redirect_uri)
        client_id_encoded = urllib.parse.quote(self.client_id or "")
        
        return (
            f"https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={client_id_encoded}"
            f"&response_type=code"
            f"&scope={scopes_encoded}"
            f"&redirect_uri={redirect_encoded}"
            f"&state={urllib.parse.quote(state)}"
            f"&access_type=offline"
            f"&prompt=consent"
        )

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri
                }
            )
            res.raise_for_status()
            data = res.json()
            
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token", ""),
                "expires_in": data.get("expires_in", 3600),
                "scopes": data.get("scope", "").split(" ")
            }

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token
                }
            )
            res.raise_for_status()
            data = res.json()
            
            return {
                "access_token": data["access_token"],
                "refresh_token": refresh_token, # Google usually doesn't send a new refresh token
                "expires_in": data.get("expires_in", 3600),
                "scopes": data.get("scope", "").split(" ")
            }

    async def discover_capabilities(self, access_token: str) -> List[Capability]:
        if not self.mcp_url:
            logger.warning("gmail_adapter.no_mcp_url_configured")
            return []
            
        from mcp.client.streamable_http import streamablehttp_client
        from mcp.client.session import ClientSession
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            logger.info("gmail_adapter.discover_capabilities_started", url=self.mcp_url)
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
                    logger.info("gmail_adapter.discover_capabilities_success", count=len(capabilities))
                    return capabilities
        except Exception as e:
            import traceback
            logger.error("gmail_adapter.discover_capabilities_failed", 
                         error=str(e), traceback=traceback.format_exc())
            return []

    async def execute_tool(self, tool_name: str, arguments: dict, access_token: str, provider_metadata: dict) -> Any:
        if not self.mcp_url:
            raise ValueError("GMAIL_MCP_URL is not configured for this environment.")
            
        from mcp.client.streamable_http import streamablehttp_client
        from mcp.client.session import ClientSession
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with streamablehttp_client(self.mcp_url, headers=headers) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                actual_tool_name = tool_name
                if tool_name.startswith(f"{self.provider_name}."):
                    actual_tool_name = tool_name[len(self.provider_name)+1:]
                
                logger.info("gmail_adapter.calling_tool", tool=actual_tool_name, args_keys=list(arguments.keys()))
                
                result = await session.call_tool(actual_tool_name, arguments)
                dump = result.model_dump()
                logger.info("gmail_adapter.tool_result", is_error=dump.get("isError"))

                return dump
