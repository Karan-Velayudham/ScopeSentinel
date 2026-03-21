import pytest
from unittest.mock import MagicMock
from pathlib import Path

from sandbox.sandbox_runner import SandboxRunner, SandboxResult
from sandbox.validator import CodeValidator, ValidationResult

@pytest.fixture
def mock_runner(tmp_path):
    runner = MagicMock(spec=SandboxRunner)
    runner.workspace_path = tmp_path
    return runner

def test_validator_no_files(mock_runner):
    validator = CodeValidator(mock_runner)
    result = validator.validate()
    
    assert result.passed is True
    assert "No applicable files" in result.output
    assert len(result.checks_run) == 0
    mock_runner.run.assert_not_called()

def test_validator_all_pass(mock_runner, tmp_path):
    (tmp_path / "main.py").touch()
    (tmp_path / "script.sh").touch()
    (tmp_path / "test_main.py").touch()
    
    # Mock runner.run to return success
    mock_runner.run.return_value = SandboxResult(0, "success_out", "")
    
    validator = CodeValidator(mock_runner)
    result = validator.validate()
    
    assert result.passed is True
    assert len(result.checks_run) == 4
    assert result.checks_run == [
        "Python syntax (py_compile)",
        "Shell syntax (script.sh)",
        "Flake8 lint",
        "Pytest"
    ]
    assert mock_runner.run.call_count == 4

def test_validator_python_syntax_fails(mock_runner, tmp_path):
    (tmp_path / "main.py").touch()
    
    err_result = SandboxResult(1, "", "SyntaxError")
    mock_runner.run.return_value = err_result
    
    validator = CodeValidator(mock_runner)
    result = validator.validate()
    
    assert result.passed is False
    assert len(result.checks_run) == 1
    assert result.checks_run == ["Python syntax (py_compile)"]
    assert "SyntaxError" in result.output

def test_validator_flake8_fails(mock_runner, tmp_path):
    (tmp_path / "main.py").touch()
    
    # Python syntax passes, flake8 fails
    pass_result = SandboxResult(0, "ok", "")
    fail_result = SandboxResult(1, "E501 line too long", "")
    mock_runner.run.side_effect = [pass_result, fail_result]
    
    validator = CodeValidator(mock_runner)
    result = validator.validate()
    
    assert result.passed is False
    assert len(result.checks_run) == 2
    assert result.checks_run == ["Python syntax (py_compile)", "Flake8 lint"]
    assert "line too long" in result.output
