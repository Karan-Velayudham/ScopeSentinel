import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

from tools.jira_tool import JiraTool
from tools.git_tool import GitTool
from tools.github_tool import GithubTool
from tools.search_tool import search_codebase
from knowledge.ingest import ingest_directory, init_collection

logger = logging.getLogger(__name__)

mcp = FastMCP("ScopeSentinel Tools")

_jira = None
_git = None
_gh = None

def get_jira():
    global _jira
    if not _jira:
        _jira = JiraTool()
    return _jira

def get_git():
    global _git
    if not _git:
        _git = GitTool()
    return _git

def get_gh():
    global _gh
    if not _gh:
        _gh = GithubTool()
    return _gh

@mcp.tool()
def fetch_jira_ticket(ticket_id: str) -> str:
    """Fetch details of a Jira ticket."""
    jira = get_jira()
    ticket = jira.fetch_ticket(ticket_id)
    return (
        f"Ticket: {ticket.id}\n"
        f"Type: {ticket.issue_type}\n"
        f"Status: {ticket.status}\n"
        f"Summary: {ticket.summary}\n"
        f"Description: {ticket.description}\n"
        f"Acceptance Criteria: {ticket.acceptance_criteria}\n"
    )

@mcp.tool()
def update_jira_ticket(ticket_id: str, plan: str) -> str:
    """Update a Jira ticket with the generated implementation plan."""
    from agents.planner_agent import PlannerOutput
    dummy_plan = PlannerOutput(ticket_id=ticket_id, summary="", steps=[], architecture_notes="", raw_plan=plan)
    jira = get_jira()
    try:
        # Instead of calling JiraTool which expects a structured plan, just use the raw plan string
        issue = jira._client.issue(ticket_id)
        description_body = f"h2. ScopeSentinel Implementation Plan\n\n{plan}"
        issue.update(fields={"description": description_body})
        return "Ticket updated successfully."
    except Exception as e:
        return f"Failed to update ticket: {e}"

@mcp.tool()
def prepare_git_branch(ticket_id: str) -> str:
    """Prepare a Git branch for the given ticket."""
    git = get_git()
    try:
        path = git.prepare_branch(ticket_id)
        return f"Branch prepared at {path}"
    except Exception as e:
        return f"Failed to prepare branch: {e}"

@mcp.tool()
def commit_and_push(ticket_id: str, summary: str) -> str:
    """Commit changes and push the branch."""
    git = get_git()
    try:
        res = git.commit_and_push(ticket_id, summary)
        return f"Pushed branch {res.branch_name} with commit {res.commit_sha}"
    except Exception as e:
        return f"Failed to commit and push: {e}"

@mcp.tool()
def create_pull_request(ticket_id: str, plan: str, branch_name: str) -> str:
    """Create a pull request on GitHub."""
    # We need a mock ticket object for gh.create_pr
    from tools.jira_tool import JiraTicket
    from agents.planner_agent import PlannerOutput
    
    ticket = JiraTicket(id=ticket_id, summary=f"PR for {ticket_id}", description="", issue_type="Task", status="Open", acceptance_criteria="")
    dummy_plan = PlannerOutput(ticket_id=ticket_id, summary="", steps=[], architecture_notes="", raw_plan=plan)
    
    gh = get_gh()
    try:
        pr = gh.create_pr(ticket, dummy_plan, branch_name)
        return f"PR created: {pr.pr_url}"
    except Exception as e:
        return f"Failed to create PR: {e}"

@mcp.tool()
async def index_repository(directory: str, repo_id: str) -> str:
    """Index a repository for semantic search."""
    from pathlib import Path
    try:
        await init_collection()
        await ingest_directory(Path(directory), repo_id)
        return f"Repository indexed: {repo_id}"
    except Exception as e:
        return f"Failed to index repository: {e}"

@mcp.tool()
async def search_index(query: str, repo_id: str = None) -> str:
    """Search the indexed codebase for relevant snippets."""
    return await search_codebase(query, repo_id)

if __name__ == "__main__":
    mcp.run()
