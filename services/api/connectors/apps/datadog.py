from typing import Any
from connectors.base import BaseConnector, ToolSchema, ToolInputField, ApiKeyConfig
from schemas import ConnectorInfo

class DatadogConnector(BaseConnector):
    auth_type = "api_key"
    api_key_config = ApiKeyConfig(fields=[
        {"name": "api_key", "label": "API Key", "secret": True},
        {"name": "app_key", "label": "Application Key", "secret": True},
        {"name": "site", "label": "Datadog Site", "secret": False, "default": "datadoghq.com"},
    ])

    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="datadog",
            name="Datadog",
            description="Query metrics, monitors, and events from Datadog.",
            category="Monitoring",
            icon_url="https://imgix.datadoghq.com/img/dd_logo_n_70x75.png",
            auth_type="api_key",
        )

    @classmethod
    def get_tools(cls) -> list[ToolSchema]:
        return [
            ToolSchema("get_metrics", "Query a metric time series from Datadog", [
                ToolInputField("metric", "string", "Metric name, e.g. system.cpu.user"),
                ToolInputField("from_ts", "integer", "Start Unix timestamp"),
                ToolInputField("to_ts", "integer", "End Unix timestamp"),
                ToolInputField("scope", "string", "Tag scope filter, e.g. host:web-01", required=False),
            ]),
            ToolSchema("list_monitors", "List Datadog monitors with optional filter", [
                ToolInputField("name", "string", "Filter by monitor name", required=False),
                ToolInputField("tags", "string", "Comma-separated tag filter", required=False),
            ]),
            ToolSchema("get_monitor", "Fetch a Datadog monitor by ID", [
                ToolInputField("monitor_id", "integer", "Monitor ID"),
            ]),
            ToolSchema("mute_monitor", "Mute a Datadog monitor for a duration", [
                ToolInputField("monitor_id", "integer", "Monitor ID"),
                ToolInputField("end_ts", "integer", "Unix timestamp when mute expires", required=False),
            ]),
            ToolSchema("get_events", "Query Datadog events log", [
                ToolInputField("start_ts", "integer", "Start Unix timestamp"),
                ToolInputField("end_ts", "integer", "End Unix timestamp"),
                ToolInputField("tags", "string", "Filter by tags", required=False),
            ]),
            ToolSchema("create_event", "Post a custom event to the Datadog event stream", [
                ToolInputField("title", "string", "Event title"),
                ToolInputField("text", "string", "Event description"),
                ToolInputField("tags", "array", "Tags to attach", required=False),
                ToolInputField("alert_type", "string", "info | error | warning | success", required=False, default="info"),
            ]),
        ]

    async def list_tools(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self.get_tools()]

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return f"Datadog tool '{name}' called with {args}"
