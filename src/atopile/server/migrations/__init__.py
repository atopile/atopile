"""
Migration step registry.

Auto-discovers all MigrationStep subclasses in this package.
"""

from __future__ import annotations

import importlib
import pkgutil
import threading
from pathlib import Path

from ._base import (
    EVENT_MIGRATION_RESULT,
    EVENT_MIGRATION_STEP_RESULT,
    MigrationStep,
    Topic,
    Topics,
)

__all__ = [
    "EVENT_MIGRATION_RESULT",
    "EVENT_MIGRATION_STEP_RESULT",
    "MigrationStep",
    "Topic",
    "Topics",
    "get_all_steps",
    "get_step",
    "get_topics",
]

# ---- Auto-discovery ----

_steps: dict[str, MigrationStep] | None = None
_steps_lock = threading.Lock()


def _discover() -> dict[str, MigrationStep]:
    """Import every module in this package and collect MigrationStep subclasses."""
    package_dir = Path(__file__).parent

    for module_info in pkgutil.iter_modules([str(package_dir)]):
        if module_info.name.startswith("_"):
            continue
        importlib.import_module(f"{__name__}.{module_info.name}")

    registry: dict[str, MigrationStep] = {}
    for cls in MigrationStep.__subclasses__():
        instance = cls()
        step_id = cls.get_id()
        if step_id in registry:
            raise ValueError(
                f"Duplicate migration step ID '{step_id}' "
                f"from {cls.__name__} and {type(registry[step_id]).__name__}"
            )
        registry[step_id] = instance
    return registry


def _ensure() -> dict[str, MigrationStep]:
    global _steps
    if _steps is None:
        with _steps_lock:
            if _steps is None:
                _steps = _discover()
    return _steps


# ---- Public API ----


def get_all_steps() -> list[MigrationStep]:
    """Return all steps sorted by topic order then step order."""
    topic_order = Topics.ordered()
    steps = list(_ensure().values())
    # Steps with unknown topics sort to the end
    topic_index = {t: i for i, t in enumerate(topic_order)}
    steps.sort(key=lambda s: (topic_index.get(s.topic, len(topic_order)), s.order))
    return steps


def get_step(step_id: str) -> MigrationStep:
    """Look up a single step by id. Raises KeyError if not found."""
    return _ensure()[step_id]


def get_topics() -> list[dict[str, str]]:
    """Return topics in display order with id, label, and icon."""
    return [t.to_dict() for t in Topics.ordered()]
