"""
ScopeSentinel — Main Orchestrator

Runs the end-to-end prototype workflow:
  1. Fetch a Jira ticket (JiraTool)
  2. Generate an implementation plan (PlannerAgent)

Usage:
  python main.py --ticket SCRUM-6
  python main.py  # runs a quick AgentScope health-check (no Jira needed)
"""

import os
import asyncio
import argparse
import logging

from dotenv import load_dotenv
import agentscope
from agentscope.model import OpenAIChatModel

from tools.jira_tool import JiraTool
from agents.planner_agent import PlannerAgent

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _build_model() -> OpenAIChatModel:
    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set in your .env file.")
    return OpenAIChatModel(
        model_name="gpt-4o",
        api_key=api_key,
        stream=False,
    )


async def run_planner_workflow(ticket_id: str) -> None:
    """Full Epic 2 workflow: fetch Jira ticket → generate plan."""
    logger.info("Initializing AgentScope...")
    agentscope.init(project="ScopeSentinel", name="PlannerRun")

    model = _build_model()
    logger.info("Model initialized.")

    # --- Step 1: Fetch ticket ---
    jira = JiraTool()
    ticket = jira.fetch_ticket(ticket_id)

    print("\n" + "=" * 60)
    print(f"  Ticket  : {ticket.id}  [{ticket.issue_type}]  — {ticket.status}")
    print(f"  Summary : {ticket.summary}")
    if ticket.acceptance_criteria:
        print(f"  AC      : {ticket.acceptance_criteria[:120]}{'…' if len(ticket.acceptance_criteria) > 120 else ''}")
    print("=" * 60)

    # --- Step 2: Generate plan ---
    planner = PlannerAgent(model=model)
    plan = await planner.plan(ticket)

    print("\n📐 Architecture Notes")
    print(f"  {plan.architecture_notes or '(none)'}\n")

    print("📋 Implementation Steps")
    for i, step in enumerate(plan.steps, start=1):
        print(f"  {i}. {step}")

    if not plan.steps:
        print("  (No steps parsed — raw plan below)")
        print(plan.raw_plan)

    print()


async def run_healthcheck() -> None:
    """Quick smoke-test: verify AgentScope + OpenAI are wired correctly."""
    logger.info("Running health check (no Jira ticket provided)...")
    agentscope.init(project="ScopeSentinel", name="HealthCheck")
    model = _build_model()

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Respond with exactly: 'ScopeSentinel is ready.'"},
    ]
    response = await model(messages)
    text = ""
    if hasattr(response, "content") and isinstance(response.content, list):
        for block in response.content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block["text"]
                break
    print(f"\n✅ Health check passed: {text.strip()}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ScopeSentinel Orchestrator")
    parser.add_argument("--ticket", help="Jira ticket ID to plan (e.g. SCRUM-6)", default=None)
    args = parser.parse_args()

    if args.ticket:
        asyncio.run(run_planner_workflow(args.ticket))
    else:
        asyncio.run(run_healthcheck())
