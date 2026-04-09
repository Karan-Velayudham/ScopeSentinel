"""
sources/cron.py — Schedule-based TriggerSource.

On startup, fetches all active `schedule` TriggerDefinitions from the API
and registers them as APScheduler cron jobs. Re-syncs every 60 seconds
to pick up newly created or modified triggers.
"""

import asyncio
import json
import logging

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from sources.base import TriggerSource

logger = logging.getLogger(__name__)


class CronSource(TriggerSource):
    def __init__(self, api_url: str, internal_auth_token: str, sync_interval: int = 60):
        self.api_url = api_url
        self.internal_auth_token = internal_auth_token
        self.sync_interval = sync_interval
        self._scheduler = AsyncIOScheduler()
        self._registered_ids: set[str] = set()

    async def start(self, dispatcher) -> None:
        self._dispatcher = dispatcher
        self._scheduler.start()
        logger.info("CronSource started — APScheduler running")

        while True:
            await self._sync_triggers()
            await asyncio.sleep(self.sync_interval)

    async def _sync_triggers(self) -> None:
        """Fetch all active schedule triggers from the API and (re)schedule them."""
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
            logger.error("CronSource: failed to fetch triggers from API", exc_info=exc)
            return

        current_ids = {t["id"] for t in triggers if t["trigger_type"] == "schedule"}

        # Remove triggers that are no longer active
        for tid in list(self._registered_ids - current_ids):
            try:
                self._scheduler.remove_job(tid)
                self._registered_ids.discard(tid)
                logger.info("CronSource: removed job %s", tid)
            except Exception:
                pass

        # Add new / update existing
        for trigger in triggers:
            if trigger["trigger_type"] != "schedule":
                continue
            tid = trigger["id"]
            cron_expr = trigger.get("cron_expr")
            if not cron_expr:
                continue

            # Parse cron expression: "min hour day month day_of_week"
            parts = cron_expr.strip().split()
            if len(parts) != 5:
                logger.warning("CronSource: invalid cron_expr for trigger %s: %s", tid, cron_expr)
                continue

            minute, hour, day, month, day_of_week = parts

            if tid not in self._registered_ids:
                self._scheduler.add_job(
                    self._fire,
                    trigger="cron",
                    id=tid,
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week,
                    kwargs={"trigger": trigger},
                    replace_existing=True,
                )
                self._registered_ids.add(tid)
                logger.info("CronSource: scheduled job %s (%s) cron=%s", tid, trigger["name"], cron_expr)

    async def _fire(self, trigger: dict) -> None:
        logger.info("CronSource: firing trigger %s (%s)", trigger["id"], trigger["name"])
        await self._dispatcher.dispatch(
            trigger=trigger,
            trigger_type="schedule",
            extra_inputs={},
        )
