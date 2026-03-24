import pytest
import httpx
from unittest.mock import AsyncMock, patch
from adapters.jira import JiraAdapter
from adapters.base import Capability

@pytest.mark.asyncio
async def test_discover_capabilities_success():
    adapter = JiraAdapter()
    access_token = "fake_token"
    
    mock_resources = [
        {
            "id": "cloud-id-123",
            "url": "https://site.atlassian.net",
            "scopes": ["read:jira-work"]
        }
    ]
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = httpx.Response(
            200, 
            json=mock_resources,
            request=httpx.Request("GET", "https://api.atlassian.com/oauth/token/accessible-resources")
        )
        
        capabilities = await adapter.discover_capabilities(access_token)
        
        # Should only have get_issue and search_issues (read:jira-work)
        cap_names = [c.name for c in capabilities]
        assert "get_issue" in cap_names
        assert "search_issues" in cap_names
        assert "create_issue" not in cap_names
        assert "add_comment" not in cap_names
        assert "update_issue" not in cap_names
        assert len(capabilities) == 2

@pytest.mark.asyncio
async def test_discover_capabilities_full_scopes():
    adapter = JiraAdapter()
    access_token = "fake_token"
    
    mock_resources = [
        {
            "id": "cloud-id-123",
            "url": "https://site.atlassian.net",
            "scopes": ["read:jira-work", "write:jira-work"]
        }
    ]
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = httpx.Response(
            200, 
            json=mock_resources,
            request=httpx.Request("GET", "https://api.atlassian.com/oauth/token/accessible-resources")
        )
        
        capabilities = await adapter.discover_capabilities(access_token)
        
        assert len(capabilities) == 5
        cap_names = [c.name for c in capabilities]
        assert "get_issue" in cap_names
        assert "create_issue" in cap_names
        assert "search_issues" in cap_names
        assert "add_comment" in cap_names
        assert "update_issue" in cap_names

@pytest.mark.asyncio
async def test_get_cloud_id_success():
    adapter = JiraAdapter()
    
    mock_resources = [
        {"id": "cloud-id-123", "url": "https://site.atlassian.net"}
    ]
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = httpx.Response(
            200, 
            json=mock_resources,
            request=httpx.Request("GET", "https://api.atlassian.com/oauth/token/accessible-resources")
        )
        
        cloud_id = await adapter._get_cloud_id("fake_token")
        assert cloud_id == "cloud-id-123"

@pytest.mark.asyncio
async def test_get_cloud_id_no_jira():
    adapter = JiraAdapter()
    
    mock_resources = [
        {"id": "other-id", "url": "not-a-jira-url"}
    ]
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = httpx.Response(
            200, 
            json=mock_resources,
            request=httpx.Request("GET", "https://api.atlassian.com/oauth/token/accessible-resources")
        )
        
        with pytest.raises(ValueError, match="No accessible Jira resources found"):
            await adapter._get_cloud_id("fake_token")
