"""
sources/redpanda.py — Event-driven TriggerSource.

Consumes from the Redpanda `incoming-events` topic. For each message,
fetches active `event` TriggerDefinitions and matches them against
the event payload using event_filter rules.

Designed for extensibility: Slack, Teams, or any future source simply
needs to publish a normalized event to the same topic.

Expected message schema on the topic:
{
    "source": "jira",           # Where the event originated
    "event_type": "jira:issue_created",
    "org_id": "abc-123",        # Tenant scoping
    "payload": { ... }          # Raw source payload
}
"""

import asyncio
import json
import logging

import httpx
from aiokafka import AIOKafkaConsumer

from sources.base import TriggerSource

logger = logging.getLogger(__name__)


class RedpandaSource(TriggerSource):
    def __init__(
        self,
        redpanda_brokers: str,
        topic: str,
        api_url: str,
        internal_auth_token: str,
        cache_ttl: int = 60,
    ):
        self.redpanda_brokers = redpanda_brokers
        self.topic = topic
        self.api_url = api_url
        self.internal_auth_token = internal_auth_token
        self.cache_ttl = cache_ttl
        self._trigger_cache: list[dict] = []
        self._cache_timestamp: float = 0

    async def start(self, dispatcher) -> None:
        self._dispatcher = dispatcher
        logger.info("RedpandaSource: connecting to %s, topic=%s", self.redpanda_brokers, self.topic)

        consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.redpanda_brokers,
            auto_offset_reset="latest",
            group_id="trigger-engine-event-consumer",
        )

        while True:
            try:
                await consumer.start()
                logger.info("RedpandaSource: connected to Redpanda")
                break
            except Exception as exc:
                logger.warning("RedpandaSource: waiting for Redpanda... %s", exc)
                await asyncio.sleep(5)

        try:
            async for msg in consumer:
                try:
                    event_data = json.loads(msg.value.decode("utf-8"))
                    await self._process(event_data)
                except json.JSONDecodeError:
                    logger.warning("RedpandaSource: non-JSON message on %s", self.topic)
                except Exception as exc:
                    logger.error("RedpandaSource: error processing message", exc_info=exc)
        finally:
            await consumer.stop()

    async def _process(self, event_data: dict) -> None:
        """Match event against active event-type TriggerDefinitions and dispatch matches."""
        import time

        org_id = event_data.get("org_id")
        if not org_id:
            logger.debug("RedpandaSource: skipping event with no org_id")
            return

        # Refresh trigger cache if stale
        now = time.monotonic()
        if now - self._cache_timestamp > self.cache_ttl:
            await self._refresh_cache()
            self._cache_timestamp = now

        # Match event against filters
        for trigger in self._trigger_cache:
            if trigger.get("trigger_type") != "event":
                continue
            if trigger.get("org_id") != org_id:
                continue

            event_filter = trigger.get("event_filter") or {}
            if self._matches(event_data, event_filter):
                logger.info(
                    "RedpandaSource: matched trigger %s for event %s/%s",
                    trigger["id"],
                    event_data.get("source"),
                    event_data.get("event_type"),
                )
                await self._dispatcher.dispatch(
                    trigger=trigger,
                    trigger_type="event",
                    extra_inputs={
                        "source": event_data.get("source"),
                        "event_type": event_data.get("event_type"),
                        "payload": event_data.get("payload", {}),
                    },
                )

    def _matches(self, event_data: dict, event_filter: dict) -> bool:
        """
        Returns True if all key/value pairs in event_filter are present
        in the top-level event_data dict. Allows partial matching.
        """
        for key, expected_value in event_filter.items():
            if event_data.get(key) != expected_value:
                return False
        return True

    async def _refresh_cache(self) -> None:
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(
                    f"{self.api_url}/api/triggers/",
                    params={"active_only": True},
                    headers={"Authorization": f"Bearer {self.internal_auth_token}"},
                )
                resp.raise_for_status()
                self._trigger_cache = resp.json().get("items", [])
                logger.debug("RedpandaSource: cache refreshed, %d triggers", len(self._trigger_cache))
        except Exception as exc:
            logger.error("RedpandaSource: failed to refresh trigger cache", exc_info=exc)
