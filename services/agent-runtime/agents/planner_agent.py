"""
PlannerAgent: Analyzes a Jira ticket and produces a step-by-step implementation plan.

Uses the OpenAI model to break down the ticket's summary, description,
and acceptance criteria into an actionable development plan with architectural notes.
"""

import re
from dataclasses import dataclass
from typing import Any, Callable

import structlog
from agentscope.model import OpenAIChatModel

from exceptions import LLMResponseError, MCPToolCallError

logger = structlog.get_logger(__name__)


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


def _extract_text(response: Any) -> str:
    """Extract a plain-text string from an AgentScope model response."""
    if hasattr(response, "content") and isinstance(response.content, list):
        for block in response.content:
            if isinstance(block, dict) and block.get("type") == "text":
                return block["text"]
    return str(response)

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
    An agent that analyzes a Jira ticket and produces a PlannerOutput
    using an LLM to break down the work into concrete implementation steps.

    Accepts a ``tool_registry`` — a flat dict of ``{tool_name: async callable}``
    supplied by ``mcp_pool.load_client_pool()``.  This makes the agent
    agnostic to which MCP server provides each tool.
    """

    def __init__(self, model: OpenAIChatModel):
        self.model = model

    async def plan(
        self,
        ticket_id: str,
        tool_registry: dict[str, Callable[..., Any]],
    ) -> PlannerOutput:
        """
        Generate an implementation plan for the given Jira ticket.

        Args:
            ticket_id:     The ID of the Jira ticket.
            tool_registry: Flat dict of MCP tool callables from the pool.

        Returns:
            A PlannerOutput with parsed steps and architecture notes.

        Raises:
            MCPToolCallError: if fetching the Jira ticket fails.
            LLMResponseError: if the LLM call fails or returns unparseable output.
        """
        log = logger.bind(ticket_id=ticket_id, step="planner.plan")
        log.info("planner.fetching_ticket")

        try:
            fetch_func = tool_registry["fetch_jira_ticket"]
            res = await fetch_func(ticket_id=ticket_id)
            ticket_content = res.content[0]["text"] if hasattr(res, "content") else str(res)
        except Exception as exc:
            raise MCPToolCallError(f"fetch_jira_ticket failed: {exc}") from exc

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_message(ticket_content)},
        ]

        try:
            response = await self.model(messages)
        except Exception as exc:
            raise LLMResponseError(f"LLM call failed in PlannerAgent.plan: {exc}") from exc

        raw_plan = _extract_text(response)
        steps, architecture_notes = _parse_plan(raw_plan)
        log.info("planner.plan_ready", num_steps=len(steps))

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
        tool_registry: dict[str, Callable[..., Any]],
        feedback: str,
        previous_plan: PlannerOutput,
    ) -> PlannerOutput:
        """
        Generate a revised plan based on human feedback.

        Args:
            ticket_id:     The ID of the Jira ticket.
            tool_registry: Flat dict of MCP tool callables from the pool.
            feedback:      The reviewer's feedback string.
            previous_plan: The PlannerOutput that was rejected.

        Returns:
            A new PlannerOutput incorporating the feedback.

        Raises:
            MCPToolCallError: if fetching the Jira ticket fails.
            LLMResponseError: if the LLM call fails or returns unparseable output.
        """
        log = logger.bind(ticket_id=ticket_id, step="planner.replan")
        log.info("planner.replanning", feedback_len=len(feedback))

        try:
            fetch_func = tool_registry["fetch_jira_ticket"]
            res = await fetch_func(ticket_id=ticket_id)
            ticket_content = res.content[0]["text"] if hasattr(res, "content") else str(res)
        except Exception as exc:
            raise MCPToolCallError(f"fetch_jira_ticket failed during replan: {exc}") from exc

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

        try:
            response = await self.model(messages)
        except Exception as exc:
            raise LLMResponseError(f"LLM call failed in PlannerAgent.replan: {exc}") from exc

        raw_plan = _extract_text(response)
        steps, architecture_notes = _parse_plan(raw_plan)
        log.info("planner.replan_ready", num_steps=len(steps))

        return PlannerOutput(
            ticket_id=ticket_id,
            summary="Fetched via MCP",
            steps=steps,
            architecture_notes=architecture_notes,
            raw_plan=raw_plan,
        )
