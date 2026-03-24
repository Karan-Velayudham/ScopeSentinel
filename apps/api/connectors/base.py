"""
connectors/base.py — Base class for all ScopeSentinel connectors.

Each connector declares:
- auth_type: how credentials are obtained ("oauth" | "api_key" | "none")
- oauth_config / api_key_fields: connector-specific auth configuration
- list_tools(): returns typed ToolSchema list for MCP tool discovery
- call_tool(): executes a named tool with given args
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from schemas import ConnectorInfo


@dataclass
class ToolInputField:
    name: str
    type: str          # "string" | "integer" | "boolean" | "object" | "array"
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolSchema:
    name: str
    description: str
    inputs: list[ToolInputField] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputs": [
                {
                    "name": f.name,
                    "type": f.type,
                    "description": f.description,
                    "required": f.required,
                    "default": f.default,
                }
                for f in self.inputs
            ],
        }


@dataclass
class OAuthConfig:
    auth_url: str
    token_url: str
    scopes: list[str]
    client_id_env: str       # env var name holding the client_id
    client_secret_env: str   # env var name holding the client_secret
    extra_params: dict[str, str] = field(default_factory=dict)


@dataclass
class ApiKeyConfig:
    fields: list[dict]  # [{"name":"api_key","label":"API Key","secret":True}, ...]


class BaseConnector(ABC):
    # Subclasses declare these at class level
    auth_type: Literal["oauth", "api_key", "none"] = "none"
    oauth_config: Optional[OAuthConfig] = None
    api_key_config: Optional[ApiKeyConfig] = None

    @classmethod
    @abstractmethod
    def info(cls) -> ConnectorInfo:
        pass

    @classmethod
    def get_tools(cls) -> list[ToolSchema]:
        """Return the static list of tools this connector exposes."""
        return []

    @abstractmethod
    async def list_tools(self) -> list[dict[str, Any]]:
        """Return tools as dicts (for backwards compat with runtime MCP pool)."""
        pass

    @abstractmethod
    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        pass
