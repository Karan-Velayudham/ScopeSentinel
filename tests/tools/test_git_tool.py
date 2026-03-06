import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from tools.git_tool import GitTool, GitResult
from git import InvalidGitRepositoryError, GitCommandError

@pytest.fixture
def mock_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_REPO_OWNER", "owner")
    monkeypatch.setenv("GITHUB_REPO_NAME", "repo")
    monkeypatch.setenv("GITHUB_REPO_LOCAL_PATH", str(tmp_path))

@patch("tools.git_tool.Repo")
def test_git_tool_init_existing_repo(mock_repo, mock_env, tmp_path):
    local_path = tmp_path / "repo"
    local_path.mkdir()
    
    tool = GitTool()
    assert tool.local_path == local_path
    assert tool.workspace_path == local_path
    mock_repo.assert_called_once_with(local_path)

@patch("tools.git_tool.Repo")
def test_git_tool_init_invalid_repo(mock_repo, mock_env, tmp_path):
    local_path = tmp_path / "repo"
    local_path.mkdir()
    
    # First call raises InvalidGitRepositoryError, meaning it's not a git repo
    # so it should rmtree and clone
    
    # We need to mock Repo.clone_from as well
    mock_repo.side_effect = InvalidGitRepositoryError()
    mock_repo.clone_from = MagicMock()
    
    tool = GitTool()
    
    mock_repo.clone_from.assert_called_once()
    assert mock_repo.clone_from.call_args[0][1] == local_path

@patch("tools.git_tool.Repo")
def test_prepare_branch(mock_repo_class, mock_env, tmp_path):
    local_path = tmp_path / "repo"
    local_path.mkdir()
    
    mock_repo_instance = MagicMock()
    mock_repo_class.return_value = mock_repo_instance
    
    mock_branch_main = MagicMock()
    mock_branch_main.name = "main"
    mock_repo_instance.branches = [mock_branch_main]
    
    tool = GitTool()
    
    # Test prepare branch
    ws = tool.prepare_branch("SCRUM-123")
    
    assert ws == local_path
    mock_repo_instance.git.checkout.assert_any_call("main")
    mock_repo_instance.remote.return_value.pull.assert_called_once()
    mock_repo_instance.git.checkout.assert_any_call("-b", "sentinel/SCRUM-123")

@patch("tools.git_tool.Repo")
def test_commit_and_push_with_changes(mock_repo_class, mock_env, tmp_path):
    local_path = tmp_path / "repo"
    local_path.mkdir()
    
    mock_repo_instance = MagicMock()
    mock_repo_class.return_value = mock_repo_instance
    
    mock_branch_main = MagicMock()
    mock_branch_main.name = "main"
    mock_repo_instance.branches = [mock_branch_main]
    
    # Simulate changes
    mock_repo_instance.index.diff.return_value = ["changed_file"]
    
    # Mock commit hexsha
    mock_commit = MagicMock()
    mock_commit.hexsha = "abcdef123"
    mock_repo_instance.index.commit.return_value = mock_commit
    
    tool = GitTool()
    
    result = tool.commit_and_push("SCRUM-123", "Summary")
    
    assert isinstance(result, GitResult)
    assert result.branch_name == "sentinel/SCRUM-123"
    assert result.commit_sha == "abcdef123"
    assert result.remote_url == "https://github.com/owner/repo"
    
    mock_repo_instance.git.add.assert_called_with(A=True)
    mock_repo_instance.index.commit.assert_called_once()
    mock_repo_instance.git.push.assert_called_once()

@patch("tools.git_tool.Repo")
def test_commit_and_push_no_changes(mock_repo_class, mock_env, tmp_path):
    local_path = tmp_path / "repo"
    local_path.mkdir()
    
    mock_repo_instance = MagicMock()
    mock_repo_class.return_value = mock_repo_instance
    
    mock_branch_main = MagicMock()
    mock_branch_main.name = "main"
    mock_repo_instance.branches = [mock_branch_main]
    
    # Simulate no changes
    mock_repo_instance.index.diff.return_value = []
    mock_repo_instance.untracked_files = []
    
    mock_commit = MagicMock()
    mock_commit.hexsha = "oldsha456"
    mock_repo_instance.head.commit = mock_commit
    
    tool = GitTool()
    
    result = tool.commit_and_push("SCRUM-123", "Summary")
    
    assert isinstance(result, GitResult)
    assert result.commit_sha == "oldsha456"
    
    mock_repo_instance.git.add.assert_called_with(A=True)
    mock_repo_instance.index.commit.assert_not_called()
    mock_repo_instance.git.push.assert_not_called()

@patch("tools.git_tool.Github")
@patch("tools.git_tool.Repo")
def test_clone_fallback_to_create(mock_repo_class, mock_github_class, mock_env, tmp_path):
    local_path = tmp_path / "repo"
    
    # Raise error on first clone attempt indicating repo not found
    error = GitCommandError("clone", 128, b"", b"not found")
    
    mock_repo_class.clone_from.side_effect = [error, MagicMock()]
    
    mock_gh_instance = MagicMock()
    mock_github_class.return_value = mock_gh_instance
    mock_user = MagicMock()
    mock_gh_instance.get_user.return_value = mock_user
    
    tool = GitTool()
    
    # Should have tried to create the repo
    mock_user.create_repo.assert_called_once_with(
        name="repo",
        description="Auto-created by ScopeSentinel for repo",
        private=False,
        auto_init=True
    )
    
    # clone_from should have been called twice
    assert mock_repo_class.clone_from.call_count == 2
