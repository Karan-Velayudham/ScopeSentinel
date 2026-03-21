import pytest
from unittest.mock import AsyncMock, MagicMock

from agents.planner_agent import (
    PlannerAgent,
    _build_user_message,
    _parse_plan,
    _extract_text,
    PlannerOutput,
)
from exceptions import MCPToolCallError


# ---------------------------------------------------------------------------
# Helper / pure function tests
# ---------------------------------------------------------------------------

def test_build_user_message():
    msg = _build_user_message("Ticket: SCRUM-123\nSummary: Add new feature")
    assert "SCRUM-123" in msg
    assert "Add new feature" in msg


def test_parse_plan():
    raw_response = '''
## Architecture Notes
We will use a standard MVC pattern with a new controller.

## Implementation Steps
1. Create the model
2. Create the view
3. Create the controller
'''
    steps, arch_notes = _parse_plan(raw_response)
    assert arch_notes == "We will use a standard MVC pattern with a new controller."
    assert len(steps) == 3
    assert steps[0] == "Create the model"
    assert steps[1] == "Create the view"
    assert steps[2] == "Create the controller"


def test_extract_text_from_content_list():
    mock_response = MagicMock()
    mock_response.content = [{"type": "text", "text": "hello world"}]
    assert _extract_text(mock_response) == "hello world"


def test_extract_text_fallback_to_str():
    mock_response = MagicMock()
    mock_response.content = []
    # str(mock) won't be "hello" but the function must not raise
    result = _extract_text(mock_response)
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# PlannerAgent.plan() — uses tool_registry dict
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_planner_agent_plan():
    # Build a mock tool_registry with "fetch_jira_ticket"
    mock_fetch = AsyncMock()
    mock_tool_response = MagicMock()
    mock_tool_response.content = [{"text": "Ticket: SCRUM-123\nSummary: Add new feature"}]
    mock_fetch.return_value = mock_tool_response
    tool_registry = {"fetch_jira_ticket": mock_fetch}

    mock_model = AsyncMock()
    mock_model_response = MagicMock()
    mock_model_response.content = [
        {
            "type": "text",
            "text": "## Architecture Notes\nTesting notes\n## Implementation Steps\n1. Do something\n2. Do nothing"
        }
    ]
    mock_model.return_value = mock_model_response

    agent = PlannerAgent(model=mock_model)
    output = await agent.plan("SCRUM-123", tool_registry)

    assert isinstance(output, PlannerOutput)
    assert output.ticket_id == "SCRUM-123"
    assert output.architecture_notes == "Testing notes"
    assert len(output.steps) == 2
    assert output.steps[0] == "Do something"

    # fetch_jira_ticket called with correct ticket_id
    mock_fetch.assert_called_once_with(ticket_id="SCRUM-123")

    # LLM called exactly once with system + user messages
    mock_model.assert_called_once()
    call_args = mock_model.call_args[0][0]
    assert len(call_args) == 2
    assert call_args[0]["role"] == "system"
    assert call_args[1]["role"] == "user"


@pytest.mark.asyncio
async def test_planner_agent_plan_missing_tool():
    """MCPToolCallError is raised when fetch_jira_ticket is not in the registry."""
    agent = PlannerAgent(model=AsyncMock())
    with pytest.raises(MCPToolCallError):
        await agent.plan("SCRUM-999", {})


# ---------------------------------------------------------------------------
# PlannerAgent.replan() — uses tool_registry dict
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_planner_agent_replan():
    mock_fetch = AsyncMock()
    mock_tool_response = MagicMock()
    mock_tool_response.content = [{"text": "Ticket: SCRUM-123"}]
    mock_fetch.return_value = mock_tool_response
    tool_registry = {"fetch_jira_ticket": mock_fetch}

    mock_model = AsyncMock()
    mock_model_response = MagicMock()
    mock_model_response.content = [
        {
            "type": "text",
            "text": "## Architecture Notes\nRevised notes\n## Implementation Steps\n1. Do something better\n2. Do nothing still"
        }
    ]
    mock_model.return_value = mock_model_response

    previous_plan = PlannerOutput(
        ticket_id="SCRUM-123",
        summary="Fetched via MCP",
        steps=["Old step"],
        architecture_notes="Old notes",
        raw_plan="Old raw plan"
    )

    agent = PlannerAgent(model=mock_model)
    output = await agent.replan("SCRUM-123", tool_registry, "Make it better", previous_plan)

    assert isinstance(output, PlannerOutput)
    assert output.architecture_notes == "Revised notes"
    assert len(output.steps) == 2
    assert output.steps[0] == "Do something better"

    mock_model.assert_called_once()
    call_args = mock_model.call_args[0][0]
    # should be: system, user, assistant (prev plan), user (feedback)
    assert len(call_args) == 4
    assert call_args[0]["role"] == "system"
    assert call_args[1]["role"] == "user"
    assert call_args[2]["role"] == "assistant"
    assert call_args[2]["content"] == "Old raw plan"
    assert call_args[3]["role"] == "user"
    assert "Make it better" in call_args[3]["content"]
