import pytest
from unittest.mock import patch, MagicMock
from hitl.hitl_gateway import HITLGateway, HITLDecision, _prompt_decision, _print_plan
from agents.planner_agent import PlannerOutput

@pytest.fixture
def sample_plan():
    return PlannerOutput(
        ticket_id="SCRUM-123",
        summary="A summary",
        steps=["Step 1"],
        architecture_notes="Notes",
        raw_plan="raw"
    )

def test_print_plan(sample_plan, capsys):
    _print_plan(sample_plan)
    captured = capsys.readouterr()
    assert "PLAN REVIEW — SCRUM-123" in captured.out
    assert "Summary: A summary" in captured.out
    assert "Architecture Notes:" in captured.out
    assert "1. Step 1" in captured.out

@patch("builtins.input")
def test_prompt_decision_approve(mock_input):
    mock_input.return_value = "a"
    decision = _prompt_decision()
    assert decision.action == "approve"
    assert decision.feedback == ""

@patch("builtins.input")
def test_prompt_decision_reject(mock_input):
    mock_input.return_value = "r"
    decision = _prompt_decision()
    assert decision.action == "reject"
    assert decision.feedback == ""

@patch("builtins.input")
def test_prompt_decision_modify_valid(mock_input):
    # first action is m, then asks for feedback
    mock_input.side_effect = ["m", "Please change this"]
    decision = _prompt_decision()
    assert decision.action == "modify"
    assert decision.feedback == "Please change this"

@patch("builtins.input")
def test_prompt_decision_modify_empty_feedback(mock_input, capsys):
    # m -> empty feedback -> top of loop -> m -> valid feedback
    mock_input.side_effect = ["m", "", "m", "Better feedback"]
    decision = _prompt_decision()
    
    captured = capsys.readouterr()
    assert "Feedback cannot be empty" in captured.out
    assert decision.action == "modify"
    assert decision.feedback == "Better feedback"

@patch("builtins.input")
def test_prompt_decision_invalid_then_approve(mock_input, capsys):
    mock_input.side_effect = ["x", "a"]
    decision = _prompt_decision()
    
    captured = capsys.readouterr()
    assert "Invalid input" in captured.out
    assert decision.action == "approve"

@patch("hitl.hitl_gateway._prompt_decision")
@patch("hitl.hitl_gateway._print_plan")
@pytest.mark.asyncio
async def test_gateway_present_and_await(mock_print, mock_prompt, sample_plan):
    mock_prompt.return_value = HITLDecision(action="approve")
    
    gateway = HITLGateway()
    decision = await gateway.present_and_await(sample_plan)
    
    assert decision.action == "approve"
    mock_print.assert_called_once_with(sample_plan)
    mock_prompt.assert_called_once()
