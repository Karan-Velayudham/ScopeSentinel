"""
sources/base.py — Abstract base class for all Trigger Sources.

Every source plugin must implement start(dispatcher). The dispatcher
is responsible for calling POST /api/runs when a trigger rule is matched.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trigger_engine.dispatcher import Dispatcher


class TriggerSource(ABC):
    """
    A self-contained event detection plugin.

    Lifecycle:
      - start(dispatcher) is called once at process startup.
      - The source runs indefinitely (blocking or async loop).
      - When an event should be dispatched, call dispatcher.dispatch(event_data).
    """

    @abstractmethod
    async def start(self, dispatcher: "Dispatcher") -> None:
        """
        Start the source. This method should run indefinitely.
        Use asyncio.gather in main.py to run multiple sources concurrently.
        """
        ...
