"""
AnalyzerAgent: Performs post-implementation code quality and security audits.
"""

import re
from dataclasses import dataclass
from typing import Any, List
from pathlib import Path

import structlog
from agentscope.model import OpenAIChatModel
from agents.planner_agent import PlannerOutput, _extract_text
from exceptions import LLMResponseError

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """\
You are an expert security researcher and staff software engineer at ScopeSentinel.
Your job is to audit the code changes implemented by an AI Coding Agent.

You will be given:
1. The original Jira ticket.
2. The approved implementation plan.
3. The actual code changes made.

Your task is to provide a final "Pass/Fail" decision and detailed feedback.

Look for:
- Security vulnerabilities (hardcoded keys, injection, etc.).
- Performance bottlenecks.
- Adherence to the implementation plan.
- General code quality (naming, structure, comments).

Output format:
DECISION: [PASS/FAIL]
FEEDBACK:
- <Point 1>
- <Point 2>
"""

@dataclass
class AnalyzerOutput:
    """Result of an AnalyzerAgent audit."""
    passed: bool
    feedback: str
    raw_response: str
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

class AnalyzerAgent:
    """
    An agent that reviews generated code against the plan and ticket.
    """

    def __init__(self, model: OpenAIChatModel):
        self.model = model

    async def analyze(
        self,
        ticket_id: str,
        ticket_content: str,
        plan: PlannerOutput,
        files_written: List[str],
        workspace_path: str
    ) -> AnalyzerOutput:
        log = logger.bind(ticket_id=ticket_id, step="analyzer.analyze")
        
        # Read file contents for context
        code_context = []
        workspace = Path(workspace_path)
        for rel_path in files_written:
            fpath = workspace / rel_path
            if fpath.exists() and fpath.is_file():
                try:
                    content = fpath.read_text(encoding="utf-8")
                    code_context.append(f"### `{rel_path}`\n```\n{content}\n```")
                except Exception:
                    continue
        
        prompt = (
            f"**Ticket:** {ticket_id}\n"
            f"**Ticket Content:**\n{ticket_content}\n\n"
            f"**Approved Plan:**\n{plan.raw_plan}\n\n"
            "**Implementation Results:**\n" + "\n".join(code_context)
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        log.info("analyzer.reviewing_code", num_files=len(files_written))
        try:
            response = await self.model(messages)
        except Exception as exc:
            raise LLMResponseError(f"LLM call failed in AnalyzerAgent.analyze: {exc}") from exc

        raw = _extract_text(response)
        
        # Extract usage
        it = response.usage.get("input_tokens", 0) if response.usage else 0
        ot = response.usage.get("output_tokens", 0) if response.usage else 0
        
        passed = "DECISION: PASS" in raw.upper()
        
        feedback_match = re.search(r"FEEDBACK:\n?(.*)", raw, re.DOTALL | re.IGNORECASE)
        feedback = feedback_match.group(1).strip() if feedback_match else "No specific feedback provided."

        return AnalyzerOutput(
            passed=passed,
            feedback=feedback,
            raw_response=raw,
            prompt_tokens=it,
            completion_tokens=ot,
            total_tokens=it + ot
        )
