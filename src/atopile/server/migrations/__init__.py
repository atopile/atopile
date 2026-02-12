"""
Migration step registry.

Auto-discovers all MigrationStep subclasses in this package.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from ._base import (
    EVENT_MIGRATION_RESULT,
    EVENT_MIGRATION_STEP_RESULT,
    MigrationStep,
    Topic,
)

__all__ = [
    "EVENT_MIGRATION_RESULT",
    "EVENT_MIGRATION_STEP_RESULT",
    "MigrationStep",
    "Topic",
    "get_all_steps",
    "get_step",
    "get_topic_order",
]

# ---- Auto-discovery ----

_steps: dict[str, MigrationStep] | None = None


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
        _steps = _discover()
    return _steps


# ---- Public API ----


def get_all_steps() -> list[MigrationStep]:
    """Return all steps sorted by topic order then step order."""
    topic_order = list(Topic)
    steps = list(_ensure().values())
    steps.sort(key=lambda s: (topic_order.index(s.topic), s.order))
    return steps


def get_step(step_id: str) -> MigrationStep:
    """Look up a single step by id. Raises KeyError if not found."""
    return _ensure()[step_id]


def get_topic_order() -> list[str]:
    """Return topic values in their display order."""
    return [t.value for t in Topic]
