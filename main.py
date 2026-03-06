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
from tools.git_tool import GitTool
from tools.github_tool import GithubTool
from agents.planner_agent import PlannerAgent
from agents.coder_agent import CoderAgent
from hitl.hitl_gateway import HITLGateway

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


MAX_REVISIONS = 3


async def run_planner_workflow(ticket_id: str) -> None:
    """Full Epic 2+3 workflow: fetch Jira ticket → generate plan → HITL gate."""
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
        print(f"  AC      : {ticket.acceptance_criteria[:120]}"
              f"{'…' if len(ticket.acceptance_criteria) > 120 else ''}")
    print("=" * 60)

    # --- Step 2: Generate plan ---
    planner = PlannerAgent(model=model)
    hitl = HITLGateway()

    plan = await planner.plan(ticket)

    # --- Step 3: HITL approval loop (Story 3.2) ---
    for revision in range(MAX_REVISIONS + 1):
        decision = await hitl.present_and_await(plan)

        if decision.action == "approve":
            print(f"  ✅ Plan approved after {revision} revision(s). Updating Jira ticket...")
            try:
                jira.update_ticket_with_plan(ticket_id, plan)
                print(f"  📝 Jira ticket {ticket_id} updated with the approved plan.")
            except ValueError as e:
                logger.warning(f"Could not update Jira ticket: {e}")
                print(f"  ⚠️  Could not update Jira ticket: {e}")

            # --- Step 4a: Prepare git branch (local repo IS the workspace) ---
            git = None
            workspace_path = None
            try:
                git = GitTool()
                workspace_path = git.prepare_branch(ticket_id)
                print(f"\n  🌿 Branch 'sentinel/{ticket_id}' ready in '{workspace_path}'")
            except (EnvironmentError, Exception) as e:
                logger.warning(f"Git setup skipped: {e}")
                print(f"  ⚠️  Git setup skipped (will use local workspace): {e}")

            # --- Step 4b: Code Generation + Sandbox Validation (Epic 4.1–4.3) ---
            print("\n  🤖 Handing off to Coder Agent...\n")
            coder = CoderAgent(model=model)
            result = await coder.code_with_validation(
                ticket, plan,
                workspace_override=workspace_path,   # write into repo dir if available
            )

            if result.files_written:
                print(f"\n  📁 Code written to: {result.workspace_path}")
                print(f"  Files ({len(result.files_written)}):")
                for f in result.files_written:
                    print(f"    • {f}")
            else:
                print("  ⚠️  Coder Agent produced no files.")
                logger.debug(result.raw_response)

            # --- Step 5: Commit + push + PR (Epic 5) ---
            git_result = None
            if git:
                print("\n  🌿 Committing and pushing...")
                try:
                    git_result = git.commit_and_push(ticket_id, ticket.summary)
                    print(f"  ✅ Branch pushed: {git_result.branch_name}")
                    print(f"     Commit: {git_result.commit_sha[:8]}")
                except Exception as e:
                    logger.warning(f"Git push failed: {e}")
                    print(f"  ⚠️  Git push failed: {e}")

            if git_result:
                print("\n  🔀 Opening Pull Request...")
                try:
                    gh = GithubTool()
                    pr = gh.create_pr(
                        ticket=ticket,
                        plan=plan,
                        branch_name=git_result.branch_name,
                    )
                    print(f"  🎉 PR #{pr.pr_number} opened: {pr.pr_url}")
                except Exception as e:
                    logger.warning(f"PR creation skipped: {e}")
                    print(f"  ⚠️  PR creation skipped: {e}")

            return

        elif decision.action == "reject":
            print(f"  ❌ Workflow aborted by reviewer for ticket {ticket_id}.")
            return

        elif decision.action == "modify":
            if revision >= MAX_REVISIONS:
                print(f"\n  ⚠️  Maximum revisions ({MAX_REVISIONS}) reached. Aborting.")
                return
            plan = await planner.replan(ticket, decision.feedback, plan)


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
