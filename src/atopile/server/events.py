"""Event types and emission for WebSocket clients."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine, Optional

from atopile.dataclasses import EventType

log = logging.getLogger(__name__)


# Callback for emitting events (registered by server at startup)
EventEmitter = Callable[[str, Optional[dict]], Coroutine[Any, Any, None]]


class EventBus:
    """
    Event emission for WebSocket clients.

    Provides both async and sync emission methods. The sync method
    schedules the async emit on the event loop for thread-safe emission
    from background threads.
    """

    def __init__(self) -> None:
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._event_emitter: Optional[EventEmitter] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Store the event loop for background thread emits."""
        self._event_loop = loop
        log.info("EventBus: Event loop captured")

    def register_emitter(self, emitter: EventEmitter) -> None:
        """Register callback for event emission (called by server)."""
        self._event_emitter = emitter
        log.info("EventBus: Event emitter registered")

    def _event_str(self, event_type: EventType | str) -> str:
        """Convert event type to string."""
        return event_type.value if isinstance(event_type, EventType) else event_type

    async def emit(
        self, event_type: EventType | str, data: Optional[dict] = None
    ) -> None:
        """Emit an event asynchronously."""
        if self._event_emitter:
            await self._event_emitter(self._event_str(event_type), data)

    def emit_sync(
        self, event_type: EventType | str, data: Optional[dict] = None
    ) -> None:
        """Emit an event from synchronous code (background thread)."""
        if self._event_loop and self._event_loop.is_running() and self._event_emitter:
            asyncio.run_coroutine_threadsafe(
                self._event_emitter(self._event_str(event_type), data),
                self._event_loop,
            )
        else:
            log.warning(
                f"Cannot emit event '{event_type}': event loop or emitter not available"
            )


# Global singleton instance
event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Get the global event bus singleton."""
    return event_bus


def reset_event_bus() -> EventBus:
    """Reset the event bus (used for tests)."""
    global event_bus
    event_bus = EventBus()
    return event_bus
