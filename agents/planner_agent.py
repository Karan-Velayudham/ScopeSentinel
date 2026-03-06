"""
PlannerAgent: Analyzes a Jira ticket and produces a step-by-step implementation plan.

Uses the OpenAI model to break down the ticket's summary, description,
and acceptance criteria into an actionable development plan with architectural notes.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field

from agentscope.model import OpenAIChatModel
from agentscope.mcp import StdIOStatefulClient

logger = logging.getLogger(__name__)


@dataclass
class PlannerOutput:
    """Structured output from the Planner Agent."""
    ticket_id: str
    summary: str                   # Original ticket summary
    steps: list[str]               # Individual implementation steps
    architecture_notes: str        # High-level design / architectural notes
    raw_plan: str                  # Full LLM response for audit/reference


SYSTEM_PROMPT = """\
You are an expert senior software engineer acting as a technical planner for ScopeSentinel, \
an autonomous software delivery platform.

Your job is to analyze a Jira ticket and produce a clear, concrete, step-by-step implementation plan.

Format your response EXACTLY as follows:

## Architecture Notes
<1-3 sentences on the high-level approach, patterns, or design decisions>

## Implementation Steps
1. <First concrete step>
2. <Second concrete step>
3. <Continue numbering...>

Rules:
- Steps must be specific enough for an AI coding agent to act on (not vague like "implement feature").
- Include file paths, function names, or component names where relevant.
- Do not include steps outside of software implementation (e.g. no "discuss with team").
- If acceptance criteria are provided, map them to specific steps.
"""


def _build_user_message(ticket_content: str) -> str:
    return f"**Here is the Jira Ticket fetched via MCP Tools:**\n\n{ticket_content}"

def _parse_plan(raw: str) -> tuple[list[str], str]:
    """
    Parse the LLM response into (steps, architecture_notes).
    Returns a tuple of (list of step strings, architecture notes string).
    """
    steps: list[str] = []
    architecture_notes = ""

    # Extract architecture notes section
    arch_match = re.search(
        r"##\s*Architecture Notes\s*\n(.*?)(?=##|\Z)",
        raw, re.DOTALL | re.IGNORECASE
    )
    if arch_match:
        architecture_notes = arch_match.group(1).strip()

    # Extract numbered steps
    steps_match = re.search(
        r"##\s*Implementation Steps\s*\n(.*?)(?=##|\Z)",
        raw, re.DOTALL | re.IGNORECASE
    )
    if steps_match:
        steps_block = steps_match.group(1).strip()
        for line in steps_block.splitlines():
            # Match lines like "1. Do something" or "  2. Do another thing"
            m = re.match(r"^\s*\d+\.\s+(.+)$", line)
            if m:
                steps.append(m.group(1).strip())

    return steps, architecture_notes


class PlannerAgent:
    """
    An agent that analyzes a JiraTicket and produces a PlannerOutput
    using an LLM to break down the work into concrete implementation steps.
    """

    def __init__(self, model: OpenAIChatModel):
        self.model = model

    async def plan(self, ticket_id: str, mcp_client: StdIOStatefulClient) -> PlannerOutput:
        """
        Generate an implementation plan for the given Jira ticket.

        Args:
            ticket_id: The ID of the Jira ticket.
            mcp_client: The MCP client to fetch ticket context with.

        Returns:
            A PlannerOutput with parsed steps and architecture notes.
        """
        logger.info(f"PlannerAgent: fetching and planning {ticket_id}")

        # Use MCP to fetch the ticket
        fetch_func = await mcp_client.get_callable_function("fetch_jira_ticket")
        res = await fetch_func(ticket_id=ticket_id)
        if hasattr(res, 'content'): # Handle AgentScope ToolResponse
            ticket_content = res.content[0]['text']
        else:
            ticket_content = str(res)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_message(ticket_content)},
        ]

        response = await self.model(messages)

        # Extract text from ChatResponse
        raw_plan = ""
        if hasattr(response, "content") and isinstance(response.content, list):
            for block in response.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    raw_plan = block["text"]
                    break
        if not raw_plan:
            raw_plan = str(response)

        steps, architecture_notes = _parse_plan(raw_plan)

        logger.info(f"PlannerAgent: produced {len(steps)} implementation steps.")

        return PlannerOutput(
            ticket_id=ticket_id,
            summary="Fetched via MCP",
            steps=steps,
            architecture_notes=architecture_notes,
            raw_plan=raw_plan,
        )

    async def replan(
        self,
        ticket_id: str,
        mcp_client: StdIOStatefulClient,
        feedback: str,
        previous_plan: PlannerOutput,
    ) -> PlannerOutput:
        """
        Generate a revised plan based on human feedback.

        Args:
            ticket_id:     The ID of the Jira ticket.
            mcp_client:    The MCP client to fetch ticket context with.
            feedback:      The reviewer's feedback string.
            previous_plan: The PlannerOutput that was rejected.

        Returns:
            A new PlannerOutput incorporating the feedback.
        """
        logger.info(f"PlannerAgent: replanning {ticket_id} with feedback: '{feedback}'")

        # Use MCP to fetch the ticket
        fetch_func = await mcp_client.get_callable_function("fetch_jira_ticket")
        res = await fetch_func(ticket_id=ticket_id)
        if hasattr(res, 'content'):
            ticket_content = res.content[0]['text']
        else:
            ticket_content = str(res)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_message(ticket_content)},
            {"role": "assistant", "content": previous_plan.raw_plan},
            {
                "role": "user",
                "content": (
                    f"The plan above was reviewed by a human. Their feedback is:\n\n"
                    f"\"{feedback}\"\n\n"
                    f"Please revise the plan to address this feedback. "
                    f"Keep the same output format."
                ),
            },
        ]

        response = await self.model(messages)

        raw_plan = ""
        if hasattr(response, "content") and isinstance(response.content, list):
            for block in response.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    raw_plan = block["text"]
                    break
        if not raw_plan:
            raw_plan = str(response)

        steps, architecture_notes = _parse_plan(raw_plan)
        logger.info(f"PlannerAgent: revised plan has {len(steps)} steps.")

        return PlannerOutput(
            ticket_id=ticket_id,
            summary="Fetched via MCP",
            steps=steps,
            architecture_notes=architecture_notes,
            raw_plan=raw_plan,
        )
