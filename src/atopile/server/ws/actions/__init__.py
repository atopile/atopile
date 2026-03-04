"""WebSocket action handlers and dispatch APIs."""

# Import modules for registration side effects.
from . import core as _core  # noqa: F401
from . import ui as _ui  # noqa: F401
from .registry import (
    dispatch_registered_action,
    get_registered_actions,
    register_action,
)

__all__ = ["dispatch_registered_action", "get_registered_actions", "register_action"]
