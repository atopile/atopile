"""Model state - workspace path and build orchestration."""

from __future__ import annotations

import importlib
from typing import Any

__all__ = [
    "artifacts",
    "atopile_install",
    "build_queue",
    "builds",
    "cost_estimation",
    "layout",
    "manufacturing",
    "packages",
    "parts",
    "parts_search",
    "parts_search_jlc",
    "projects",
    "resolve",
    "stdlib",
]


def __getattr__(name: str) -> Any:
    if name in __all__:
        return importlib.import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + __all__)
