"""
ScopeSentinel — Main Orchestrator

Runs the end-to-end prototype workflow:
  1. Load MCP client pool from mcp_servers.yaml
  2. Fetch a Jira ticket
  3. Generate an implementation plan (PlannerAgent)
  4. HITL approval gate
  5. Code generation + sandbox validation (CoderAgent)      [skipped in dry-run]
  6. Commit, push, and create PR                            [skipped in dry-run]

Usage:
  python main.py --ticket SCRUM-6
  python main.py --ticket SCRUM-6 --dry-run   # plan + HITL only, no code/git
  python main.py                               # runs a quick AgentScope health-check
"""

import os
import sys
import uuid
import asyncio
import argparse

import structlog
from dotenv import load_dotenv
import agentscope
from agentscope.model import OpenAIChatModel

from tools.remote_registry import build_remote_tool_registry
from agents.planner_agent import PlannerAgent
from agents.coder_agent import CoderAgent
from hitl.hitl_gateway import HITLGateway
from exceptions import (
    ScopeSentinelError,
    MCPConnectionError,
    MCPToolCallError,
    LLMTimeoutError,
    LLMResponseError,
    DockerUnavailableError,
    ConfigurationError,
)

# ---------------------------------------------------------------------------
# Logging setup (0.1.2)
# ---------------------------------------------------------------------------

def _configure_logging() -> None:
    """Configure structlog for JSON (prod) or console (dev) output."""
    log_format = os.environ.get("LOG_FORMAT", "console").lower()

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            structlog.stdlib.NAME_TO_LEVEL.get(
                os.environ.get("LOG_LEVEL", "info"), structlog.stdlib.NAME_TO_LEVEL["info"]
            )
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


_configure_logging()
logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Model factory
# ---------------------------------------------------------------------------

def _build_model() -> OpenAIChatModel:
    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ConfigurationError("OPENAI_API_KEY is not set in your .env file.")
    return OpenAIChatModel(
        model_name="gpt-4o",
        api_key=api_key,
        stream=False,
    )


MAX_REVISIONS = 3

# ---------------------------------------------------------------------------
# Core workflows
# ---------------------------------------------------------------------------

