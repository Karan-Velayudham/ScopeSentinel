from typing import Dict, Any, List
from adapters.base import BaseOAuthAdapter, Capability

class SkeletonAdapter(BaseOAuthAdapter):
    def __init__(self, provider_id: str, name: str, category: str, icon_url: str):
        self.provider_id = provider_id
        self.name = name
        self.category = category
        self.icon_url = icon_url

    def info(self) -> Dict[str, Any]:
        return {
            "id": self.provider_id,
            "name": self.name,
            "description": f"Integration for {self.name}",
            "category": self.category,
            "icon_url": self.icon_url,
            "auth_type": "oauth"
        }

    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        return "#"

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        return {}

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        return {}

    async def discover_capabilities(self, access_token: str) -> List[Capability]:
        return []

    async def execute_tool(self, tool_name: str, arguments: dict, access_token: str, provider_metadata: dict) -> Any:
        return {}
