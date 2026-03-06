import pytest
from unittest.mock import MagicMock, patch
from tools.github_tool import GithubTool, PRResult, _build_pr_body
from tools.jira_tool import JiraTicket
from agents.planner_agent import PlannerOutput
from github import GithubException

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_REPO_OWNER", "owner")
    monkeypatch.setenv("GITHUB_REPO_NAME", "repo")
    monkeypatch.setenv("JIRA_URL", "https://test.atlassian.net")

@pytest.fixture
def sample_ticket():
    return JiraTicket(
        id="SCRUM-789",
        summary="Add login button",
        description="Just do it",
        status="To Do",
        issue_type="Story",
        acceptance_criteria=""
    )

@pytest.fixture
def sample_plan():
    return PlannerOutput(
        ticket_id="SCRUM-789",
        summary="Add login button",
        steps=["Step 1", "Step 2"],
        architecture_notes="Architecture is cool",
        raw_plan="raw"
    )

def test_build_pr_body(sample_ticket, sample_plan):
    body = _build_pr_body(sample_ticket, sample_plan, "https://jira.url")
    assert "[SCRUM-789](https://jira.url/browse/SCRUM-789)" in body
    assert "Architecture is cool" in body
    assert "1. Step 1" in body
    assert "2. Step 2" in body

@patch("tools.github_tool.Github")
def test_github_tool_init(mock_github_class, mock_env):
    mock_gh_instance = MagicMock()
    mock_github_class.return_value = mock_gh_instance
    
    tool = GithubTool()
    
    assert tool.token == "test-token"
    assert tool.repo_owner == "owner"
    assert tool.repo_name == "repo"
    assert tool.jira_url == "https://test.atlassian.net"
    mock_gh_instance.get_repo.assert_called_once_with("owner/repo")

@patch("tools.github_tool.Github")
def test_create_pr_success(mock_github_class, mock_env, sample_ticket, sample_plan):
    mock_gh_instance = MagicMock()
    mock_github_class.return_value = mock_gh_instance
    
    mock_repo = MagicMock()
    mock_gh_instance.get_repo.return_value = mock_repo
    
    mock_pr = MagicMock()
    mock_pr.number = 42
    mock_pr.html_url = "https://github.com/owner/repo/pull/42"
    mock_repo.create_pull.return_value = mock_pr
    
    tool = GithubTool()
    
    result = tool.create_pr(sample_ticket, sample_plan, "sentinel/SCRUM-789")
    
    assert isinstance(result, PRResult)
    assert result.pr_number == 42
    assert result.pr_url == "https://github.com/owner/repo/pull/42"
    assert result.title == "[SCRUM-789] Add login button"
    
    mock_repo.create_pull.assert_called_once()
    kwargs = mock_repo.create_pull.call_args[1]
    assert kwargs["title"] == "[SCRUM-789] Add login button"
    assert kwargs["head"] == "sentinel/SCRUM-789"
    assert kwargs["base"] == "main"
    assert "Architecture is cool" in kwargs["body"]

@patch("tools.github_tool.Github")
def test_create_pr_already_exists(mock_github_class, mock_env, sample_ticket, sample_plan):
    mock_gh_instance = MagicMock()
    mock_github_class.return_value = mock_gh_instance
    
    mock_repo = MagicMock()
    mock_gh_instance.get_repo.return_value = mock_repo
    
    # Simulate PR already exists
    error = GithubException(422, {"errors": [{"message": "already exists"}]})
    mock_repo.create_pull.side_effect = error
    
    # Mock finding the existing PR
    mock_existing_pr = MagicMock()
    mock_existing_pr.number = 43
    mock_existing_pr.html_url = "https://github.com/owner/repo/pull/43"
    mock_existing_pr.title = "Existing PR"
    mock_repo.get_pulls.return_value = [mock_existing_pr]
    
    tool = GithubTool()
    result = tool.create_pr(sample_ticket, sample_plan, "sentinel/SCRUM-789")
    
    assert result.pr_number == 43
    assert result.pr_url == "https://github.com/owner/repo/pull/43"
    mock_repo.get_pulls.assert_called_once_with(head="owner:sentinel/SCRUM-789")

@patch("tools.github_tool.Github")
def test_create_pr_other_error(mock_github_class, mock_env, sample_ticket, sample_plan):
    mock_gh_instance = MagicMock()
    mock_github_class.return_value = mock_gh_instance
    
    mock_repo = MagicMock()
    mock_gh_instance.get_repo.return_value = mock_repo
    
    # Simulate other error
    error = GithubException(500, {"message": "Server Error"})
    mock_repo.create_pull.side_effect = error
    
    tool = GithubTool()
    
    with pytest.raises(ValueError, match="Failed to create PR"):
        tool.create_pr(sample_ticket, sample_plan, "sentinel/SCRUM-789")
