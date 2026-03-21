"""PagerDuty connector stub."""
from connectors.base import BaseConnector


class PagerDutyConnector(BaseConnector):
    @classmethod
    def info(cls) -> dict:
        return {
            "id": "pagerduty",
            "name": "PagerDuty",
            "description": "Connect to PagerDuty to receive incident alerts and manage on-call rotations.",
            "icon": "🚨",
            "category": "Observability",
        }

    async def list_tools(self) -> list[dict]:
        return [
            {"name": "create_incident", "description": "Creates a PagerDuty incident."},
            {"name": "resolve_incident", "description": "Resolves an open PagerDuty incident."},
            {"name": "get_on_call", "description": "Returns the current on-call user for a schedule."},
        ]

    async def call_tool(self, tool_name: str, params: dict) -> str:
        return f"[PagerDuty mock] {tool_name} called with params: {params}"
