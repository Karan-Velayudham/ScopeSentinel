from typing import Any
"""Prometheus connector stub."""
from connectors.base import BaseConnector
from schemas import ConnectorInfo


class PrometheusConnector(BaseConnector):
    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="prometheus",
            name="Prometheus",
            description="Connect to Prometheus to query metrics and evaluate alert rules.",
            icon_url="📊",
            category="Observability",
        )

    async def list_tools(self) -> list[dict]:
        return [
            {"name": "query_metric", "description": "Executes a PromQL query against the Prometheus endpoint."},
            {"name": "list_alerts", "description": "Returns all currently firing alert rules."},
        ]

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return f"Prometheus tool {name} called successfully with {args}"
