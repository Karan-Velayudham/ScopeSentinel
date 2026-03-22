from typing import Any
from connectors.base import BaseConnector, ToolSchema, ToolInputField, OAuthConfig
from schemas import ConnectorInfo

class JiraConnector(BaseConnector):
    auth_type = "oauth"
    oauth_config = OAuthConfig(
        auth_url="https://auth.atlassian.com/authorize",
        token_url="https://auth.atlassian.com/oauth/token",
        scopes=["read:jira-work", "write:jira-work", "read:jira-user"],
        client_id_env="JIRA_CLIENT_ID",
        client_secret_env="JIRA_CLIENT_SECRET",
        extra_params={"audience": "api.atlassian.com", "prompt": "consent"},
    )

    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="jira",
            name="Jira",
            description="Create, update, and query Jira issues and projects.",
            category="Issue Tracker",
            icon_url="https://wac-cdn.atlassian.com/assets/img/favicons/atlassian/favicon.png",
            auth_type="oauth",
        )

    @classmethod
    def get_tools(cls) -> list[ToolSchema]:
        return [
            ToolSchema("get_issue", "Fetch a Jira issue by key", [
                ToolInputField("issue_key", "string", "Jira issue key, e.g. PROJ-123"),
            ]),
            ToolSchema("create_issue", "Create a new Jira issue", [
                ToolInputField("project_key", "string", "Jira project key"),
                ToolInputField("summary", "string", "Issue summary/title"),
                ToolInputField("description", "string", "Issue description body"),
                ToolInputField("issue_type", "string", "Issue type: Bug | Story | Task | Epic", required=False, default="Task"),
                ToolInputField("priority", "string", "Priority: Highest|High|Medium|Low|Lowest", required=False),
                ToolInputField("assignee", "string", "Assignee account ID", required=False),
            ]),
            ToolSchema("update_issue", "Update fields on an existing Jira issue", [
                ToolInputField("issue_key", "string", "Jira issue key"),
                ToolInputField("fields", "object", "Key-value fields to update"),
            ]),
            ToolSchema("transition_issue", "Transition a Jira issue to a new status", [
                ToolInputField("issue_key", "string", "Jira issue key"),
                ToolInputField("transition_name", "string", "Target status name, e.g. In Progress"),
            ]),
            ToolSchema("add_comment", "Add a comment to a Jira issue", [
                ToolInputField("issue_key", "string", "Jira issue key"),
                ToolInputField("body", "string", "Comment text (Jira markdown)"),
            ]),
            ToolSchema("search_issues", "Search Jira issues using JQL", [
                ToolInputField("jql", "string", "JQL query string"),
                ToolInputField("max_results", "integer", "Maximum results to return", required=False, default=20),
            ]),
        ]

    async def list_tools(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self.get_tools()]

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return f"Jira tool '{name}' called with {args}"
