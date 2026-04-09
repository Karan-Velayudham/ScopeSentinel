"""
dispatcher.py — Core dispatch logic for the Trigger Engine.

Receives a normalized trigger event from any TriggerSource and calls
POST /api/runs on the Control Plane API to start a workflow run.

Responsibility:
  - Build the correct run payload from TriggerDefinition fields + extra_inputs
  - Set trigger_type correctly for traceability
  - Retry on transient API failures
"""

import asyncio
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Number of retry attempts for the POST /api/runs call
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds


class Dispatcher:
    def __init__(self, api_url: str, internal_auth_token: str):
        self.api_url = api_url
        self.internal_auth_token = internal_auth_token

    async def dispatch(
        self,
        trigger: dict,
        trigger_type: str,
        extra_inputs: dict[str, Any],
    ) -> None:
        """
        Fire a workflow run for the given trigger definition.

        Args:
            trigger: The TriggerDefinition dict from the API.
            trigger_type: "schedule", "one_time", or "event"
            extra_inputs: Additional context from the event (e.g., Jira payload).
        """
        org_id = trigger.get("org_id")
        agent_id = trigger.get("agent_id")
        trigger_id = trigger.get("id")
        trigger_name = trigger.get("name", "unknown")

        if not org_id or not agent_id:
            logger.error(
                "Dispatcher: trigger %s missing org_id or agent_id, skipping", trigger_id
            )
            return

        # Merge static inputs from the TriggerDefinition with runtime event data
        static_inputs: dict[str, Any] = {}
        if trigger.get("inputs"):
            try:
                static_inputs = trigger["inputs"] if isinstance(trigger["inputs"], dict) else json.loads(trigger["inputs"])
            except (json.JSONDecodeError, TypeError):
                pass

        merged_inputs = {**static_inputs, **extra_inputs}

        # Extract a human-readable task description for the run
        task = merged_inputs.pop("task", None) or trigger_name

        payload = {
            "agent_id": agent_id,
            "inputs": {**merged_inputs, "task": task},
            "trigger_type": trigger_type,
        }

        # Extract ticket_id if present in event payload (e.g., Jira issue key)
        jira_key = extra_inputs.get("payload", {}).get("issue", {}).get("key")
        if jira_key:
            payload["ticket_id"] = jira_key

        log = logger.getChild("dispatch")
        log.info(
            "Dispatching run for trigger %s (%s), agent=%s, org=%s",
            trigger_id,
            trigger_name,
            agent_id,
            org_id,
        )

        # Retry loop with exponential backoff
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                    resp = await client.post(
                        f"{self.api_url}/api/runs/",
                        json=payload,
                        headers={
                            "X-ScopeSentinel-Org-ID": org_id,
                            "Authorization": f"Bearer {self.internal_auth_token}",
                        },
                    )
                    resp.raise_for_status()
                    run_data = resp.json()
                    log.info(
                        "Run created: run_id=%s status=%s",
                        run_data.get("run_id"),
                        run_data.get("status"),
                    )
                    return  # Success
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                wait = RETRY_BACKOFF_BASE ** attempt
                if attempt < MAX_RETRIES:
                    log.warning(
                        "Dispatch attempt %d/%d failed (%s). Retrying in %ds...",
                        attempt,
                        MAX_RETRIES,
                        exc,
                        wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    log.error(
                        "Dispatch failed after %d attempts for trigger %s: %s",
                        MAX_RETRIES,
                        trigger_id,
                        exc,
                    )
