from typing import Dict, Any, List
from adapters.base import BaseOAuthAdapter, Capability

class JiraAdapter(BaseOAuthAdapter):
    provider_name = "jira"

    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        # Mock URL for testing, real implementation uses Atlassian endpoints
        return f"https://auth.atlassian.com/authorize?audience=api.atlassian.com&client_id=MOCK_CLIENT_ID&scope=read%3Ajira-work%20write%3Ajira-work&redirect_uri={redirect_uri}&state={state}&response_type=code&prompt=consent"

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        return {
            "access_token": "mock_atlassian_access_token_" + code,
            "refresh_token": "mock_atlassian_refresh_token",
            "expires_in": 3600,
            "scopes": ["read:jira-work", "write:jira-work"]
        }

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        return {
            "access_token": "refreshed_mock_atlassian_access_token",
            "refresh_token": "new_mock_atlassian_refresh_token",
            "expires_in": 3600,
            "scopes": ["read:jira-work", "write:jira-work"]
        }

    async def discover_capabilities(self, access_token: str) -> List[Capability]:
        return [
            Capability(
                name="create_issue",
                description="Creates an issue in the Jira project.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "projectKey": {"type": "string"},
                        "summary": {"type": "string"},
                        "description": {"type": "string"}
                    },
                    "required": ["projectKey", "summary"]
                },
                scopes_required=["write:jira-work"]
            ),
            Capability(
                name="search_issues",
                description="Searches Jira issues using JQL.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "jql": {"type": "string"}
                    },
                    "required": ["jql"]
                },
                scopes_required=["read:jira-work"]
            )
        ]

    async def execute_tool(self, tool_name: str, arguments: dict, access_token: str) -> Any:
        import httpx
        # Mock execution logic
        if tool_name == "create_issue":
            return {"status": "success", "issue_key": f"{arguments.get('projectKey')}-123", "message": "Issue created via OAuth"}
        elif tool_name == "search_issues":
            return {"issues": [{"key": "TEST-1", "summary": "Found issue via OAuth Search"}]}
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
