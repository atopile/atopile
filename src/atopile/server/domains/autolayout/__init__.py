"""Autolayout domain services and provider adapters."""

from typing import Any

__all__ = ["AutolayoutService", "get_autolayout_service"]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from atopile.server.domains.autolayout.service import (
        AutolayoutService,
        get_autolayout_service,
    )

    return {
        "AutolayoutService": AutolayoutService,
        "get_autolayout_service": get_autolayout_service,
    }[name]
