"""Linear connector stub."""
from connectors.base import BaseConnector
from schemas import ConnectorInfo


class LinearConnector(BaseConnector):
    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="linear",
            name="Linear",
            description="Connect to Linear to create and update issues and projects.",
            icon_url="📐",
            category="Issue Tracking",
        )

    async def list_tools(self) -> list[dict]:
        return [
            {"name": "create_issue", "description": "Creates a new issue in a Linear team."},
            {"name": "update_issue", "description": "Updates the status or priority of an issue."},
            {"name": "list_issues", "description": "Lists issues in a Linear project by filter."},
        ]

    async def call_tool(self, tool_name: str, params: dict) -> str:
        return f"[Linear mock] {tool_name} called with params: {params}"
