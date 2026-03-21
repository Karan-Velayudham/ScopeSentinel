"""
HITLGateway: Human-in-the-Loop approval gate for ScopeSentinel.

Presents the Planner Agent's output to the user in the terminal and
awaits an Approve / Reject / Modify decision before proceeding.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Literal

from agents.planner_agent import PlannerOutput

logger = logging.getLogger(__name__)

DIVIDER = "=" * 60
THIN    = "-" * 60


@dataclass
class HITLDecision:
    """The outcome of a human review gate."""
    action: Literal["approve", "reject", "modify"]
    feedback: str = ""  # Only populated when action == "modify"


def _print_plan(plan: PlannerOutput) -> None:
    """Pretty-print a PlannerOutput to the terminal for human review."""
    print(f"\n{DIVIDER}")
    print(f"  🔍 PLAN REVIEW — {plan.ticket_id}")
    print(f"  Summary: {plan.summary}")
    print(THIN)

    if plan.architecture_notes:
        print("  📐 Architecture Notes:")
        for line in plan.architecture_notes.splitlines():
            print(f"     {line}")
        print()

    print("  📋 Implementation Steps:")
    if plan.steps:
        for i, step in enumerate(plan.steps, start=1):
            print(f"     {i}. {step}")
    else:
        print("     (no steps parsed — see raw plan below)")
        print(plan.raw_plan)

    print(DIVIDER)


def _prompt_decision() -> HITLDecision:
    """
    Synchronously prompt the user for an Approve / Reject / Modify decision.
    Loops until a valid input is provided.
    """
    while True:
        print("\n  What would you like to do with this plan?")
        print("    [A] Approve  — proceed to code generation")
        print("    [R] Reject   — abort this ticket")
        print("    [M] Modify   — request a revised plan with feedback")
        raw = input("\n  Your choice (A/R/M): ").strip().lower()

        if raw in ("a", "approve"):
            print("\n  ✅ Plan approved. Proceeding...\n")
            return HITLDecision(action="approve")

        elif raw in ("r", "reject"):
            print("\n  ❌ Plan rejected. Aborting workflow.\n")
            return HITLDecision(action="reject")

        elif raw in ("m", "modify"):
            feedback = input("\n  Enter your feedback for the planner:\n  > ").strip()
            if not feedback:
                print("  ⚠️  Feedback cannot be empty. Please try again.")
                continue
            print(f"\n  🔄 Sending feedback to planner: \"{feedback}\"\n")
            return HITLDecision(action="modify", feedback=feedback)

        else:
            print("  ⚠️  Invalid input. Please enter A, R, or M.")


class HITLGateway:
    """
    Presents a generated plan to a human operator and collects their decision.

    Runs the blocking prompt in a thread executor so it plays well with
    the top-level asyncio event loop.
    """

    async def present_and_await(self, plan: PlannerOutput) -> HITLDecision:
        """
        Display the plan and await a human decision asynchronously.

        Args:
            plan: The PlannerOutput produced by PlannerAgent.

        Returns:
            A HITLDecision with action and optional feedback.
        """
        _print_plan(plan)
        loop = asyncio.get_event_loop()
        # Run the blocking input() call in a thread so async loop stays healthy
        decision = await loop.run_in_executor(None, _prompt_decision)
        logger.info(f"HITL decision: {decision.action!r}" +
                    (f" — feedback: '{decision.feedback}'" if decision.feedback else ""))
        return decision
