from typing import Any
from connectors.base import BaseConnector, ToolSchema, ToolInputField, OAuthConfig
from schemas import ConnectorInfo

class DiscordConnector(BaseConnector):
    auth_type = "oauth"
    oauth_config = OAuthConfig(
        auth_url="https://discord.com/api/oauth2/authorize",
        token_url="https://discord.com/api/oauth2/token",
        scopes=["bot", "applications.commands"],
        client_id_env="DISCORD_CLIENT_ID",
        client_secret_env="DISCORD_CLIENT_SECRET",
    )

    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="discord",
            name="Discord",
            description="Send messages, create threads, and manage Discord servers.",
            category="Messaging",
            icon_url="https://assets-global.website-files.com/6257adef93867e50d84d30e2/636e0a6a49cf127bf92de1e2_icon_clyde_blurple_RGB.png",
            auth_type="oauth",
        )

    @classmethod
    def get_tools(cls) -> list[ToolSchema]:
        return [
            ToolSchema("post_message", "Send a message to a Discord channel", [
                ToolInputField("channel_id", "string", "Discord channel ID"),
                ToolInputField("content", "string", "Message content (markdown supported)"),
                ToolInputField("embed_title", "string", "Optional embed title", required=False),
                ToolInputField("embed_description", "string", "Optional embed description", required=False),
            ]),
            ToolSchema("create_thread", "Create a new thread in a channel", [
                ToolInputField("channel_id", "string", "Parent channel ID"),
                ToolInputField("name", "string", "Thread name"),
                ToolInputField("message", "string", "Initial thread message"),
            ]),
            ToolSchema("list_channels", "List channels in a Discord server", [
                ToolInputField("guild_id", "string", "Discord server (guild) ID"),
            ]),
        ]

    async def list_tools(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self.get_tools()]

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return f"Discord tool '{name}' called with {args}"
