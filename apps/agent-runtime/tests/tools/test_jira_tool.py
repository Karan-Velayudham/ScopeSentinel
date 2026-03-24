import pytest
from unittest.mock import MagicMock, patch
from tools.jira_tool import JiraTool, JiraTicket
from agents.planner_agent import PlannerOutput
from jira import JIRAError

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("JIRA_URL", "https://test.atlassian.net")
    monkeypatch.setenv("JIRA_USERNAME", "user@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "token")

@patch("tools.jira_tool.JIRA")
def test_jira_tool_init(mock_jira_class, mock_env):
    tool = JiraTool()
    mock_jira_class.assert_called_once_with(
        server="https://test.atlassian.net",
        basic_auth=("user@example.com", "token")
    )

@patch("tools.jira_tool.JIRA")
def test_fetch_ticket_success(mock_jira_class, mock_env):
    mock_jira_instance = MagicMock()
    mock_jira_class.return_value = mock_jira_instance
    
    mock_issue = MagicMock()
    mock_issue.fields.summary = "Test summary"
    mock_issue.fields.description = "Test description"
    mock_issue.fields.status = "In Progress"
    mock_issue.fields.issuetype = "Bug"
    # Custom field for AC
    mock_issue.fields.customfield_10016 = "AC 1"
    
    mock_jira_instance.issue.return_value = mock_issue
    
    tool = JiraTool()
    ticket = tool.fetch_ticket("SCRUM-1")
    
    assert isinstance(ticket, JiraTicket)
    assert ticket.id == "SCRUM-1"
    assert ticket.summary == "Test summary"
    assert ticket.description == "Test description"
    assert ticket.status == "In Progress"
    assert ticket.issue_type == "Bug"
    assert ticket.acceptance_criteria == "AC 1"

@patch("tools.jira_tool.JIRA")
def test_fetch_ticket_not_found(mock_jira_class, mock_env):
    mock_jira_instance = MagicMock()
    mock_jira_class.return_value = mock_jira_instance
    
    error = JIRAError(status_code=404, text="Not Found")
    mock_jira_instance.issue.side_effect = error
    
    tool = JiraTool()
    with pytest.raises(ValueError, match="not found in Jira"):
        tool.fetch_ticket("SCRUM-999")

@patch("tools.jira_tool.JIRA")
def test_fetch_ticket_access_denied(mock_jira_class, mock_env):
    mock_jira_instance = MagicMock()
    mock_jira_class.return_value = mock_jira_instance
    
    error = JIRAError(status_code=403, text="Forbidden")
    mock_jira_instance.issue.side_effect = error
    
    tool = JiraTool()
    with pytest.raises(ValueError, match="Access denied to ticket"):
        tool.fetch_ticket("SCRUM-999")

def test_serialize_field():
    assert JiraTool._serialize_field("test") == "test"
    assert JiraTool._serialize_field(["a", "b"]) == "a\nb"
    
    # Mock property holder
    class PropHolder:
        def __init__(self, val):
            self.value = val
    
    assert JiraTool._serialize_field(PropHolder("hi")) == "hi"

def test_extract_ac_from_description():
    tool = JiraTool()
    
    # Has acceptance criteria heading
    desc = """
Some description.
h3. Acceptance Criteria
1. Test
2. Test 2
h3. Notes
Something else
"""
    ac = tool._extract_ac_from_description(desc)
    assert "1. Test\n2. Test 2" == ac

@patch("tools.jira_tool.JIRA")
def test_update_ticket_with_plan(mock_jira_class, mock_env):
    mock_jira_instance = MagicMock()
    mock_jira_class.return_value = mock_jira_instance
    
    mock_issue = MagicMock()
    mock_jira_instance.issue.return_value = mock_issue
    
    plan = PlannerOutput(
        ticket_id="SCRUM-1",
        summary="summary",
        steps=["Step 1"],
        architecture_notes="Notes",
        raw_plan="raw"
    )
    
    tool = JiraTool()
    tool.update_ticket_with_plan("SCRUM-1", plan)
    
    mock_issue.update.assert_called_once()
    kwargs = mock_issue.update.call_args[1]
    assert "description" in kwargs["fields"]
    desc = kwargs["fields"]["description"]
    assert "h2. ScopeSentinel Implementation Plan" in desc
    assert "h3. Architecture Notes\nNotes" in desc
    assert "h3. Implementation Steps\n# Step 1" in desc
