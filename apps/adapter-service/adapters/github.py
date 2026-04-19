import os
import httpx
from typing import Dict, Any, List
from adapters.base import BaseOAuthAdapter, Capability
import structlog

logger = structlog.get_logger(__name__)

class GithubAdapter(BaseOAuthAdapter):
    provider_name = "github"

    def __init__(self):
        self.client_id = os.environ.get("GITHUB_CLIENT_ID")
        self.client_secret = os.environ.get("GITHUB_CLIENT_SECRET")
        self.mcp_url = os.environ.get("GITHUB_MCP_URL")

    def info(self) -> Dict[str, Any]:
        return {
            "id": "github",
            "name": "GitHub",
            "description": "Version control integration for repositories, issues, and PRs.",
            "category": "VCS",
            "icon_url": "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png",
            "auth_type": "oauth"
        }

    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        scopes = "repo user:email"
        import urllib.parse
        scopes_encoded = urllib.parse.quote(scopes)
        redirect_encoded = urllib.parse.quote(redirect_uri)
        client_id_encoded = urllib.parse.quote(self.client_id or "")
        
        return (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={client_id_encoded}"
            f"&scope={scopes_encoded}"
            f"&redirect_uri={redirect_encoded}"
            f"&state={urllib.parse.quote(state)}"
        )

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri
                },
                headers={"Accept": "application/json"}
            )
            res.raise_for_status()
            data = res.json()
            
            if "error" in data:
                raise ValueError(f"GitHub OAuth error: {data.get('error_description', data['error'])}")
            
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token", ""),
                "expires_in": data.get("expires_in", 0),
                "scopes": data.get("scope", "").split(",")
            }

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token
                },
                headers={"Accept": "application/json"}
            )
            res.raise_for_status()
            data = res.json()
            
            if "error" in data:
                raise ValueError(f"GitHub OAuth refresh error: {data.get('error_description', data['error'])}")
            
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token", ""),
                "expires_in": data.get("expires_in", 0),
                "scopes": data.get("scope", "").split(",")
            }

    async def discover_capabilities(self, access_token: str) -> List[Capability]:
        if not self.mcp_url:
            logger.warning("github_adapter.no_mcp_url_configured")
            return []
            
        from mcp.client.streamable_http import streamablehttp_client
        from mcp.client.session import ClientSession
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            logger.info("github_adapter.discover_capabilities_started", url=self.mcp_url)
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
                    logger.info("github_adapter.discover_capabilities_success", count=len(capabilities))
                    return capabilities
        except Exception as e:
            import traceback
            logger.error("github_adapter.discover_capabilities_failed", 
                         error=str(e), traceback=traceback.format_exc())
            return []

    async def execute_tool(self, tool_name: str, arguments: dict, access_token: str, provider_metadata: dict) -> Any:
        if not self.mcp_url:
            raise ValueError("GITHUB_MCP_URL is not configured for this environment.")
            
        from mcp.client.streamable_http import streamablehttp_client
        from mcp.client.session import ClientSession
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with streamablehttp_client(self.mcp_url, headers=headers) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                actual_tool_name = tool_name
                if tool_name.startswith(f"{self.provider_name}."):
                    actual_tool_name = tool_name[len(self.provider_name)+1:]
                
                logger.info("github_adapter.calling_tool", tool=actual_tool_name, args_keys=list(arguments.keys()))
                
                result = await session.call_tool(actual_tool_name, arguments)
                dump = result.model_dump()
                logger.info("github_adapter.tool_result", is_error=dump.get("isError"))

                return dump
