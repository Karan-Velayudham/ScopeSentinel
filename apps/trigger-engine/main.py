"""
main.py — Trigger Engine entry point.

Bootstraps all TriggerSource plugins and runs them concurrently:
  - CronSource:     Handles recurring schedule-type triggers.
  - OneTimeSource:  Polls for one-time triggers ready to fire.
  - RedpandaSource: Consumes events for event-type triggers.

Adding a new source (e.g., Slack) only requires:
  1. Creating sources/slack.py implementing TriggerSource.
  2. Importing and adding it to `sources` list below.
"""

import asyncio
import logging
import os

from dispatcher import Dispatcher
from sources.cron import CronSource
from sources.one_time import OneTimeSource
from sources.redpanda import RedpandaSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


async def main() -> None:
    api_url = _env("API_URL", "http://localhost:8000")
    internal_auth_token = _env("INTERNAL_AUTH_TOKEN", "")
    redpanda_brokers = _env("REDPANDA_BROKERS", "localhost:19092")
    webhook_topic = _env("WEBHOOK_TOPIC", "incoming-events")

    logger.info("Trigger Engine starting up")
    logger.info("  API_URL: %s", api_url)
    logger.info("  REDPANDA_BROKERS: %s", redpanda_brokers)
    logger.info("  WEBHOOK_TOPIC: %s", webhook_topic)

    dispatcher = Dispatcher(api_url=api_url, internal_auth_token=internal_auth_token)

    # ── Source plugins ────────────────────────────────────────────────────────
    # Each source runs independently. To add Slack/Teams in the future:
    #   from sources.slack import SlackSource
    #   SlackSource(...)
    sources = [
        CronSource(api_url=api_url, internal_auth_token=internal_auth_token, sync_interval=60),
        OneTimeSource(api_url=api_url, internal_auth_token=internal_auth_token, poll_interval=30),
        RedpandaSource(
            redpanda_brokers=redpanda_brokers,
            topic=webhook_topic,
            api_url=api_url,
            internal_auth_token=internal_auth_token,
        ),
    ]

    # Run all sources concurrently
    await asyncio.gather(
        *[source.start(dispatcher) for source in sources]
    )


if __name__ == "__main__":
    asyncio.run(main())
