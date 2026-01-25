"""Model state - event loop, workspace paths, event emission."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

log = logging.getLogger(__name__)

# Callback for emitting events (registered by server at startup)
EventEmitter = Callable[[str, Optional[dict]], Coroutine[Any, Any, None]]


class ModelState:
    """
    Shared model state for the application.

    This provides:
    - Event loop reference for background thread event emission
    - Workspace paths for project discovery
    - Event emission via a registered callback (from server/connections)
    """

    def __init__(self) -> None:
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._workspace_path: Optional[Path] = None
        self._event_emitter: Optional[EventEmitter] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Store the event loop for background thread emits."""
        self._event_loop = loop
        log.info("ModelState: Event loop captured")

    def set_workspace_path(self, path: Optional[Path]) -> None:
        """Set workspace path for discovery operations."""
        self._workspace_path = path

    @property
    def workspace_path(self) -> Optional[Path]:
        """Get workspace path for discovery operations."""
        return self._workspace_path

    def register_event_emitter(self, emitter: EventEmitter) -> None:
        """Register callback for event emission (called by server)."""
        self._event_emitter = emitter
        log.info("ModelState: Event emitter registered")

    async def emit_event(self, event_type: str, data: Optional[dict] = None) -> None:
        """Emit an event asynchronously."""
        if self._event_emitter:
            await self._event_emitter(event_type, data)

    def emit_event_sync(self, event_type: str, data: Optional[dict] = None) -> None:
        """Emit an event from synchronous code (background thread)."""
        if self._event_loop and self._event_loop.is_running() and self._event_emitter:
            asyncio.run_coroutine_threadsafe(
                self._event_emitter(event_type, data), self._event_loop
            )
        else:
            log.warning(
                f"Cannot emit event '{event_type}': event loop or emitter not available"
            )


# Global singleton instance
model_state = ModelState()


def get_model_state() -> ModelState:
    """Get the global model state singleton."""
    return model_state


def reset_model_state() -> ModelState:
    """Reset the model state (used for tests)."""
    global model_state
    model_state = ModelState()
    return model_state
