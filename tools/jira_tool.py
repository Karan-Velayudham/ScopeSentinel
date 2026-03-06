"""
JiraTool: Fetches Jira ticket details for ScopeSentinel.

Reads credentials from environment variables:
  - JIRA_URL:        Base URL of your Jira instance (e.g. https://your-org.atlassian.net)
  - JIRA_USERNAME:   Jira account email
  - JIRA_API_TOKEN:  Jira API token (create at https://id.atlassian.com/manage-profile/security/api-tokens)
"""

import os
import logging
import argparse
from dataclasses import dataclass

from dotenv import load_dotenv
from jira import JIRA, JIRAError

logger = logging.getLogger(__name__)


@dataclass
class JiraTicket:
    """Structured representation of a Jira ticket."""
    id: str
    summary: str
    description: str
    acceptance_criteria: str
    status: str
    issue_type: str


class JiraTool:
    """
    A tool to fetch Jira ticket information.
    Authenticates using JIRA_URL, JIRA_USERNAME, and JIRA_API_TOKEN env vars.
    """

    # Common custom field names for acceptance criteria (varies by Jira config)
    ACCEPTANCE_CRITERIA_FIELDS = [
        "customfield_10016",  # common in many Jira setups
        "customfield_10020",
        "customfield_10034",
    ]
    ACCEPTANCE_CRITERIA_LABEL = "acceptance criteria"

    def __init__(self):
        load_dotenv()

        jira_url = os.environ.get("JIRA_URL")
        username = os.environ.get("JIRA_USERNAME")
        api_token = os.environ.get("JIRA_API_TOKEN")

        if not all([jira_url, username, api_token]):
            raise EnvironmentError(
                "Missing required Jira credentials. Please set JIRA_URL, "
                "JIRA_USERNAME, and JIRA_API_TOKEN in your .env file."
            )

        self._client = JIRA(
            server=jira_url,
            basic_auth=(username, api_token)
        )
        logger.info(f"JiraTool connected to: {jira_url}")

    def fetch_ticket(self, ticket_id: str) -> JiraTicket:
        """
        Fetch a Jira ticket's details by its ID.

        Args:
            ticket_id: The Jira ticket ID (e.g. "PROJ-123").

        Returns:
            A JiraTicket dataclass with the ticket's structured data.

        Raises:
            ValueError: If the ticket is not found or access is denied.
        """
        try:
            issue = self._client.issue(ticket_id)
        except JIRAError as e:
            if e.status_code == 404:
                raise ValueError(f"Ticket '{ticket_id}' not found in Jira.") from e
            elif e.status_code == 403:
                raise ValueError(f"Access denied to ticket '{ticket_id}'. Check your credentials.") from e
            else:
                raise ValueError(f"Jira API error for ticket '{ticket_id}': {e.text}") from e

        fields = issue.fields
        raw_description = getattr(fields, "description", "") or ""

        # Try to extract acceptance criteria from known custom fields
        acceptance_criteria = ""
        for field_name in self.ACCEPTANCE_CRITERIA_FIELDS:
            value = getattr(fields, field_name, None)
            if value:
                acceptance_criteria = str(value)
                logger.info(f"Found acceptance criteria in field: {field_name}")
                break

        # Fallback: look for an 'Acceptance Criteria' section in the description
        if not acceptance_criteria:
            acceptance_criteria = self._extract_ac_from_description(raw_description)

        return JiraTicket(
            id=ticket_id,
            summary=getattr(fields, "summary", ""),
            description=raw_description,
            acceptance_criteria=acceptance_criteria,
            status=str(fields.status),
            issue_type=str(fields.issuetype),
        )

    def _extract_ac_from_description(self, description: str) -> str:
        """
        Attempt to extract an Acceptance Criteria section from the
        description text by looking for a heading containing 'acceptance criteria'.
        """
        if not description:
            return ""

        lines = description.splitlines()
        ac_lines = []
        in_ac_section = False

        for line in lines:
            lower = line.lower().strip()
            # Detect an 'Acceptance Criteria' heading (handles Jira markup like h3. or **)
            if self.ACCEPTANCE_CRITERIA_LABEL in lower and not in_ac_section:
                in_ac_section = True
                continue
            # Stop at the next heading
            if in_ac_section and any(
                lower.startswith(marker) for marker in ["h1.", "h2.", "h3.", "h4.", "##", "#"]
            ):
                break
            if in_ac_section:
                ac_lines.append(line)

        return "\n".join(ac_lines).strip()


# --- CLI for quick manual testing ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Fetch a Jira ticket for ScopeSentinel.")
    parser.add_argument("--ticket", required=True, help="The Jira ticket ID (e.g. PROJ-123)")
    args = parser.parse_args()

    tool = JiraTool()
    ticket = tool.fetch_ticket(args.ticket)

    print("\n" + "=" * 60)
    print(f"  Ticket     : {ticket.id}")
    print(f"  Type       : {ticket.issue_type}")
    print(f"  Status     : {ticket.status}")
    print(f"  Summary    : {ticket.summary}")
    print("-" * 60)
    print("  Description:")
    print(ticket.description or "  (none)")
    print("-" * 60)
    print("  Acceptance Criteria:")
    print(ticket.acceptance_criteria or "  (not found)")
    print("=" * 60 + "\n")
