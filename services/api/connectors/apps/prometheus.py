"""Prometheus connector stub."""
from connectors.base import BaseConnector


class PrometheusConnector(BaseConnector):
    @classmethod
    def info(cls) -> dict:
        return {
            "id": "prometheus",
            "name": "Prometheus",
            "description": "Connect to Prometheus to query metrics and evaluate alert rules.",
            "icon": "📊",
            "category": "Observability",
        }

    async def list_tools(self) -> list[dict]:
        return [
            {"name": "query_metric", "description": "Executes a PromQL query against the Prometheus endpoint."},
            {"name": "list_alerts", "description": "Returns all currently firing alert rules."},
        ]

    async def call_tool(self, tool_name: str, params: dict) -> str:
        return f"[Prometheus mock] {tool_name} called with params: {params}"
