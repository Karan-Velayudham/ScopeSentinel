import os
import json
import httpx
from typing import Dict, Any, List
from adapters.base import BaseOAuthAdapter, Capability
import structlog

logger = structlog.get_logger(__name__)

class ConfluenceAdapter(BaseOAuthAdapter):
    provider_name = "confluence"

    def __init__(self):
        self.client_id = os.environ.get("CONFLUENCE_CLIENT_ID")
        self.client_secret = os.environ.get("CONFLUENCE_CLIENT_SECRET")

    def info(self) -> Dict[str, Any]:
        return {
            "id": "confluence",
            "name": "Confluence",
            "description": "Create, update, and search Confluence documentation.",
            "category": "Wiki",
            "icon_url": "https://wac-cdn.atlassian.com/assets/img/favicons/confluence/favicon.png",
            "auth_type": "oauth"
        }

    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        scopes = "read:confluence-content.all read:confluence-space.summary write:confluence-content offline_access"
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
                "refresh_token": data.get("refresh_token", ""),
                "expires_in": data.get("expires_in", 3600),
                "scopes": data.get("scope", "").split(" "),
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
                "refresh_token": data.get("refresh_token", ""),
                "expires_in": data.get("expires_in", 3600),
                "scopes": data.get("scope", "").split(" ")
            }

    async def _get_cloud_id(self, access_token: str) -> str:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://api.atlassian.com/oauth/token/accessible-resources",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            res.raise_for_status()
            resources = res.json()
            
            # Filter for Confluence sites
            confluence_resources = [r for r in resources if "id" in r and r.get("url", "").startswith("https://")]
            if not confluence_resources:
                raise ValueError("No accessible Confluence resources found for this account")
            
            return confluence_resources[0]["id"]

    async def discover_capabilities(self, access_token: str) -> List[Capability]:
        from mcp.client.streamable_http import streamablehttp_client
        from mcp.client.session import ClientSession
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        mcp_url = "https://mcp.atlassian.com/v1/mcp"
        
        try:
            logger.info("confluence_adapter.discover_capabilities_started", url=mcp_url)
            async with streamablehttp_client(mcp_url, headers=headers) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    
                    capabilities = []
                    for t in tools_result.tools:
                        # Optional: filter out non-confluence tools if Atlassian MCP returns all of them
                        # But typically Atlassian tools are prefixed or specific, we will expose everything the MCP offers
                        schema = t.inputSchema or {}
                        if "properties" in schema and "cloudId" in schema["properties"]:
                            del schema["properties"]["cloudId"]
                        if "required" in schema and "cloudId" in schema["required"]:
                            schema["required"].remove("cloudId")
                        capabilities.append(
                            Capability(
                                name=t.name,
                                description=t.description or "",
                                input_schema=schema,
                                scopes_required=[]
                            )
                        )
                    logger.info("confluence_adapter.discover_capabilities_success", count=len(capabilities))
                    return capabilities
        except Exception as e:
            import traceback
            logger.error("confluence_adapter.discover_capabilities_failed", 
                         error=str(e), 
                         traceback=traceback.format_exc())
            return []

    async def execute_tool(self, tool_name: str, arguments: dict, access_token: str, provider_metadata: dict) -> Any:
        from mcp.client.streamable_http import streamablehttp_client
        from mcp.client.session import ClientSession
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        mcp_url = "https://mcp.atlassian.com/v1/mcp"
        
        cloud_id = provider_metadata.get("cloud_id")
        if cloud_id and "cloudId" not in arguments:
            arguments = {"cloudId": cloud_id, **arguments}

        async with streamablehttp_client(mcp_url, headers=headers) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                actual_tool_name = tool_name
                if tool_name.startswith(f"{self.provider_name}."):
                    actual_tool_name = tool_name[len(self.provider_name)+1:]
                
                logger.info("confluence_adapter.calling_tool", tool=actual_tool_name, 
                            args_keys=list(arguments.keys()), cloud_id=cloud_id)
                
                result = await session.call_tool(actual_tool_name, arguments)
                dump = result.model_dump()
                logger.info("confluence_adapter.tool_result", is_error=dump.get("isError"))

                return dump
