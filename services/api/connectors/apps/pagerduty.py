from typing import Any
from connectors.base import BaseConnector, ToolSchema, ToolInputField, ApiKeyConfig
from schemas import ConnectorInfo

class PagerDutyConnector(BaseConnector):
    auth_type = "api_key"
    api_key_config = ApiKeyConfig(fields=[
        {"name": "api_key", "label": "API Key (REST API Key)", "secret": True},
        {"name": "routing_key", "label": "Events Routing Key (v2)", "secret": True},
    ])

    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="pagerduty",
            name="PagerDuty",
            description="Trigger, resolve, and manage PagerDuty incidents and on-call schedules.",
            category="Alerting",
            icon_url="https://www.pagerduty.com/favicon.ico",
            auth_type="api_key",
        )

    @classmethod
    def get_tools(cls) -> list[ToolSchema]:
        return [
            ToolSchema("trigger_incident", "Trigger a new PagerDuty incident", [
                ToolInputField("summary", "string", "Incident summary"),
                ToolInputField("severity", "string", "Severity: critical | error | warning | info", required=False, default="error"),
                ToolInputField("source", "string", "Source system name"),
                ToolInputField("dedup_key", "string", "Deduplication key (idempotency)", required=False),
            ]),
            ToolSchema("resolve_incident", "Resolve an existing PagerDuty incident", [
                ToolInputField("dedup_key", "string", "Deduplication key of the incident to resolve"),
            ]),
            ToolSchema("list_incidents", "List PagerDuty incidents", [
                ToolInputField("statuses", "array", "Filter by status: triggered | acknowledged | resolved", required=False),
                ToolInputField("limit", "integer", "Maximum results", required=False, default=25),
            ]),
            ToolSchema("get_oncall", "Get the current on-call users for a schedule", [
                ToolInputField("schedule_id", "string", "PagerDuty schedule ID", required=False),
            ]),
            ToolSchema("create_note", "Add a note to an incident", [
                ToolInputField("incident_id", "string", "Incident ID"),
                ToolInputField("content", "string", "Note content"),
            ]),
        ]

    async def list_tools(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self.get_tools()]

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return f"PagerDuty tool '{name}' called with {args}"
