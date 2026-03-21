from typing import Any
from connectors.base import BaseConnector
from schemas import ConnectorInfo

class SlackConnector(BaseConnector):
    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="slack",
            name="Slack",
            description="Send messages, notifications, and interactive blocks to Slack channels.",
            category="Chat",
            icon_url="https://upload.wikimedia.org/wikipedia/commons/d/d5/Slack_icon_2019.svg"
        )

    async def list_tools(self) -> list[dict[str, Any]]:
        return [{"name": "slack_send_message", "description": "Sends a message to a channel"}]

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return f"Slack tool {name} called successfully with {args}"
