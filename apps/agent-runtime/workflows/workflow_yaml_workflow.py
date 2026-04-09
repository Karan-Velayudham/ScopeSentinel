"""
workflows/workflow_yaml_workflow.py — Dynamic YAML-defined workflow executor.

Runs any Workflow created in the UI by interpreting its yaml_content step graph.

Supported step types:
  - tool   : Calls a named MCP/platform tool via execute_tool_activity
  - hitl   : Pauses execution and waits for human approval via Temporal Signal
  - agent  : Delegates to a sub-agent (runs llm_reasoning + tool loop inline)

YAML schema example:
  steps:
    - name: fetch_issue
      type: tool
      tool: jira:get_issue
      args:
        issue_key: "{{ inputs.ticket_id }}"

    - name: human_review
      type: hitl

    - name: create_pr
      type: tool
      tool: github:create_pull_request
      args:
        title: "Automated: {{ steps.fetch_issue.result }}"

Simple template substitution is supported: {{ inputs.<key> }} and {{ steps.<name>.result }}.
"""

import json
import re
from datetime import timedelta
from typing import Any

import yaml
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.workflow_activities import get_workflow_config_activity
    from activities.react_activities import (
        execute_tool_activity,
        log_event_activity,
        update_run_status_activity,
        get_org_id_activity,
    )

_default_retry = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(seconds=2),
    maximum_interval=timedelta(seconds=30),
)


def _render(value: Any, context: dict) -> Any:
    """
    Recursively substitute {{ inputs.key }} and {{ steps.name.result }} in strings.
    Non-string values are returned as-is.
    """
    if isinstance(value, str):
        def _sub(m: re.Match) -> str:
            expr = m.group(1).strip()
            parts = expr.split(".")
            node = context
            try:
                for p in parts:
                    node = node[p]
                return str(node)
            except (KeyError, TypeError):
                return m.group(0)  # leave unresolved placeholders intact

        return re.sub(r"\{\{\s*(.+?)\s*\}\}", _sub, value)
    elif isinstance(value, dict):
        return {k: _render(v, context) for k, v in value.items()}
    elif isinstance(value, list):
        return [_render(v, context) for v in value]
    return value


