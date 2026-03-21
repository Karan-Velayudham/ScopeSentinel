from typing import Any
from connectors.base import BaseConnector
from schemas import ConnectorInfo

class GithubConnector(BaseConnector):
    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="github",
            name="GitHub",
            description="Integrate with GitHub repositories, pull requests, and actions.",
            category="VCS",
            icon_url="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
        )

    async def list_tools(self) -> list[dict[str, Any]]:
        return [{"name": "github_create_pr", "description": "Creates a pull request"}]

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return f"Mocked Github tool {name} called with {args}"
