from abc import ABC, abstractmethod
from typing import Any

from schemas import ConnectorInfo

class BaseConnector(ABC):
    @classmethod
    @abstractmethod
    def info(cls) -> ConnectorInfo:
        pass

    @abstractmethod
    async def list_tools(self) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        pass
