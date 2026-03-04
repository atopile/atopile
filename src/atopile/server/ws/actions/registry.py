"""Registry for self-registering WebSocket action handlers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from atopile.dataclasses import AppContext

ActionResult = dict[str, Any]
ActionHandler = Callable[[dict[str, Any], AppContext], Awaitable[ActionResult]]

_handlers: dict[str, ActionHandler] = {}


def register_action(name: str) -> Callable[[ActionHandler], ActionHandler]:
    """Register a WebSocket action handler by action name."""

    def decorator(func: ActionHandler) -> ActionHandler:
        existing = _handlers.get(name)
        if existing and existing is not func:
            msg = f"Duplicate WebSocket action registration: {name}"
            raise ValueError(msg)
        _handlers[name] = func
        return func

    return decorator


def get_registered_actions() -> tuple[str, ...]:
    """Return all registered action names sorted for diagnostics."""
    return tuple(sorted(_handlers.keys()))


async def dispatch_registered_action(
    action: str, payload: dict[str, Any], ctx: AppContext
) -> ActionResult | None:
    """
    Dispatch action to a registered handler.

    Returns None if no registered handler exists for the action.
    """
    handler = _handlers.get(action)
    if handler is None:
        return None
    return await handler(payload, ctx)
