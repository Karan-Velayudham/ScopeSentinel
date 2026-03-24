from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pydantic import BaseModel

class Capability(BaseModel):
    name: str # e.g., 'create_issue'
    description: str
    input_schema: Dict[str, Any] # JSON Schema
    scopes_required: List[str] = []

class BaseOAuthAdapter(ABC):
    """
    Abstract Base Class for all OAuth integrations.
    Provides standard methods for handshake, token management, and capability discovery.
    """
    provider_name: str

    @abstractmethod
    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Returns the authorization URL to redirect the user to."""
        pass

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchanges the authorization code for tokens.
        Should return a standardized dictionary:
        {
            "access_token": str,
            "refresh_token": str,
            "expires_in": int,
            "scopes": List[str]
        }
        """
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refreshes an expired token.
        Returns the same standardized dictionary as exchange_code.
        """
        pass

    @abstractmethod
    async def discover_capabilities(self, access_token: str) -> List[Capability]:
        """
        Discovers capabilities (e.g., Jira endpoints available) given an access token.
        Must normalize them into the Capability model.
        """
        pass

    @abstractmethod
    async def execute_tool(self, tool_name: str, arguments: dict, access_token: str, provider_metadata: dict) -> Any:
        """
        Executes a normalized capability using the provider's API.
        """
        pass
