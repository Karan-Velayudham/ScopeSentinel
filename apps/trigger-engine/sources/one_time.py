"""
sources/one_time.py — One-time TriggerSource.

Polls the API every 30s for `one_time` triggers where run_at <= now.
After firing, immediately deactivates the trigger via PATCH.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

import httpx

from sources.base import TriggerSource

logger = logging.getLogger(__name__)


class OneTimeSource(TriggerSource):
    def __init__(self, api_url: str, internal_auth_token: str, poll_interval: int = 30):
        self.api_url = api_url
        self.internal_auth_token = internal_auth_token
        self.poll_interval = poll_interval

    async def start(self, dispatcher) -> None:
        self._dispatcher = dispatcher
        logger.info("OneTimeSource started — polling every %ds", self.poll_interval)

        while True:
            await self._check_and_fire()
            await asyncio.sleep(self.poll_interval)

    async def _check_and_fire(self) -> None:
        now = datetime.now(timezone.utc)
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(
                    f"{self.api_url}/api/triggers/",
                    params={"active_only": True},
                    headers={"Authorization": f"Bearer {self.internal_auth_token}"},
                )
                resp.raise_for_status()
                triggers = resp.json().get("items", [])
        except Exception as exc:
            logger.error("OneTimeSource: failed to fetch triggers", exc_info=exc)
            return

        for trigger in triggers:
            if trigger["trigger_type"] != "one_time":
                continue

            run_at_str = trigger.get("run_at")
            if not run_at_str:
                continue

            try:
                run_at = datetime.fromisoformat(run_at_str.replace("Z", "+00:00"))
            except ValueError:
                continue

            if run_at <= now:
                logger.info("OneTimeSource: firing trigger %s (%s)", trigger["id"], trigger["name"])
                await self._dispatcher.dispatch(
                    trigger=trigger,
                    trigger_type="one_time",
                    extra_inputs={},
                )
                # Deactivate immediately to prevent double-firing
                await self._deactivate(trigger["id"], client)

    async def _deactivate(self, trigger_id: str, client: httpx.AsyncClient) -> None:
        try:
            await client.patch(
                f"{self.api_url}/api/triggers/{trigger_id}",
                json={"is_active": False},
                headers={"Authorization": f"Bearer {self.internal_auth_token}"},
            )
            logger.info("OneTimeSource: deactivated trigger %s", trigger_id)
        except Exception as exc:
            logger.error("OneTimeSource: failed to deactivate trigger %s", trigger_id, exc_info=exc)
