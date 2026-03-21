from typing import Any
from connectors.base import BaseConnector
from schemas import ConnectorInfo


class GitLabConnector(BaseConnector):
    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="gitlab",
            name="GitLab",
            description="Connect to GitLab to trigger pipelines and manage merge requests.",
            icon_url="🦊",
            category="VCS",
        )

    async def list_tools(self) -> list[dict]:
        return [
            {"name": "create_merge_request", "description": "Opens a merge request on a GitLab project."},
            {"name": "trigger_pipeline", "description": "Triggers a CI/CD pipeline on a branch."},
            {"name": "get_pipeline_status", "description": "Gets the current status of a pipeline."},
        ]

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return f"GitLab tool {name} called successfully with {args}"
