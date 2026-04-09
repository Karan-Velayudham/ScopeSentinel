"""
tests/test_run_dispatch.py — Unit tests for the Temporal dispatch routing logic.

The routing function is inlined here to avoid importing the heavy runs.py module
and its transitive deps (temporalio, redis, asyncpg, jose, etc.).
Keep in sync with routers/runs.py:_resolve_temporal_dispatch.
"""

import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Inline copy of the pure routing function — mirrors routers/runs.py exactly
# ---------------------------------------------------------------------------

def _resolve_temporal_dispatch(run, task_input: str, inputs_json: str) -> tuple[str, list, str]:
    temporal_wf_id = f"ss-run-{run.id}"
    if run.workflow_id:
        return (
            "WorkflowYamlWorkflow",
            [str(run.workflow_id), str(run.id), task_input, inputs_json],
            temporal_wf_id,
        )
    else:
        return (
            "AgentReActWorkflow",
            [str(run.agent_id), str(run.id), task_input],
            temporal_wf_id,
        )


def _make_run(**kwargs):
    defaults = dict(id="run-001", org_id="org-001", agent_id=None, workflow_id=None)
    defaults.update(kwargs)
    run = MagicMock()
    for k, v in defaults.items():
        setattr(run, k, v)
    return run


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestResolveTemporalDispatch:

    def test_agent_only_routes_to_react_workflow(self):
        run = _make_run(agent_id="agent-abc", workflow_id=None)
        wf_type, args, _ = _resolve_temporal_dispatch(run, "Do the task", "{}")
        assert wf_type == "AgentReActWorkflow"
        assert args == ["agent-abc", "run-001", "Do the task"]

    def test_workflow_id_routes_to_yaml_workflow(self):
        run = _make_run(agent_id=None, workflow_id="wf-xyz")
        wf_type, args, _ = _resolve_temporal_dispatch(run, "Run workflow", '{"ticket_id": "T-1"}')
        assert wf_type == "WorkflowYamlWorkflow"
        assert args == ["wf-xyz", "run-001", "Run workflow", '{"ticket_id": "T-1"}']

    def test_workflow_id_takes_priority_over_agent_id(self):
        run = _make_run(agent_id="agent-abc", workflow_id="wf-xyz")
        wf_type, _, _ = _resolve_temporal_dispatch(run, "task", "{}")
        assert wf_type == "WorkflowYamlWorkflow"

    def test_canonical_temporal_id_format(self):
        run_agent = _make_run(agent_id="agent-abc", workflow_id=None)
        run_wf    = _make_run(agent_id=None, workflow_id="wf-xyz")
        _, _, agent_wf_id = _resolve_temporal_dispatch(run_agent, "t", "{}")
        _, _, yaml_wf_id  = _resolve_temporal_dispatch(run_wf,    "t", "{}")
        assert agent_wf_id == "ss-run-run-001"
        assert yaml_wf_id  == "ss-run-run-001"

    def test_empty_inputs_json_passed_through(self):
        run = _make_run(workflow_id="wf-empty")
        _, args, _ = _resolve_temporal_dispatch(run, "x", "{}")
        assert args[3] == "{}"

    def test_task_input_in_react_args(self):
        run = _make_run(agent_id="a")
        _, args, _ = _resolve_temporal_dispatch(run, "fix the bug", "{}")
        assert args[2] == "fix the bug"

    def test_task_input_in_yaml_args(self):
        run = _make_run(workflow_id="w")
        _, args, _ = _resolve_temporal_dispatch(run, "run deployment steps", "{}")
        assert args[2] == "run deployment steps"
