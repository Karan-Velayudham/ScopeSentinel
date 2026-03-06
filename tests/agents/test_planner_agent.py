import pytest
from unittest.mock import AsyncMock, MagicMock

from agents.planner_agent import (
    PlannerAgent,
    _build_user_message,
    _parse_plan,
    PlannerOutput,
)
from tools.jira_tool import JiraTicket

pytestmark = pytest.mark.asyncio

@pytest.fixture
def sample_ticket():
    return JiraTicket(
        id="SCRUM-123",
        summary="Add new feature",
        description="We need a new feature that does X.",
        status="To Do",
        issue_type="Task",
        acceptance_criteria="1. X works properly\n2. Tests are passing",
    )

def test_build_user_message(sample_ticket):
    msg = _build_user_message(sample_ticket)
    assert "**Ticket ID:** SCRUM-123" in msg
    assert "**Type:** Task" in msg
    assert "**Summary:** Add new feature" in msg
    assert "**Description:**" in msg
    assert "We need a new feature that does X." in msg
    assert "**Acceptance Criteria:**" in msg
    assert "1. X works properly" in msg

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

async def test_planner_agent_plan(sample_ticket):
    mock_model = AsyncMock()
    # Mock the response structure: Model returns a MagicMock/AsyncMock that behaves like the expected response
    mock_response = MagicMock()
    mock_response.content = [
        {
            "type": "text",
            "text": "## Architecture Notes\nTesting notes\n## Implementation Steps\n1. Do something\n2. Do nothing"
        }
    ]
    mock_model.return_value = mock_response

    agent = PlannerAgent(model=mock_model)
    output = await agent.plan(sample_ticket)

    assert isinstance(output, PlannerOutput)
    assert output.ticket_id == "SCRUM-123"
    assert output.summary == "Add new feature"
    assert output.architecture_notes == "Testing notes"
    assert len(output.steps) == 2
    assert output.steps[0] == "Do something"
    
    # Verify the model was called
    mock_model.assert_called_once()
    call_args = mock_model.call_args[0][0] # The messages list
    assert len(call_args) == 2
    assert call_args[0]["role"] == "system"
    assert call_args[1]["role"] == "user"

async def test_planner_agent_replan(sample_ticket):
    mock_model = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = [
        {
            "type": "text",
            "text": "## Architecture Notes\nRevised notes\n## Implementation Steps\n1. Do something better\n2. Do nothing still"
        }
    ]
    mock_model.return_value = mock_response

    agent = PlannerAgent(model=mock_model)
    
    previous_plan = PlannerOutput(
        ticket_id="SCRUM-123",
        summary="Add new feature",
        steps=["Old step"],
        architecture_notes="Old notes",
        raw_plan="Old raw plan"
    )

    output = await agent.replan(sample_ticket, "Make it better", previous_plan)

    assert isinstance(output, PlannerOutput)
    assert output.architecture_notes == "Revised notes"
    assert len(output.steps) == 2
    assert output.steps[0] == "Do something better"
    
    mock_model.assert_called_once()
    call_args = mock_model.call_args[0][0] # The messages list
    assert len(call_args) == 4
    assert call_args[0]["role"] == "system"
    assert call_args[1]["role"] == "user"
    assert call_args[2]["role"] == "assistant"
    assert call_args[2]["content"] == "Old raw plan"
    assert call_args[3]["role"] == "user"
    assert "Make it better" in call_args[3]["content"]