async def run_planner_workflow(ticket_id: str, *, dry_run: bool = False, org_id: str = None) -> None:
    """Full workflow: fetch Jira ticket → generate plan → HITL gate → (code + PR)."""
    run_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(run_id=run_id, ticket_id=ticket_id)

    log = structlog.get_logger(__name__)
    log.info("workflow.start", dry_run=dry_run)

    try:
        agentscope.init(project="ScopeSentinel", name="PlannerRun")
        model = _build_model()
        log.info("model.ready")

        # Step 1: Start dynamic MCP client pool
        log.info("remote_registry.loading")
        try:
            tool_registry = await build_remote_tool_registry(org_id)
        except Exception as exc:
            raise MCPConnectionError(f"Failed to load remote tools: {exc}") from exc

        try:
            # Step 2: Fetch ticket
            log.info("step.fetch_ticket")
            try:
                fetch_func = tool_registry["fetch_jira_ticket"]
                res = await fetch_func(ticket_id=ticket_id)
                # Handle dict or string responses
                if isinstance(res, dict):
                    ticket_content = res.get("content", [{"text": str(res)}])[0]["text"]
                elif hasattr(res, "content"):
                    ticket_content = res.content[0]["text"]
                else:
                    ticket_content = str(res)
            except Exception as exc:
                raise MCPToolCallError(f"fetch_jira_ticket failed: {exc}") from exc

            print("\n" + "=" * 60)
            print(f"  Ticket Context Snapshot:\n{ticket_content}")
            print("=" * 60)

            # Step 3: Generate plan
            log.info("step.planner")
            planner = PlannerAgent(model=model)
            hitl = HITLGateway()

            try:
                plan = await planner.plan(ticket_id, tool_registry)
            except Exception as exc:
                raise LLMResponseError(f"PlannerAgent failed: {exc}") from exc

            # Step 4: HITL approval loop
            for revision in range(MAX_REVISIONS + 1):
                log.info("step.hitl", revision=revision)
                decision = await hitl.present_and_await(plan)

                if decision.action == "approve":
                    print(f"  ✅ Plan approved after {revision} revision(s). Updating Jira ticket...")
                    log.info("hitl.approved", revision=revision)

                    try:
                        update_func = tool_registry["update_jira_ticket"]
                        await update_func(ticket_id=ticket_id, plan=plan.raw_plan)
                        log.info("jira.ticket_updated")
                    except Exception as exc:
                        log.warning("jira.update_failed", error=str(exc))
                        print(f"  ⚠️  Could not update Jira ticket: {exc}")

                    # Step 5: Code generation (skipped in dry-run)
                    if dry_run:
                        log.info("dry_run.skip_coder")
                        print("\n  🌵 Dry-run mode: skipping code generation and git push.\n")
                        return

                    print("\n  🤖 Handing off to Coder Agent (Code + Validate + PR)...\n")
                    log.info("step.coder")
                    coder = CoderAgent(model=model)
                    try:
                        result = await coder.code_with_validation(
                            ticket_id=ticket_id,
                            ticket_content=ticket_content,
                            plan=plan,
                            tool_registry=tool_registry,
                        )
                    except Exception as exc:
                        raise LLMResponseError(f"CoderAgent failed: {exc}") from exc

                    if result.files_written:
                        print(f"\n  📁 Code written to: {result.workspace_path}")
                        print(f"  Files ({len(result.files_written)}):")
                        for f in result.files_written:
                            print(f"    • {f}")
                    else:
                        log.warning("coder.no_files_written")
                        print("  ⚠️  Coder Agent produced no files.")

                    log.info("workflow.complete")
                    print("\n  🎉 Workflow Complete. Agent has handled Git pushing and PR creation via MCP.")
                    return

                elif decision.action == "reject":
                    log.info("hitl.rejected")
                    print(f"  ❌ Workflow aborted by reviewer for ticket {ticket_id}.")
                    return

                elif decision.action == "modify":
                    if revision >= MAX_REVISIONS:
                        log.warning("hitl.max_revisions_reached", limit=MAX_REVISIONS)
                        print(f"\n  ⚠️  Maximum revisions ({MAX_REVISIONS}) reached. Aborting.")
                        return
                    log.info("hitl.replanning", revision=revision)
                    try:
                        plan = await planner.replan(ticket_id, tool_registry, decision.feedback, plan)
                    except Exception as exc:
                        raise LLMResponseError(f"Replanning failed: {exc}") from exc

        finally:
            log.info("workflow.finished")

    except ConfigurationError as exc:
        log.error("config.error", error=str(exc))
        print(f"\n  ❌ Configuration error: {exc}")
        sys.exit(1)
    except MCPConnectionError as exc:
        log.error("mcp.connection_error", error=str(exc))
        print(f"\n  ❌ MCP connection failed: {exc}")
        sys.exit(2)
    except MCPToolCallError as exc:
        log.error("mcp.tool_call_error", error=str(exc))
        print(f"\n  ❌ MCP tool call failed: {exc}")
        sys.exit(3)
    except (LLMTimeoutError, LLMResponseError) as exc:
        log.error("llm.error", error=str(exc))
        print(f"\n  ❌ LLM error: {exc}")
        sys.exit(4)
    except ScopeSentinelError as exc:
        log.error("runtime.error", error=str(exc))
        print(f"\n  ❌ Runtime error: {exc}")
        sys.exit(5)


async def run_healthcheck() -> None:
    """Quick smoke-test: verify AgentScope + OpenAI are wired correctly."""
    run_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(run_id=run_id)
    log = structlog.get_logger(__name__)
    log.info("healthcheck.start")

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
    log.info("healthcheck.passed", response=text.strip())
    print(f"\n✅ Health check passed: {text.strip()}\n")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ScopeSentinel Orchestrator")
    parser.add_argument("--ticket", help="Jira ticket ID to plan (e.g. SCRUM-6)", default=None)
    parser.add_argument("--org-id", help="Tenant organization ID", default=os.environ.get("ORG_ID"))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run planner + HITL only; skip code generation and git push",
    )
    args = parser.parse_args()

    if args.ticket:
        asyncio.run(run_planner_workflow(args.ticket, dry_run=args.dry_run, org_id=args.org_id))
    else:
        asyncio.run(run_healthcheck())
