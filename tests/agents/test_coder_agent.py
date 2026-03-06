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
from tools.jira_tool import JiraTicket
from agents.planner_agent import PlannerOutput

@pytest.fixture
def sample_ticket():
    return JiraTicket(
        id="SCRUM-456",
        summary="Implement code",
        description="Write the actual code",
        status="In Progress",
        issue_type="Task",
        acceptance_criteria=""
    )

@pytest.fixture
def sample_plan():
    return PlannerOutput(
        ticket_id="SCRUM-456",
        summary="Implement code",
        steps=["Create file A", "Delete file B"],
        architecture_notes="Do it well",
        raw_plan="Original plan"
    )

def test_build_coding_prompt(sample_ticket, sample_plan):
    prompt = _build_coding_prompt(sample_ticket, sample_plan)
    assert "**Ticket:** SCRUM-456 — Implement code" in prompt
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

@pytest.mark.asyncio
async def test_coder_agent_code(sample_ticket, sample_plan, tmp_path):
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
    output = await agent.code(sample_ticket, sample_plan, workspace_override=workspace)

    assert isinstance(output, CoderOutput)
    assert output.ticket_id == "SCRUM-456"
    assert "new_file.py" in output.files_written
    
    # Check if new file was created
    new_file_path = workspace / "new_file.py"
    assert new_file_path.exists()
    assert new_file_path.read_text() == "print(1)\n"
    
    # Check if old file was deleted
    assert not file_to_delete.exists()

@patch("agents.coder_agent.CoderAgent.code")
@pytest.mark.asyncio
async def test_coder_agent_code_with_validation_success(mock_code, sample_ticket, sample_plan, tmp_path):
    # Mock output from .code()
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
    
    # Mock SandboxRunner and Validator to return success
    with patch("sandbox.sandbox_runner.SandboxRunner") as MockRunner:
        with patch("sandbox.validator.CodeValidator") as MockValidator:
            mock_validator_instance = MockValidator.return_value
            mock_result = MagicMock()
            mock_result.passed = True
            mock_validator_instance.validate.return_value = mock_result
            
            output = await agent.code_with_validation(sample_ticket, sample_plan, workspace_override=workspace)
            
            assert output is initial_output
            mock_validator_instance.validate.assert_called_once()
            # Agent's model should not be called since validation passed
            agent.model.assert_not_called()

@patch("agents.coder_agent.CoderAgent.code")
@pytest.mark.asyncio
async def test_coder_agent_code_with_validation_retry(mock_code, sample_ticket, sample_plan, tmp_path):
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
    # Provide corrected files in the response
    mock_response.content = [
        {
            "type": "text",
            "text": "### `test.py`\n```python\nprint('fixed')\n```"
        }
    ]
    mock_model.return_value = mock_response

    agent = CoderAgent(model=mock_model)
    
    with patch("sandbox.sandbox_runner.SandboxRunner") as MockRunner:
        with patch("sandbox.validator.CodeValidator") as MockValidator:
            mock_validator_instance = MockValidator.return_value
            
            # Fail first validation, pass second
            fail_result = MagicMock()
            fail_result.passed = False
            fail_result.output = "SyntaxError"
            
            pass_result = MagicMock()
            pass_result.passed = True
            
            mock_validator_instance.validate.side_effect = [fail_result, pass_result]
            
            output = await agent.code_with_validation(sample_ticket, sample_plan, workspace_override=workspace)
            
            # Assert validation called twice
            assert mock_validator_instance.validate.call_count == 2
            
            # Model called once for self-correction
            agent.model.assert_called_once()
            
            # Verify file was written with corrected content
            fixed_file = workspace / "test.py"
            assert fixed_file.read_text() == "print('fixed')\n"
            
            assert output.files_written == ["test.py"]
            assert output.raw_response == "### `test.py`\n```python\nprint('fixed')\n```"
