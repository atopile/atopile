"""Global UI state store shared across the hub.

Single-instance module. Import and mutate fields directly:

    from .store import store
    store.projects = ({"root": "/a", "name": "myproj", "targets": []},)

Assigning to a field automatically notifies subscribers.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from typing import Any


def _serialize(value: object) -> object:
    """Serialize a value for JSON. Frozen dataclasses become dicts."""
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)  # type: ignore[arg-type]
    return value


@dataclass(frozen=True)
class CoreStatus:
    connected: bool = False


@dataclass(frozen=True)
class ProjectState:
    projects: tuple = ()
    builds: tuple = ()
    selected_project: str | None = None
    selected_target: str | None = None


@dataclass
class Store:
    """In-memory shared UI state. Notifies on change automatically.

    Top-level fields are reactive — assigning to them notifies subscribers.
    """

    core_status: CoreStatus = CoreStatus()
    project_state: ProjectState = ProjectState()

    def __setattr__(self, name: str, value: Any) -> None:
        try:
            old = getattr(self, name)
        except AttributeError:
            object.__setattr__(self, name, value)
            return
        object.__setattr__(self, name, value)
        if old != value and on_change is not None:
            asyncio.ensure_future(on_change(name, _serialize(value)))

    def get(self, key: str) -> object:
        """Get the serialized value of a top-level field."""
        return _serialize(getattr(self, key))


store = Store()
on_change: Any = None
