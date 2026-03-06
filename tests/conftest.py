import pytest
import os

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set required environment variables for tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("JIRA_URL", "https://test.atlassian.net")
    monkeypatch.setenv("JIRA_USERNAME", "test@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "test-jira-token")
    monkeypatch.setenv("GITHUB_TOKEN", "test-github-token")
    monkeypatch.setenv("GITHUB_REPO_OWNER", "test-owner")
    monkeypatch.setenv("GITHUB_REPO_NAME", "test-repo")
    monkeypatch.setenv("GITHUB_REPO_LOCAL_PATH", "/tmp/test-repo-path")
