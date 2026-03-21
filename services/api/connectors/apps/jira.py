from typing import Any
from connectors.base import BaseConnector
from schemas import ConnectorInfo

class JiraConnector(BaseConnector):
    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="jira",
            name="Jira",
            description="Create, update, and track Jira issues directly from workflows.",
            category="Issue Tracking",
            icon_url="https://cdn.iconscout.com/icon/free/png-256/jira-3628286-3030011.png"
        )

    async def list_tools(self) -> list[dict[str, Any]]:
        return [{"name": "jira_create_issue", "description": "Creates a Jira issue"}]

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return f"Jira tool {name} called successfully with {args}"
