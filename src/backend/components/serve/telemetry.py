from __future__ import annotations

import logging
from typing import Any

from fastapi import Request

from ..shared.telemetry import log_event as _log_backend_event


def log_event(event: str, *, level: int = logging.INFO, **fields: Any) -> None:
    _log_backend_event(
        service="components-serve",
        event=event,
        level=level,
        logger_name="atopile.components.serve",
        **fields,
    )


def get_request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    if value is None:
        return None
    return str(value)
