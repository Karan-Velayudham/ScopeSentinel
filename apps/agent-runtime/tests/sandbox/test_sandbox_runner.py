import pytest
from unittest.mock import MagicMock, patch
from sandbox.sandbox_runner import SandboxRunner, SandboxResult
from docker.errors import DockerException, ContainerError

@patch("sandbox.sandbox_runner.docker.from_env")
def test_sandbox_runner_init_success(mock_from_env, tmp_path):
    mock_client = MagicMock()
    mock_from_env.return_value = mock_client
    
    runner = SandboxRunner(tmp_path)
    
    # Should resolve path and default image
    assert runner.workspace_path == tmp_path.resolve()
    assert runner.image == "python:3.12-slim"
    
    # Needs to ping
    mock_client.ping.assert_called_once()

@patch("sandbox.sandbox_runner.docker.from_env")
def test_sandbox_runner_init_docker_error(mock_from_env, tmp_path):
    mock_from_env.side_effect = DockerException("No docker daemon")
    
    with pytest.raises(RuntimeError, match="Could not connect to Docker daemon"):
        SandboxRunner(tmp_path)

@patch("sandbox.sandbox_runner.docker.from_env")
def test_sandbox_runner_run_success(mock_from_env, tmp_path):
    mock_client = MagicMock()
    mock_from_env.return_value = mock_client
    
    # mock containers run
    mock_client.containers.run.return_value = b"Hello from docker"
    
    runner = SandboxRunner(tmp_path)
    result = runner.run("echo 'Hello from docker'")
    
    assert isinstance(result, SandboxResult)
    assert result.exit_code == 0
    assert result.stdout == "Hello from docker"
    assert result.stderr == ""
    assert result.success is True
    
    # verify run arguments
    mock_client.containers.run.assert_called_once()
    kwargs = mock_client.containers.run.call_args[1]
    assert kwargs["command"] == ["sh", "-c", "echo 'Hello from docker'"]
    assert str(tmp_path.resolve()) in kwargs["volumes"]
    assert kwargs["remove"] is True

@patch("sandbox.sandbox_runner.docker.from_env")
def test_sandbox_runner_run_container_error(mock_from_env, tmp_path):
    mock_client = MagicMock()
    mock_from_env.return_value = mock_client
    
    # Create a mock ContainerError
    mock_container = MagicMock()
    error = ContainerError(
        container=mock_container,
        exit_status=127,
        command="badcmd",
        image="python:3.12-slim",
        stderr=b"command not found"
    )
    mock_client.containers.run.side_effect = error
    
    runner = SandboxRunner(tmp_path)
    result = runner.run("badcmd")
    
    assert isinstance(result, SandboxResult)
    assert result.exit_code == 127
    assert result.stdout == ""
    assert result.stderr == "command not found"
    assert result.success is False

@patch("sandbox.sandbox_runner.docker.from_env")
def test_sandbox_runner_run_other_error(mock_from_env, tmp_path):
    mock_client = MagicMock()
    mock_from_env.return_value = mock_client
    
    # Raise a generic exception
    mock_client.containers.run.side_effect = Exception("Out of memory")
    
    runner = SandboxRunner(tmp_path)
    result = runner.run("hugecmd")
    
    assert isinstance(result, SandboxResult)
    assert result.exit_code == 1
    assert result.stderr == "Out of memory"
    assert result.success is False

def test_sandbox_result_summary():
    res1 = SandboxResult(0, "ok", "")
    assert res1.summary() == "STDOUT:\nok"
    
    res2 = SandboxResult(1, "", "error")
    assert res2.summary() == "STDERR:\nerror"
    
    res3 = SandboxResult(1, "out", "err")
    assert res3.summary() == "STDOUT:\nout\nSTDERR:\nerr"
    
    res4 = SandboxResult(1, "", "")
    assert res4.summary() == "(no output)"
