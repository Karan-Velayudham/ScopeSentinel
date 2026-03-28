"""
PlannerAgent: Analyzes a Jira ticket and produces a step-by-step implementation plan.

Uses the OpenAI model to break down the ticket's summary, description,
and acceptance criteria into an actionable development plan with architectural notes.
"""

import re
from dataclasses import dataclass
from typing import Any, Callable, List, Optional

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
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


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
- **NEW**: You have access to a `search_index` tool. Use it to find relevant code snippets in the codebase to make your plan more accurate and detailed.
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

    def __init__(
        self,
        model: OpenAIChatModel,
        system_prompt: str = None,
        tool_definitions: Optional[List[dict]] = None,
    ):
        self.model = model
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.tool_definitions = tool_definitions or []

    async def plan(
        self,
        ticket_id: str,
        tool_registry: dict[str, Callable[..., Any]],
    ) -> PlannerOutput:
        """
        Generate an implementation plan for the given Jira ticket.
        If tool_definitions were provided, the LLM can call them directly
        to gather additional context before writing the plan.
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
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": _build_user_message(ticket_content)},
        ]

        # Agentic loop — keep going until the LLM doesn't request a tool call
        max_iterations = 5
        for _ in range(max_iterations):
            try:
                kwargs = {}
                if self.tool_definitions:
                    kwargs["tools"] = self.tool_definitions
                    kwargs["tool_choice"] = "auto"
                response = await self.model(messages, **kwargs)
            except Exception as exc:
                raise LLMResponseError(f"LLM call failed in PlannerAgent.plan: {exc}") from exc

            # Check if the LLM wants to call a tool
            tool_calls = getattr(response, "tool_calls", None)
            if not tool_calls:
                # No tool call — the LLM gave a final answer
                break

            # Dispatch each tool call and feed results back into messages
            messages.append({"role": "assistant", "tool_calls": tool_calls})
            for tc in tool_calls:
                fn_name = tc.function.name
                import json as _json
                fn_args = _json.loads(tc.function.arguments or "{}")
                log.info("planner.tool_call", tool=fn_name, args=fn_args)
                try:
                    callable_fn = tool_registry.get(fn_name)
                    if callable_fn:
                        tool_result = await callable_fn(**fn_args)
                        result_str = str(tool_result)
                    else:
                        result_str = f"Tool '{fn_name}' not found in registry."
                except Exception as te:
                    result_str = f"Error calling '{fn_name}': {te}"
                    log.warning("planner.tool_call_failed", tool=fn_name, error=str(te))

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                })

        # Extract usage from AgentScope response
        it = response.usage.get("input_tokens", 0) if response.usage else 0
        ot = response.usage.get("output_tokens", 0) if response.usage else 0

        raw_plan = _extract_text(response)
        steps, architecture_notes = _parse_plan(raw_plan)
        log.info("planner.plan_ready", num_steps=len(steps), tokens=it + ot)

        return PlannerOutput(
            ticket_id=ticket_id,
            summary="Fetched via MCP",
            steps=steps,
            architecture_notes=architecture_notes,
            raw_plan=raw_plan,
            prompt_tokens=it,
            completion_tokens=ot,
            total_tokens=it + ot,
        )

    async def replan(
        self,
        ticket_id: str,
        tool_registry: dict[str, Callable[..., Any]],
        tool_definitions: Optional[List[dict]],
        feedback: str,
        previous_plan: PlannerOutput,
    ) -> PlannerOutput:
        """Generate a revised plan based on human feedback."""
        log = logger.bind(ticket_id=ticket_id, step="planner.replan")
        log.info("planner.replanning", feedback_len=len(feedback))

        try:
            fetch_func = tool_registry["fetch_jira_ticket"]
            res = await fetch_func(ticket_id=ticket_id)
            ticket_content = res.content[0]["text"] if hasattr(res, "content") else str(res)
        except Exception as exc:
            raise MCPToolCallError(f"fetch_jira_ticket failed during replan: {exc}") from exc

        messages = [
            {"role": "system", "content": self.system_prompt},
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
            active_tools = tool_definitions or self.tool_definitions
            kwargs = {"tools": active_tools, "tool_choice": "auto"} if active_tools else {}
            response = await self.model(messages, **kwargs)
        except Exception as exc:
            raise LLMResponseError(f"LLM call failed in PlannerAgent.replan: {exc}") from exc

        # Extract usage
        it = response.usage.get("input_tokens", 0) if response.usage else 0
        ot = response.usage.get("output_tokens", 0) if response.usage else 0

        raw_plan = _extract_text(response)
        steps, architecture_notes = _parse_plan(raw_plan)
        log.info("planner.replan_ready", num_steps=len(steps), tokens=it + ot)

        return PlannerOutput(
            ticket_id=ticket_id,
            summary="Fetched via MCP",
            steps=steps,
            architecture_notes=architecture_notes,
            raw_plan=raw_plan,
            prompt_tokens=it,
            completion_tokens=ot,
            total_tokens=it + ot,
        )
