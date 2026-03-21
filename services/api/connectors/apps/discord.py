"""Discord connector stub."""
from connectors.base import BaseConnector
from schemas import ConnectorInfo


class DiscordConnector(BaseConnector):
    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="discord",
            name="Discord",
            description="Connect to Discord to send messages and notifications to channels.",
            icon_url="💬",
            category="Chat",
        )

    async def list_tools(self) -> list[dict]:
        return [
            {"name": "send_message", "description": "Sends a message to a Discord channel."},
            {"name": "create_thread", "description": "Creates a new thread in a channel."},
        ]

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return f"Discord tool {name} called successfully with {args}"
