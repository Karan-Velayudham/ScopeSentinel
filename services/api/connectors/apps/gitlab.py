"""GitLab connector stub."""
from connectors.base import BaseConnector


class GitLabConnector(BaseConnector):
    @classmethod
    def info(cls) -> dict:
        return {
            "id": "gitlab",
            "name": "GitLab",
            "description": "Connect to GitLab to trigger pipelines and manage merge requests.",
            "icon": "🦊",
            "category": "VCS",
        }

    async def list_tools(self) -> list[dict]:
        return [
            {"name": "create_merge_request", "description": "Opens a merge request on a GitLab project."},
            {"name": "trigger_pipeline", "description": "Triggers a CI/CD pipeline on a branch."},
            {"name": "get_pipeline_status", "description": "Gets the current status of a pipeline."},
        ]

    async def call_tool(self, tool_name: str, params: dict) -> str:
        return f"[GitLab mock] {tool_name} called with params: {params}"
