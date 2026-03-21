"""Jenkins connector stub."""
from connectors.base import BaseConnector
from schemas import ConnectorInfo


class JenkinsConnector(BaseConnector):
    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="jenkins",
            name="Jenkins",
            description="Connect to Jenkins to trigger and monitor CI/CD build jobs.",
            icon_url="🤵",
            category="CI/CD",
        )

    async def list_tools(self) -> list[dict]:
        return [
            {"name": "trigger_build", "description": "Triggers a Jenkins build job."},
            {"name": "get_build_status", "description": "Gets the result of the latest build."},
            {"name": "list_jobs", "description": "Lists all available Jenkins jobs."},
        ]

    async def call_tool(self, tool_name: str, params: dict) -> str:
        return f"[Jenkins mock] {tool_name} called with params: {params}"