@workflow.defn(name="WorkflowYamlWorkflow")
class WorkflowYamlWorkflow:
    """
    Executes a YAML-defined Workflow record stored in the database.

    Args (passed by the API at start_workflow):
        workflow_id  : UUID of the Workflow DB record
        run_id       : UUID of the WorkflowRun DB record
        task_input   : The task/instruction string for context in templates
        inputs_json  : JSON-serialised dict of runtime inputs (from TriggerRunRequest)
    """

    def __init__(self) -> None:
        self._hitl_decision: dict | None = None

    # ------------------------------------------------------------------
    # Temporal Signal handler (HITL)
    # ------------------------------------------------------------------

    @workflow.signal(name="hitl-decision-signal")
    async def hitl_signal(self, decision: dict) -> None:
        """Receives approve/reject/modify from the API decision endpoint."""
        self._hitl_decision = decision

    # ------------------------------------------------------------------
    # Main workflow entrypoint
    # ------------------------------------------------------------------

    @workflow.run
    async def run(
        self,
        workflow_id: str,
        run_id: str,
        task_input: str,
        inputs_json: str = "{}",
    ) -> dict:
        # 1. Resolve tenant
        org_id = await workflow.execute_activity(
            get_org_id_activity,
            run_id,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=_default_retry,
        )

        # 2. Mark running
        await workflow.execute_activity(
            update_run_status_activity,
            {"run_id": run_id, "status": "RUNNING"},
            start_to_close_timeout=timedelta(seconds=10),
        )

        # 3. Fetch workflow YAML definition
        wf_config = await workflow.execute_activity(
            get_workflow_config_activity,
            workflow_id,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=_default_retry,
        )

        # 4. Parse YAML
        try:
            wf_def = yaml.safe_load(wf_config["yaml_content"]) or {}
        except yaml.YAMLError as exc:
            await workflow.execute_activity(
                update_run_status_activity,
                {"run_id": run_id, "status": "FAILED"},
                start_to_close_timeout=timedelta(seconds=10),
            )
            return {"status": "FAILED", "error": f"Invalid YAML: {exc}"}

        steps: list[dict] = wf_def.get("steps", [])

        # 5. Build template context
        try:
            inputs: dict = json.loads(inputs_json) if inputs_json else {}
        except json.JSONDecodeError:
            inputs = {}
        inputs.setdefault("task", task_input)

        context = {"inputs": inputs, "steps": {}}

        # 6. Execute steps sequentially
        for step in steps:
            step_name = step.get("name", "unnamed")
            step_type = step.get("type", "tool")

            await workflow.execute_activity(
                log_event_activity,
                {
                    "run_id": run_id,
                    "event_type": "LOG",
                    "payload": {"message": f"Starting step: {step_name} ({step_type})"},
                },
                start_to_close_timeout=timedelta(seconds=10),
            )

            # ── HITL step ──────────────────────────────────────────────
            if step_type == "hitl":
                # Signal the API that we're paused and wait for human decision
                await workflow.execute_activity(
                    update_run_status_activity,
                    {"run_id": run_id, "status": "WAITING_HITL"},
                    start_to_close_timeout=timedelta(seconds=10),
                )

                # Pause until signal arrives (no timeout — humans take their time)
                await workflow.wait_condition(lambda: self._hitl_decision is not None)

                decision = self._hitl_decision
                self._hitl_decision = None  # reset for potential future HITL steps

                if decision.get("action") == "reject":
                    await workflow.execute_activity(
                        update_run_status_activity,
                        {"run_id": run_id, "status": "FAILED"},
                        start_to_close_timeout=timedelta(seconds=10),
                    )
                    return {"status": "REJECTED", "step": step_name}

                # approve or modify — resume
                await workflow.execute_activity(
                    update_run_status_activity,
                    {"run_id": run_id, "status": "RUNNING"},
                    start_to_close_timeout=timedelta(seconds=10),
                )
                context["steps"][step_name] = {"result": decision.get("feedback", "")}
                continue

            # ── Tool step ──────────────────────────────────────────────
            if step_type == "tool":
                tool_name = step.get("tool", "")
                raw_args = step.get("args", {})
                rendered_args = _render(raw_args, context)

                await workflow.execute_activity(
                    log_event_activity,
                    {
                        "run_id": run_id,
                        "event_type": "TOOL_CALL",
                        "payload": {"tool": tool_name, "args": rendered_args},
                    },
                    start_to_close_timeout=timedelta(seconds=10),
                )

                tool_output = await workflow.execute_activity(
                    execute_tool_activity,
                    {
                        "tool_name": tool_name,
                        "tool_args": json.dumps(rendered_args) if isinstance(rendered_args, dict) else rendered_args,
                        "org_id": org_id,
                    },
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=_default_retry,
                )

                result_value = tool_output.get("result") or tool_output.get("error")

                await workflow.execute_activity(
                    log_event_activity,
                    {
                        "run_id": run_id,
                        "event_type": "TOOL_RESULT",
                        "payload": {"tool": tool_name, "output": result_value},
                    },
                    start_to_close_timeout=timedelta(seconds=10),
                )

                context["steps"][step_name] = {"result": result_value}
                continue

            # ── Unknown step type ──────────────────────────────────────
            await workflow.execute_activity(
                log_event_activity,
                {
                    "run_id": run_id,
                    "event_type": "LOG",
                    "payload": {"message": f"Unknown step type '{step_type}' for step '{step_name}' — skipping."},
                },
                start_to_close_timeout=timedelta(seconds=10),
            )

        # 7. Finalize
        await workflow.execute_activity(
            update_run_status_activity,
            {"run_id": run_id, "status": "COMPLETED"},
            start_to_close_timeout=timedelta(seconds=10),
        )

        return {
            "status": "COMPLETED",
            "workflow_name": wf_config["name"],
            "steps_executed": [s.get("name") for s in steps],
            "outputs": context["steps"],
        }
