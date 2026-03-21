import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from main import run_healthcheck, run_planner_workflow

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tool_registry():
    """Minimal tool_registry used by run_planner_workflow tests."""
    fetch_res = MagicMock()
    fetch_res.content = [{"text": "Ticket: SCRUM-1\nSummary: Test ticket"}]

    update_res = MagicMock()
    update_res.content = [{"text": "Ticket updated successfully."}]

    return {
        "fetch_jira_ticket": AsyncMock(return_value=fetch_res),
        "update_jira_ticket": AsyncMock(return_value=update_res),
        "prepare_git_branch": AsyncMock(return_value=MagicMock(content=[{"text": "Branch prepared at /tmp/ws"}])),
        "commit_and_push": AsyncMock(return_value=MagicMock(content=[{"text": "Pushed"}])),
        "create_pull_request": AsyncMock(return_value=MagicMock(content=[{"text": "PR created"}])),
    }


def _make_mock_clients():
    """Return a list of closeable mock clients."""
    client = AsyncMock()
    return [client]


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@patch("main.agentscope")
@patch("main._build_model")
async def test_run_healthcheck(mock_build_model, mock_agentscope, capsys):
    mock_model = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = [{"type": "text", "text": "ScopeSentinel is ready."}]
    mock_model.return_value = mock_response
    mock_build_model.return_value = mock_model

    await run_healthcheck()

    mock_agentscope.init.assert_called_once_with(project="ScopeSentinel", name="HealthCheck")
    captured = capsys.readouterr()
    assert "Health check passed: ScopeSentinel is ready." in captured.out


# ---------------------------------------------------------------------------
# Full workflow — approve
# ---------------------------------------------------------------------------

@patch("main.load_client_pool")
@patch("main.CoderAgent")
@patch("main.HITLGateway")
@patch("main.PlannerAgent")
@patch("main._build_model")
@patch("main.agentscope")
async def test_run_planner_workflow_approve(
    mock_agentscope, mock_build_model, mock_planner_cls,
    mock_hitl_cls, mock_coder_cls, mock_load_pool
):
    tool_registry = _make_tool_registry()
    mock_clients = _make_mock_clients()
    mock_load_pool.return_value = (mock_clients, tool_registry)

    mock_plan = MagicMock()
    mock_plan.raw_plan = "The plan"
    mock_planner = MagicMock()
    mock_planner.plan = AsyncMock(return_value=mock_plan)
    mock_planner_cls.return_value = mock_planner

    mock_decision = MagicMock()
    mock_decision.action = "approve"
    mock_hitl = MagicMock()
    mock_hitl.present_and_await = AsyncMock(return_value=mock_decision)
    mock_hitl_cls.return_value = mock_hitl

    mock_coder_output = MagicMock()
    mock_coder_output.files_written = ["file.py"]
    mock_coder_output.workspace_path = "/tmp/ws"
    mock_coder = MagicMock()
    mock_coder.code_with_validation = AsyncMock(return_value=mock_coder_output)
    mock_coder_cls.return_value = mock_coder

    await run_planner_workflow("SCRUM-1")

    mock_load_pool.assert_called_once_with("mcp_servers.yaml")
    mock_planner.plan.assert_called_once_with("SCRUM-1", tool_registry)
    mock_hitl.present_and_await.assert_called_once_with(mock_plan)
    tool_registry["update_jira_ticket"].assert_called_once()
    mock_coder.code_with_validation.assert_called_once_with(
        ticket_id="SCRUM-1",
        ticket_content=tool_registry["fetch_jira_ticket"].return_value.content[0]["text"],
        plan=mock_plan,
        tool_registry=tool_registry,
    )
    # All clients must be closed (via finally)
    for client in mock_clients:
        client.close.assert_called_once()


# ---------------------------------------------------------------------------
# Full workflow — reject
# ---------------------------------------------------------------------------

@patch("main.load_client_pool")
@patch("main.HITLGateway")
@patch("main.PlannerAgent")
@patch("main._build_model")
@patch("main.agentscope")
async def test_run_planner_workflow_reject(
    mock_agentscope, mock_build_model, mock_planner_cls,
    mock_hitl_cls, mock_load_pool, capsys
):
    tool_registry = _make_tool_registry()
    mock_clients = _make_mock_clients()
    mock_load_pool.return_value = (mock_clients, tool_registry)

    mock_planner = MagicMock()
    mock_planner.plan = AsyncMock(return_value=MagicMock())
    mock_planner_cls.return_value = mock_planner

    mock_decision = MagicMock()
    mock_decision.action = "reject"
    mock_hitl = MagicMock()
    mock_hitl.present_and_await = AsyncMock(return_value=mock_decision)
    mock_hitl_cls.return_value = mock_hitl

    await run_planner_workflow("SCRUM-2")

    captured = capsys.readouterr()
    assert "Workflow aborted by reviewer" in captured.out
    # update_jira_ticket must NOT be called
    tool_registry["update_jira_ticket"].assert_not_called()
    # Clients still closed
    for client in mock_clients:
        client.close.assert_called_once()


# ---------------------------------------------------------------------------
# Full workflow — max revisions
# ---------------------------------------------------------------------------

@patch("main.load_client_pool")
@patch("main.HITLGateway")
@patch("main.PlannerAgent")
@patch("main._build_model")
@patch("main.agentscope")
async def test_run_planner_workflow_max_revisions(
    mock_agentscope, mock_build_model, mock_planner_cls,
    mock_hitl_cls, mock_load_pool, capsys
):
    from main import MAX_REVISIONS

    tool_registry = _make_tool_registry()
    mock_clients = _make_mock_clients()
    mock_load_pool.return_value = (mock_clients, tool_registry)

    mock_planner = MagicMock()
    mock_planner.plan = AsyncMock(return_value=MagicMock())
    mock_planner.replan = AsyncMock(return_value=MagicMock())
    mock_planner_cls.return_value = mock_planner

    mock_decision = MagicMock()
    mock_decision.action = "modify"
    mock_decision.feedback = "Change it"
    mock_hitl = MagicMock()
    mock_hitl.present_and_await = AsyncMock(return_value=mock_decision)
    mock_hitl_cls.return_value = mock_hitl

    await run_planner_workflow("SCRUM-3")

    captured = capsys.readouterr()
    assert "Maximum revisions" in captured.out
    assert "Aborting" in captured.out

    assert mock_hitl.present_and_await.call_count == MAX_REVISIONS + 1
    assert mock_planner.replan.call_count == MAX_REVISIONS
    for client in mock_clients:
        client.close.assert_called_once()
