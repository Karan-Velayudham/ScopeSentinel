import os
import json
import httpx
from typing import Dict, Any, List
from adapters.base import BaseOAuthAdapter, Capability

class JiraAdapter(BaseOAuthAdapter):
    provider_name = "jira"

    def __init__(self):
        self.client_id = os.environ.get("JIRA_CLIENT_ID")
        self.client_secret = os.environ.get("JIRA_CLIENT_SECRET")

    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        scopes = "read:jira-work write:jira-work read:jira-user offline_access"
        return (
            f"https://auth.atlassian.com/authorize"
            f"?audience=api.atlassian.com"
            f"&client_id={self.client_id}"
            f"&scope={scopes}"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
            f"&response_type=code"
            f"&prompt=consent"
        )

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://auth.atlassian.com/oauth/token",
                json={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri
                }
            )
            res.raise_for_status()
            data = res.json()
            
            # Fetch cloud_id
            cloud_id = await self._get_cloud_id(data["access_token"])
            
            return {
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "expires_in": data["expires_in"],
                "scopes": data["scope"].split(" "),
                "provider_metadata": json.dumps({"cloud_id": cloud_id})
            }

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://auth.atlassian.com/oauth/token",
                json={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token
                }
            )
            res.raise_for_status()
            data = res.json()
            return {
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "expires_in": data["expires_in"],
                "scopes": data["scope"].split(" ")
            }

    async def _get_cloud_id(self, access_token: str) -> str:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://api.atlassian.com/oauth/token/accessible-resources",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            res.raise_for_status()
            resources = res.json()
            
            # Filter for Jira sites
            jira_resources = [r for r in resources if "id" in r and r.get("url", "").startswith("https://")]
            if not jira_resources:
                raise ValueError("No accessible Jira resources found for this account")
            
            # For now, pick the first Jira site
            return jira_resources[0]["id"]

    async def discover_capabilities(self, access_token: str) -> List[Capability]:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://api.atlassian.com/oauth/token/accessible-resources",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            res.raise_for_status()
            resources = res.json()
            
            if not resources:
                return []
            
            # Assume first resource's scopes represent the token's permissions
            granted_scopes = resources[0].get("scopes", [])
            
            all_capabilities = [
                Capability(
                    name="get_issue",
                    description="Fetch a Jira issue by key (e.g., PROJ-123).",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "issue_key": {"type": "string", "description": "The Jira issue key."}
                        },
                        "required": ["issue_key"]
                    },
                    scopes_required=["read:jira-work"]
                ),
                Capability(
                    name="create_issue",
                    description="Creates a new issue in a Jira project.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "project_key": {"type": "string", "description": "Project key (e.g., 'PROJ')."},
                            "summary": {"type": "string", "description": "Short summary of the issue."},
                            "description": {"type": "string", "description": "Detailed description of the issue."},
                            "issue_type": {"type": "string", "description": "Type: Bug, Story, Task.", "default": "Task"}
                        },
                        "required": ["project_key", "summary"]
                    },
                    scopes_required=["write:jira-work"]
                ),
                Capability(
                    name="search_issues",
                    description="Search for Jira issues using JQL.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "jql": {"type": "string", "description": "JQL query string."}
                        },
                        "required": ["jql"]
                    },
                    scopes_required=["read:jira-work"]
                ),
                Capability(
                    name="add_comment",
                    description="Adds a comment to an existing Jira issue.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "issue_key": {"type": "string", "description": "The Jira issue key."},
                            "body": {"type": "string", "description": "The comment text."}
                        },
                        "required": ["issue_key", "body"]
                    },
                    scopes_required=["write:jira-work"]
                ),
                Capability(
                    name="update_issue",
                    description="Updates an existing Jira issue.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "issue_key": {"type": "string", "description": "The Jira issue key."},
                            "summary": {"type": "string", "description": "New summary (optional)."},
                            "description": {"type": "string", "description": "New description (optional)."}
                        },
                        "required": ["issue_key"]
                    },
                    scopes_required=["write:jira-work"]
                )
            ]
            
            # Filter capabilities based on granted scopes
            return [
                cap for cap in all_capabilities 
                if all(scope in granted_scopes for scope in cap.scopes_required)
            ]

    async def execute_tool(self, tool_name: str, arguments: dict, access_token: str, provider_metadata: dict) -> Any:
        cloud_id = provider_metadata.get("cloud_id")
        if not cloud_id:
            raise ValueError("Missing cloud_id in provider metadata")

        base_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3"
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            if tool_name == "get_issue":
                issue_key = arguments["issue_key"]
                res = await client.get(f"{base_url}/issue/{issue_key}", headers=headers)
                res.raise_for_status()
                return res.json()

            elif tool_name == "create_issue":
                payload = {
                    "fields": {
                        "project": {"key": arguments["project_key"]},
                        "summary": arguments["summary"],
                        "description": {
                            "type": "doc",
                            "version": 1,
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": arguments.get("description", "")}
                                    ]
                                }
                            ]
                        },
                        "issuetype": {"name": arguments.get("issue_type", "Task")}
                    }
                }
                res = await client.post(f"{base_url}/issue", headers=headers, json=payload)
                res.raise_for_status()
                return res.json()

            elif tool_name == "search_issues":
                res = await client.post(
                    f"{base_url}/search",
                    headers=headers,
                    json={"jql": arguments["jql"]}
                )
                res.raise_for_status()
                return res.json()

            elif tool_name == "add_comment":
                issue_key = arguments["issue_key"]
                payload = {
                    "body": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {"type": "text", "text": arguments["body"]}
                                ]
                            }
                        ]
                    }
                }
                res = await client.post(f"{base_url}/issue/{issue_key}/comment", headers=headers, json=payload)
                res.raise_for_status()
                return res.json()

            elif tool_name == "update_issue":
                issue_key = arguments["issue_key"]
                fields = {}
                if "summary" in arguments:
                    fields["summary"] = arguments["summary"]
                if "description" in arguments:
                    fields["description"] = {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {"type": "text", "text": arguments["description"]}
                                ]
                            }
                        ]
                    }
                
                res = await client.put(f"{base_url}/issue/{issue_key}", headers=headers, json={"fields": fields})
                res.raise_for_status()
                return {"status": "success", "issue_key": issue_key}

            else:
                raise ValueError(f"Unknown tool: {tool_name}")
