import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from agents.coder_agent import (
    CoderAgent,
    CoderOutput,
    _build_coding_prompt,
    _parse_files,
    _parse_deletions
)
from agents.planner_agent import PlannerOutput


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_plan():
    return PlannerOutput(
        ticket_id="SCRUM-456",
        summary="Implement code",
        steps=["Create file A", "Delete file B"],
        architecture_notes="Do it well",
        raw_plan="Original plan"
    )


@pytest.fixture
def mock_tool_registry():
    """A minimal tool_registry that fakes all git/github MCP tools."""
    prepare_res = MagicMock()
    prepare_res.content = [{"text": "Branch prepared at /tmp/workspace-SCRUM-456"}]

    commit_res = MagicMock()
    commit_res.content = [{"text": "Pushed branch sentinel/SCRUM-456"}]

    pr_res = MagicMock()
    pr_res.content = [{"text": "PR created: https://github.com/org/repo/pull/1"}]

    return {
        "prepare_git_branch": AsyncMock(return_value=prepare_res),
        "commit_and_push": AsyncMock(return_value=commit_res),
        "create_pull_request": AsyncMock(return_value=pr_res),
    }


# ---------------------------------------------------------------------------
# Pure function tests (unchanged behaviour)
# ---------------------------------------------------------------------------

def test_build_coding_prompt(sample_plan):
    prompt = _build_coding_prompt("SCRUM-456", "ticket body", sample_plan)
    assert "**Ticket:** SCRUM-456" in prompt
    assert "**Architecture Notes:**\nDo it well" in prompt
    assert "1. Create file A" in prompt
    assert "2. Delete file B" in prompt


def test_parse_files():
    raw = """
Some text
### `src/main.py`
```python
print("Hello")
```
More text
### `src/utils.py`
```
def add(a, b):
    return a + b
```
"""
    files = _parse_files(raw)
    assert len(files) == 2
    assert "src/main.py" in files
    assert 'print("Hello")\n' in files["src/main.py"]
    assert "src/utils.py" in files
    assert "def add(a, b):\n    return a + b\n" in files["src/utils.py"]


def test_parse_deletions():
    raw = """
I will delete this now.
### DELETE `old_dir/`
And this file.
### DELETE `old_file.py`
"""
    deletions = _parse_deletions(raw)
    assert len(deletions) == 2
    assert deletions[0] == "old_dir/"
    assert deletions[1] == "old_file.py"


# ---------------------------------------------------------------------------
# CoderAgent.code() — workspace + file writing (no tool_registry needed)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_coder_agent_code(sample_plan, tmp_path):
    mock_model = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = [
        {
            "type": "text",
            "text": "### DELETE `to_delete.txt`\n### `new_file.py`\n```python\nprint(1)\n```"
        }
    ]
    mock_model.return_value = mock_response

    # Setup the workspace with a file to delete
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    file_to_delete = workspace / "to_delete.txt"
    file_to_delete.touch()

    agent = CoderAgent(model=mock_model)
    output = await agent.code("SCRUM-456", "ticket body", sample_plan, workspace_override=workspace)

    assert isinstance(output, CoderOutput)
    assert output.ticket_id == "SCRUM-456"
    assert "new_file.py" in output.files_written

    new_file_path = workspace / "new_file.py"
    assert new_file_path.exists()
    assert new_file_path.read_text() == "print(1)\n"
    assert not file_to_delete.exists()


# ---------------------------------------------------------------------------
# CoderAgent.code_with_validation() — uses tool_registry
# ---------------------------------------------------------------------------

@patch("agents.coder_agent.CoderAgent.code")
@pytest.mark.asyncio
async def test_code_with_validation_success(mock_code, sample_plan, mock_tool_registry, tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    initial_output = CoderOutput(
        ticket_id="SCRUM-456",
        workspace_path=str(workspace),
        files_written=["test.py"],
        raw_response="Initial raw"
    )
    mock_code.return_value = initial_output

    agent = CoderAgent(model=AsyncMock())

    with patch("sandbox.sandbox_runner.SandboxRunner"):
        with patch("sandbox.validator.CodeValidator") as MockValidator:
            mock_vi = MockValidator.return_value
            mock_result = MagicMock()
            mock_result.passed = True
            mock_vi.validate.return_value = mock_result

            output = await agent.code_with_validation(
                "SCRUM-456", "ticket body", sample_plan, mock_tool_registry
            )

    assert output is initial_output
    mock_vi.validate.assert_called_once()
    # prepare_git_branch should have been called
    mock_tool_registry["prepare_git_branch"].assert_called_once_with(ticket_id="SCRUM-456")
    # commit + PR should have been called (workspace_path resolved from prep result)
    mock_tool_registry["commit_and_push"].assert_called_once()
    mock_tool_registry["create_pull_request"].assert_called_once()


@patch("agents.coder_agent.CoderAgent.code")
@pytest.mark.asyncio
async def test_code_with_validation_retry(mock_code, sample_plan, mock_tool_registry, tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    initial_output = CoderOutput(
        ticket_id="SCRUM-456",
        workspace_path=str(workspace),
        files_written=["test.py"],
        raw_response="Initial raw"
    )
    mock_code.return_value = initial_output

    mock_model = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = [
        {"type": "text", "text": "### `test.py`\n```python\nprint('fixed')\n```"}
    ]
    mock_model.return_value = mock_response

    agent = CoderAgent(model=mock_model)

    with patch("sandbox.sandbox_runner.SandboxRunner"):
        with patch("sandbox.validator.CodeValidator") as MockValidator:
            mock_vi = MockValidator.return_value

            fail_result = MagicMock()
            fail_result.passed = False
            fail_result.output = "SyntaxError"

            pass_result = MagicMock()
            pass_result.passed = True

            mock_vi.validate.side_effect = [fail_result, pass_result]

            output = await agent.code_with_validation(
                "SCRUM-456", "ticket body", sample_plan, mock_tool_registry
            )

    assert mock_vi.validate.call_count == 2
    agent.model.assert_called_once()

    fixed_file = workspace / "test.py"
    assert fixed_file.read_text() == "print('fixed')\n"
    assert output.files_written == ["test.py"]
