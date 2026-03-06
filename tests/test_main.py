import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from main import run_healthcheck, run_planner_workflow

pytestmark = pytest.mark.asyncio

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

@patch("main.GithubTool")
@patch("main.GitTool")
@patch("main.CoderAgent")
@patch("main.HITLGateway")
@patch("main.PlannerAgent")
@patch("main.JiraTool")
@patch("main._build_model")
@patch("main.agentscope")
async def test_run_planner_workflow_approve(
    mock_agentscope, mock_build_model, mock_jira_tool, mock_planner_agent,
    mock_hitl_gateway, mock_coder_agent, mock_git_tool, mock_github_tool
):
    # Setup mocks
    mock_jira_instance = MagicMock()
    mock_jira_tool.return_value = mock_jira_instance
    mock_ticket = MagicMock()
    mock_ticket.id = "SCRUM-1"
    mock_ticket.summary = "Test"
    mock_jira_instance.fetch_ticket.return_value = mock_ticket
    
    mock_planner_instance = MagicMock()
    mock_planner_agent.return_value = mock_planner_instance
    mock_plan = MagicMock()
    mock_planner_instance.plan = AsyncMock(return_value=mock_plan)
    
    mock_hitl_instance = MagicMock()
    mock_hitl_gateway.return_value = mock_hitl_instance
    mock_decision = MagicMock()
    mock_decision.action = "approve"
    mock_hitl_instance.present_and_await = AsyncMock(return_value=mock_decision)
    
    mock_git_instance = MagicMock()
    mock_git_tool.return_value = mock_git_instance
    mock_git_instance.prepare_branch.return_value = "/tmp/workspace"
    mock_git_result = MagicMock()
    mock_git_result.branch_name = "branch"
    mock_git_instance.commit_and_push.return_value = mock_git_result
    
    mock_coder_instance = MagicMock()
    mock_coder_agent.return_value = mock_coder_instance
    mock_coder_output = MagicMock()
    mock_coder_output.files_written = ["file.py"]
    mock_coder_output.workspace_path = "/tmp/workspace"
    mock_coder_instance.code_with_validation = AsyncMock(return_value=mock_coder_output)
    
    mock_gh_instance = MagicMock()
    mock_github_tool.return_value = mock_gh_instance
    
    # Run
    await run_planner_workflow("SCRUM-1")
    
    # Assertions
    mock_jira_instance.fetch_ticket.assert_called_once_with("SCRUM-1")
    mock_planner_instance.plan.assert_called_once_with(mock_ticket)
    mock_hitl_instance.present_and_await.assert_called_once_with(mock_plan)
    mock_jira_instance.update_ticket_with_plan.assert_called_once_with("SCRUM-1", mock_plan)
    mock_git_instance.prepare_branch.assert_called_once_with("SCRUM-1")
    mock_coder_instance.code_with_validation.assert_called_once_with(
        mock_ticket, mock_plan, workspace_override="/tmp/workspace"
    )
    mock_git_instance.commit_and_push.assert_called_once()
    mock_gh_instance.create_pr.assert_called_once()


@patch("main.HITLGateway")
@patch("main.PlannerAgent")
@patch("main.JiraTool")
@patch("main._build_model")
@patch("main.agentscope")
async def test_run_planner_workflow_reject(
    mock_agentscope, mock_build_model, mock_jira_tool, mock_planner_agent, mock_hitl_gateway, capsys
):
    mock_jira_instance = MagicMock()
    mock_jira_tool.return_value = mock_jira_instance
    mock_ticket = MagicMock()
    mock_jira_instance.fetch_ticket.return_value = mock_ticket
    
    mock_planner_instance = MagicMock()
    mock_planner_agent.return_value = mock_planner_instance
    mock_planner_instance.plan = AsyncMock()
    
    mock_hitl_instance = MagicMock()
    mock_hitl_gateway.return_value = mock_hitl_instance
    mock_decision = MagicMock()
    mock_decision.action = "reject"
    mock_hitl_instance.present_and_await = AsyncMock(return_value=mock_decision)
    
    await run_planner_workflow("SCRUM-2")
    
    captured = capsys.readouterr()
    assert "Workflow aborted by reviewer" in captured.out
    
    # Ensure downstream was not called
    mock_jira_instance.update_ticket_with_plan.assert_not_called()

@patch("main.HITLGateway")
@patch("main.PlannerAgent")
@patch("main.JiraTool")
@patch("main._build_model")
@patch("main.agentscope")
async def test_run_planner_workflow_max_revisions(
    mock_agentscope, mock_build_model, mock_jira_tool, mock_planner_agent, mock_hitl_gateway, capsys
):
    mock_jira_instance = MagicMock()
    mock_jira_tool.return_value = mock_jira_instance
    
    mock_planner_instance = MagicMock()
    mock_planner_agent.return_value = mock_planner_instance
    mock_planner_instance.plan = AsyncMock()
    mock_planner_instance.replan = AsyncMock()
    
    mock_hitl_instance = MagicMock()
    mock_hitl_gateway.return_value = mock_hitl_instance
    mock_decision = MagicMock()
    mock_decision.action = "modify"
    mock_decision.feedback = "Change it"
    
    # Will return "modify" endlessly
    mock_hitl_instance.present_and_await = AsyncMock(return_value=mock_decision)
    
    await run_planner_workflow("SCRUM-3")
    
    captured = capsys.readouterr()
    assert "Maximum revisions" in captured.out
    assert "Aborting" in captured.out
    
    assert mock_hitl_instance.present_and_await.call_count == 4 # MAX_REVISIONS + 1
    assert mock_planner_instance.replan.call_count == 3 # MAX_REVISIONS
