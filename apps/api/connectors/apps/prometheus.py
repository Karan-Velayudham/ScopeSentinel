from typing import Any
from connectors.base import BaseConnector, ToolSchema, ToolInputField, ApiKeyConfig
from schemas import ConnectorInfo

class PrometheusConnector(BaseConnector):
    auth_type = "api_key"
    api_key_config = ApiKeyConfig(fields=[
        {"name": "base_url", "label": "Prometheus Base URL", "secret": False},
        {"name": "bearer_token", "label": "Bearer Token (if auth enabled)", "secret": True, "required": False},
    ])

    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="prometheus",
            name="Prometheus",
            description="Query metrics and alerts from a Prometheus monitoring instance.",
            category="Monitoring",
            icon_url="https://prometheus.io/assets/favicons/favicon.ico",
            auth_type="api_key",
        )

    @classmethod
    def get_tools(cls) -> list[ToolSchema]:
        return [
            ToolSchema("query_instant", "Execute an instant PromQL query", [
                ToolInputField("query", "string", "PromQL query expression"),
                ToolInputField("time", "string", "Evaluation timestamp (RFC3339 or Unix)", required=False),
            ]),
            ToolSchema("query_range", "Execute a range PromQL query", [
                ToolInputField("query", "string", "PromQL query expression"),
                ToolInputField("start", "string", "Start time (RFC3339 or Unix timestamp)"),
                ToolInputField("end", "string", "End time (RFC3339 or Unix timestamp)"),
                ToolInputField("step", "string", "Query resolution step, e.g. 15s | 1m"),
            ]),
            ToolSchema("list_alerts", "List currently firing Prometheus alerts", [
                ToolInputField("filter", "string", "Filter by alert name pattern", required=False),
            ]),
            ToolSchema("get_targets", "List all scrape targets and their health status", []),
        ]

    async def list_tools(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self.get_tools()]

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return f"Prometheus tool '{name}' called with {args}"
