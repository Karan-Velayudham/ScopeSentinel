from typing import Any
from connectors.base import BaseConnector, ToolSchema, ToolInputField, OAuthConfig
from schemas import ConnectorInfo

class GithubConnector(BaseConnector):
    auth_type = "oauth"
    oauth_config = OAuthConfig(
        auth_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        scopes=["repo", "read:org", "read:user"],
        client_id_env="GITHUB_CLIENT_ID",
        client_secret_env="GITHUB_CLIENT_SECRET",
    )

    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="github",
            name="GitHub",
            description="Manage repositories, pull requests, issues, and GitHub Actions.",
            category="VCS",
            icon_url="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png",
            auth_type="oauth",
        )

    @classmethod
    def get_tools(cls) -> list[ToolSchema]:
        return [
            ToolSchema("get_pull_request", "Fetch details and diff of a pull request", [
                ToolInputField("repo", "string", "Repository in owner/repo format"),
                ToolInputField("pr_number", "integer", "Pull request number"),
            ]),
            ToolSchema("create_pull_request", "Open a new pull request", [
                ToolInputField("repo", "string", "Repository in owner/repo format"),
                ToolInputField("title", "string", "PR title"),
                ToolInputField("body", "string", "PR description body"),
                ToolInputField("head", "string", "Source branch name"),
                ToolInputField("base", "string", "Target branch name", required=False, default="main"),
            ]),
            ToolSchema("post_review_comment", "Post a review comment on a pull request", [
                ToolInputField("repo", "string", "Repository in owner/repo format"),
                ToolInputField("pr_number", "integer", "Pull request number"),
                ToolInputField("body", "string", "Comment markdown body"),
            ]),
            ToolSchema("create_issue", "Create a new GitHub issue", [
                ToolInputField("repo", "string", "Repository in owner/repo format"),
                ToolInputField("title", "string", "Issue title"),
                ToolInputField("body", "string", "Issue body"),
                ToolInputField("labels", "array", "Labels to apply", required=False),
            ]),
            ToolSchema("list_issues", "List issues in a repository", [
                ToolInputField("repo", "string", "Repository in owner/repo format"),
                ToolInputField("state", "string", "Filter by state: open | closed | all", required=False, default="open"),
            ]),
            ToolSchema("get_file_contents", "Read file contents from a repository", [
                ToolInputField("repo", "string", "Repository in owner/repo format"),
                ToolInputField("path", "string", "File path within the repository"),
                ToolInputField("ref", "string", "Branch, tag, or commit SHA", required=False, default="main"),
            ]),
            ToolSchema("trigger_workflow", "Trigger a GitHub Actions workflow dispatch", [
                ToolInputField("repo", "string", "Repository in owner/repo format"),
                ToolInputField("workflow_id", "string", "Workflow filename or ID"),
                ToolInputField("ref", "string", "Branch to run the workflow on"),
                ToolInputField("inputs", "object", "Workflow input parameters", required=False),
            ]),
        ]

    async def list_tools(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self.get_tools()]

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return f"GitHub tool '{name}' called with {args}"
