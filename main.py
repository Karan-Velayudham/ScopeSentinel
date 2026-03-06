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
from agentscope.mcp import StdIOStatefulClient

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

    # --- Step 1: Start MCP Client ---
    logger.info("Starting MCP Client connecting to tools...")
    mcp_client = StdIOStatefulClient("tools_mcp", command="python", args=["tools/mcp_server.py"])
    await mcp_client.connect()

    # --- Step 2: Fetch ticket for display (Agent will also fetch internally) ---
    fetch_func = await mcp_client.get_callable_function("fetch_jira_ticket")
    res = await fetch_func(ticket_id=ticket_id)
    if hasattr(res, 'content'):
        ticket_content = res.content[0]['text']
    else:
        ticket_content = str(res)

    print("\n" + "=" * 60)
    print(f"  Ticket Context Snapshot:\n{ticket_content}")
    print("=" * 60)

    # --- Step 3: Generate plan ---
    planner = PlannerAgent(model=model)
    hitl = HITLGateway()

    plan = await planner.plan(ticket_id, mcp_client)

    # --- Step 4: HITL approval loop (Story 3.2) ---
    for revision in range(MAX_REVISIONS + 1):
        decision = await hitl.present_and_await(plan)

        if decision.action == "approve":
            print(f"  ✅ Plan approved after {revision} revision(s). Updating Jira ticket...")
            try:
                update_func = await mcp_client.get_callable_function("update_jira_ticket")
                update_res = await update_func(ticket_id=ticket_id, plan=plan.raw_plan)
                print(f"  📝 Jira ticket {ticket_id} updated: {update_res}")
            except Exception as e:
                logger.warning(f"Could not update Jira ticket via MCP: {e}")
                print(f"  ⚠️  Could not update Jira ticket: {e}")

            # --- Step 5: Code Generation, Validation, and PR Creation via Coder Agent ---
            print("\n  🤖 Handing off to Coder Agent (Code + Validate + PR)...\n")
            coder = CoderAgent(model=model)
            result = await coder.code_with_validation(
                ticket_id=ticket_id,
                ticket_content=ticket_content,
                plan=plan,
                mcp_client=mcp_client
            )

            if result.files_written:
                print(f"\n  📁 Code written to: {result.workspace_path}")
                print(f"  Files ({len(result.files_written)}):")
                for f in result.files_written:
                    print(f"    • {f}")
            else:
                print("  ⚠️  Coder Agent produced no files.")
                logger.debug(result.raw_response)
                
            print("\n  🎉 Workflow Complete. Agent has handled Git pushing and PR creation via MCP.")
            await mcp_client.close()
            return

        elif decision.action == "reject":
            print(f"  ❌ Workflow aborted by reviewer for ticket {ticket_id}.")
            await mcp_client.close()
            return

        elif decision.action == "modify":
            if revision >= MAX_REVISIONS:
                print(f"\n  ⚠️  Maximum revisions ({MAX_REVISIONS}) reached. Aborting.")
                await mcp_client.close()
                return
            plan = await planner.replan(ticket_id, mcp_client, decision.feedback, plan)



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
