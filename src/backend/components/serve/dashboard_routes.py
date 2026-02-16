from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from .dashboard_metrics import DashboardMetrics

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])

_KNOWN_SERVICES = (
    "components-serve",
    "components-fetch",
    "packages-serve",
)


def _get_dashboard_metrics(request: Request) -> DashboardMetrics:
    metrics = getattr(request.app.state, "dashboard_metrics", None)
    if metrics is None:
        raise HTTPException(status_code=500, detail="Dashboard metrics unavailable")
    return metrics


def _inject_service_placeholders(payload: dict[str, Any]) -> None:
    raw_services = payload.get("services")
    if not isinstance(raw_services, list):
        payload["services"] = []
        raw_services = payload["services"]
    indexed = {
        entry.get("service"): entry
        for entry in raw_services
        if isinstance(entry, dict) and isinstance(entry.get("service"), str)
    }
    for service in _KNOWN_SERVICES:
        if service in indexed:
            continue
        raw_services.append(
            {
                "service": service,
                "status": "standby",
                "requests": 0,
                "requests_per_min": 0.0,
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "error_rate_pct": 0.0,
                "success_rate_pct": 100.0,
            }
        )
    payload["services"] = sorted(raw_services, key=lambda entry: str(entry["service"]))


@router.get("/metrics")
def get_dashboard_metrics(
    request: Request,
    window_seconds: int = Query(default=900, ge=60, le=86400),
) -> dict[str, Any]:
    metrics = _get_dashboard_metrics(request)
    snapshot_package_stats = getattr(request.app.state, "snapshot_package_stats", {})
    payload = metrics.snapshot(
        window_seconds=window_seconds,
        snapshot_package_stats=(
            snapshot_package_stats if isinstance(snapshot_package_stats, dict) else {}
        ),
    )
    _inject_service_placeholders(payload)
    return payload


def test_inject_service_placeholders_adds_future_services() -> None:
    payload = {
        "services": [
            {
                "service": "components-serve",
                "status": "online",
            }
        ]
    }
    _inject_service_placeholders(payload)
    names = [item["service"] for item in payload["services"]]
    assert names == ["components-fetch", "components-serve", "packages-serve"]
