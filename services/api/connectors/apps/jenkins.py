from typing import Any
from connectors.base import BaseConnector, ToolSchema, ToolInputField, ApiKeyConfig
from schemas import ConnectorInfo

class JenkinsConnector(BaseConnector):
    auth_type = "api_key"
    api_key_config = ApiKeyConfig(fields=[
        {"name": "base_url", "label": "Jenkins Base URL", "secret": False},
        {"name": "username", "label": "Username", "secret": False},
        {"name": "api_token", "label": "API Token", "secret": True},
    ])

    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="jenkins",
            name="Jenkins",
            description="Trigger and monitor Jenkins CI/CD jobs and build pipelines.",
            category="CI/CD",
            icon_url="https://www.jenkins.io/images/logos/jenkins/jenkins.png",
            auth_type="api_key",
        )

    @classmethod
    def get_tools(cls) -> list[ToolSchema]:
        return [
            ToolSchema("trigger_build", "Trigger a Jenkins job build", [
                ToolInputField("job_name", "string", "Full job name or path"),
                ToolInputField("parameters", "object", "Build parameters as key-value pairs", required=False),
            ]),
            ToolSchema("get_build_status", "Get the status of a specific Jenkins build", [
                ToolInputField("job_name", "string", "Job name or path"),
                ToolInputField("build_number", "integer", "Build number; use -1 for last build", required=False, default=-1),
            ]),
            ToolSchema("get_build_logs", "Retrieve the console log for a Jenkins build", [
                ToolInputField("job_name", "string", "Job name or path"),
                ToolInputField("build_number", "integer", "Build number"),
            ]),
            ToolSchema("list_jobs", "List all Jenkins jobs", [
                ToolInputField("folder", "string", "Folder path to list jobs from", required=False),
            ]),
            ToolSchema("abort_build", "Abort a running Jenkins build", [
                ToolInputField("job_name", "string", "Job name or path"),
                ToolInputField("build_number", "integer", "Build number to abort"),
            ]),
        ]

    async def list_tools(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self.get_tools()]

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return f"Jenkins tool '{name}' called with {args}"
