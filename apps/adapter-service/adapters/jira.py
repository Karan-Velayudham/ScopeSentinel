import os
import json
import httpx
from typing import Dict, Any, List
from adapters.base import BaseOAuthAdapter, Capability

class JiraAdapter(BaseOAuthAdapter):
    provider_name = "jira"

    def __init__(self):
        self.client_id = os.environ.get("JIRA_CLIENT_ID")
        self.client_secret = os.environ.get("JIRA_CLIENT_SECRET")

    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        scopes = "read:jira-work write:jira-work read:jira-user offline_access"
        import urllib.parse
        scopes_encoded = urllib.parse.quote(scopes)
        redirect_encoded = urllib.parse.quote(redirect_uri)
        client_id_encoded = urllib.parse.quote(self.client_id or "")
        
        return (
            f"https://auth.atlassian.com/authorize"
            f"?audience=api.atlassian.com"
            f"&client_id={client_id_encoded}"
            f"&scope={scopes_encoded}"
            f"&redirect_uri={redirect_encoded}"
            f"&state={urllib.parse.quote(state)}"
            f"&response_type=code"
            f"&prompt=consent"
        )

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://auth.atlassian.com/oauth/token",
                json={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri
                }
            )
            res.raise_for_status()
            data = res.json()
            
            # Fetch cloud_id
            cloud_id = await self._get_cloud_id(data["access_token"])
            
            return {
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "expires_in": data["expires_in"],
                "scopes": data["scope"].split(" "),
                "provider_metadata": json.dumps({"cloud_id": cloud_id})
            }

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://auth.atlassian.com/oauth/token",
                json={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token
                }
            )
            res.raise_for_status()
            data = res.json()
            return {
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "expires_in": data["expires_in"],
                "scopes": data["scope"].split(" ")
            }

    async def _get_cloud_id(self, access_token: str) -> str:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://api.atlassian.com/oauth/token/accessible-resources",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            res.raise_for_status()
            resources = res.json()
            
            # Filter for Jira sites
            jira_resources = [r for r in resources if "id" in r and r.get("url", "").startswith("https://")]
            if not jira_resources:
                raise ValueError("No accessible Jira resources found for this account")
            
            # For now, pick the first Jira site
            return jira_resources[0]["id"]

    async def discover_capabilities(self, access_token: str) -> List[Capability]:
        from mcp.client.sse import sse_client
        from mcp.client.session import ClientSession
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        try:
            async with sse_client("https://mcp.atlassian.com/v1/mcp", headers=headers) as (read_stream, write_stream):
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
                    return capabilities
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.error("jira_adapter.discover_capabilities_failed", error=str(e))
            return []

    async def execute_tool(self, tool_name: str, arguments: dict, access_token: str, provider_metadata: dict) -> Any:
        from mcp.client.sse import sse_client
        from mcp.client.session import ClientSession
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        async with sse_client("https://mcp.atlassian.com/v1/mcp", headers=headers) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                
                # Convert the CallToolResult into a serializable dictionary
                return result.model_dump()

