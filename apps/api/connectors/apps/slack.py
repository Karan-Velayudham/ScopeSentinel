from typing import Any
from connectors.base import BaseConnector, ToolSchema, ToolInputField, OAuthConfig
from schemas import ConnectorInfo

class SlackConnector(BaseConnector):
    auth_type = "oauth"
    oauth_config = OAuthConfig(
        auth_url="https://slack.com/oauth/v2/authorize",
        token_url="https://slack.com/api/oauth.v2.access",
        scopes=["chat:write", "channels:read", "files:write", "users:read"],
        client_id_env="SLACK_CLIENT_ID",
        client_secret_env="SLACK_CLIENT_SECRET",
    )

    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            id="slack",
            name="Slack",
            description="Send messages, create channels, and manage Slack workspaces.",
            category="Messaging",
            icon_url="https://a.slack-edge.com/80588/marketing/img/meta/slack_hash_256.png",
            auth_type="oauth",
        )

    @classmethod
    def get_tools(cls) -> list[ToolSchema]:
        return [
            ToolSchema("post_message", "Send a message to a Slack channel", [
                ToolInputField("channel", "string", "Channel name or ID, e.g. #alerts"),
                ToolInputField("text", "string", "Message text (supports Slack markdown)"),
                ToolInputField("thread_ts", "string", "Thread timestamp to reply in thread", required=False),
            ]),
            ToolSchema("post_thread_reply", "Reply in an existing message thread", [
                ToolInputField("channel", "string", "Channel ID"),
                ToolInputField("thread_ts", "string", "Parent message timestamp"),
                ToolInputField("text", "string", "Reply text"),
            ]),
            ToolSchema("list_channels", "List all public channels in the workspace", [
                ToolInputField("limit", "integer", "Maximum number of channels", required=False, default=100),
            ]),
            ToolSchema("create_channel", "Create a new Slack channel", [
                ToolInputField("name", "string", "Channel name (lowercase, no spaces)"),
                ToolInputField("is_private", "boolean", "Create as private channel", required=False, default=False),
            ]),
            ToolSchema("upload_file", "Upload a file or snippet to a channel", [
                ToolInputField("channel", "string", "Channel ID"),
                ToolInputField("content", "string", "File content as string"),
                ToolInputField("filename", "string", "Filename to display"),
                ToolInputField("title", "string", "File title", required=False),
            ]),
        ]

    async def list_tools(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self.get_tools()]

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return f"Slack tool '{name}' called with {args}"
