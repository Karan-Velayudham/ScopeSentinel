from typing import Any
from connectors.base import BaseConnector
from schemas import ConnectorInfo

class DatadogConnector(BaseConnector):
    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="datadog",
            name="Datadog",
            description="Query metrics and create Datadog events and dashboards.",
            category="Observability",
            icon_url="https://cdn.iconscout.com/icon/free/png-256/datadog-282688.png"
        )

    async def list_tools(self) -> list[dict[str, Any]]:
        return [{"name": "datadog_query_metric", "description": "Query a Datadog metric"}]

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return f"Datadog tool {name} called successfully with {args}"
