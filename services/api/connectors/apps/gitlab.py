from typing import Any
from connectors.base import BaseConnector, ToolSchema, ToolInputField, OAuthConfig
from schemas import ConnectorInfo

class GitLabConnector(BaseConnector):
    auth_type = "oauth"
    oauth_config = OAuthConfig(
        auth_url="https://gitlab.com/oauth/authorize",
        token_url="https://gitlab.com/oauth/token",
        scopes=["api", "read_user", "read_repository"],
        client_id_env="GITLAB_CLIENT_ID",
        client_secret_env="GITLAB_CLIENT_SECRET",
    )

    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="gitlab",
            name="GitLab",
            description="Manage GitLab repositories, merge requests, and CI/CD pipelines.",
            category="VCS",
            icon_url="https://about.gitlab.com/images/press/logo/png/gitlab-logo-200.png",
            auth_type="oauth",
        )

    @classmethod
    def get_tools(cls) -> list[ToolSchema]:
        return [
            ToolSchema("get_merge_request", "Fetch a GitLab merge request with diff", [
                ToolInputField("project_id", "string", "Project ID or namespace/project"),
                ToolInputField("mr_iid", "integer", "Merge request internal ID"),
            ]),
            ToolSchema("create_merge_request", "Create a new GitLab merge request", [
                ToolInputField("project_id", "string", "Project ID or namespace/project"),
                ToolInputField("title", "string", "Merge request title"),
                ToolInputField("source_branch", "string", "Source branch"),
                ToolInputField("target_branch", "string", "Target branch", required=False, default="main"),
                ToolInputField("description", "string", "MR description", required=False),
            ]),
            ToolSchema("create_issue", "Create a new GitLab issue", [
                ToolInputField("project_id", "string", "Project ID or namespace/project"),
                ToolInputField("title", "string", "Issue title"),
                ToolInputField("description", "string", "Issue description"),
                ToolInputField("labels", "string", "Comma-separated labels", required=False),
            ]),
            ToolSchema("trigger_pipeline", "Trigger a GitLab CI/CD pipeline", [
                ToolInputField("project_id", "string", "Project ID or namespace/project"),
                ToolInputField("ref", "string", "Branch or tag to run pipeline on"),
                ToolInputField("variables", "object", "Pipeline variables", required=False),
            ]),
            ToolSchema("get_pipeline_status", "Get status of a CI/CD pipeline", [
                ToolInputField("project_id", "string", "Project ID or namespace/project"),
                ToolInputField("pipeline_id", "integer", "Pipeline ID"),
            ]),
        ]

    async def list_tools(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self.get_tools()]

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return f"GitLab tool '{name}' called with {args}"
