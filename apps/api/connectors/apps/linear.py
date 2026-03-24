from typing import Any
from connectors.base import BaseConnector, ToolSchema, ToolInputField, OAuthConfig
from schemas import ConnectorInfo

class LinearConnector(BaseConnector):
    auth_type = "oauth"
    oauth_config = OAuthConfig(
        auth_url="https://linear.app/oauth/authorize",
        token_url="https://api.linear.app/oauth/token",
        scopes=["read", "write", "issues:create"],
        client_id_env="LINEAR_CLIENT_ID",
        client_secret_env="LINEAR_CLIENT_SECRET",
    )

    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="linear",
            name="Linear",
            description="Manage Linear issues, projects, and sprints.",
            category="Issue Tracker",
            icon_url="https://linear.app/favicon.ico",
            auth_type="oauth",
        )

    @classmethod
    def get_tools(cls) -> list[ToolSchema]:
        return [
            ToolSchema("get_issue", "Fetch a Linear issue by ID or identifier", [
                ToolInputField("issue_id", "string", "Issue ID or identifier, e.g. ENG-123"),
            ]),
            ToolSchema("create_issue", "Create a new Linear issue", [
                ToolInputField("team_id", "string", "Team ID to create issue in"),
                ToolInputField("title", "string", "Issue title"),
                ToolInputField("description", "string", "Issue description (markdown)", required=False),
                ToolInputField("priority", "integer", "Priority: 0=No priority, 1=Urgent, 2=High, 3=Normal, 4=Low", required=False),
                ToolInputField("assignee_id", "string", "User ID to assign", required=False),
            ]),
            ToolSchema("update_issue", "Update a Linear issue", [
                ToolInputField("issue_id", "string", "Issue ID"),
                ToolInputField("title", "string", "New title", required=False),
                ToolInputField("description", "string", "New description", required=False),
                ToolInputField("state_id", "string", "New state ID", required=False),
            ]),
            ToolSchema("add_comment", "Add a comment to a Linear issue", [
                ToolInputField("issue_id", "string", "Issue ID"),
                ToolInputField("body", "string", "Comment body (markdown)"),
            ]),
            ToolSchema("list_teams", "List all teams in the workspace", []),
            ToolSchema("search_issues", "Search Linear issues", [
                ToolInputField("query", "string", "Search query string"),
                ToolInputField("team_id", "string", "Filter by team ID", required=False),
            ]),
        ]

    async def list_tools(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self.get_tools()]

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return f"Linear tool '{name}' called with {args}"
