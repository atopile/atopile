from __future__ import annotations

import logging
from typing import Any

from fastapi import Request

from ..shared.telemetry import log_event as _log_backend_event
from .dashboard_metrics import DashboardMetrics

_dashboard_metrics: DashboardMetrics | None = None


def set_dashboard_metrics(metrics: DashboardMetrics | None) -> None:
    global _dashboard_metrics
    _dashboard_metrics = metrics


def get_dashboard_metrics() -> DashboardMetrics | None:
    return _dashboard_metrics


def log_event(event: str, *, level: int = logging.INFO, **fields: Any) -> None:
    if _dashboard_metrics is not None:
        _dashboard_metrics.observe(event, fields)
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
