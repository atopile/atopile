from __future__ import annotations

import json
import sqlite3
from pathlib import Path
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


def _read_state_counts(state_db: Path) -> dict[str, int]:
    if not state_db.exists():
        return {}
    with sqlite3.connect(state_db) as conn:
        rows = conn.execute(
            "select status, count(*) from roundtrip_part_state group by status"
        ).fetchall()
    return {str(status): int(count) for status, count in rows}


def _read_manifest_stats(manifest_db: Path) -> tuple[int | None, list[dict[str, Any]]]:
    if not manifest_db.exists():
        return None, []
    with sqlite3.connect(manifest_db) as conn:
        total = int(conn.execute("select count(*) from fetch_manifest").fetchone()[0])
        rows = conn.execute(
            """
            select
              artifact_type,
              count(*) as artifact_count,
              count(distinct lcsc_id) as part_count
            from fetch_manifest
            group by artifact_type
            order by artifact_count desc, artifact_type asc
            """
        ).fetchall()
    by_type = [
        {
            "artifact_type": str(artifact_type),
            "artifact_count": int(artifact_count),
            "part_count": int(part_count),
        }
        for artifact_type, artifact_count, part_count in rows
    ]
    return total, by_type


def _read_current_snapshot(snapshot_root: Path) -> dict[str, Any]:
    current = snapshot_root / "current"
    if not (current.exists() or current.is_symlink()):
        return {}
    resolved = current.resolve(strict=False)
    metadata: dict[str, Any] = {}
    metadata_path = resolved / "metadata.json"
    if metadata_path.exists():
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                metadata = payload
        except Exception:
            metadata = {}
    return {
        "current_link": str(current),
        "resolved_snapshot": str(resolved),
        "metadata": metadata,
    }


def _collect_pipeline_status(request: Request) -> dict[str, Any]:
    cfg = getattr(request.app.state, "components_config", None)
    if cfg is None:
        return {}

    cache_dir = Path(cfg.cache_dir)
    state_db = cache_dir / "fetch" / "roundtrip_state.sqlite3"
    manifest_db = cache_dir / "fetch" / "manifest.sqlite3"
    snapshot_root = cache_dir / "snapshots"

    state_counts = _read_state_counts(state_db)
    success = int(state_counts.get("success", 0))
    failed = int(state_counts.get("failed", 0))
    running = int(state_counts.get("running", 0))
    total_parts_seen = success + failed + running
    success_rate_pct = round((100.0 * success / total_parts_seen), 3) if total_parts_seen else None

    manifest_total, assets_by_type = _read_manifest_stats(manifest_db)
    current_snapshot = _read_current_snapshot(snapshot_root)
    snapshot_meta = current_snapshot.get("metadata", {})
    stage2_components = (
        int(snapshot_meta.get("source_component_count", 0))
        if isinstance(snapshot_meta, dict)
        else 0
    )

    serve_snapshot = str(cfg.current_snapshot_path)
    snapshot_mismatch_vs_cache_dir = not serve_snapshot.startswith(str(cache_dir))

    return {
        "cache_dir": str(cache_dir),
        "stage1": {
            "state_db": str(state_db),
            "state_counts": state_counts,
            "total_parts_seen": total_parts_seen,
            "success_rate_pct": success_rate_pct,
            "manifest_db": str(manifest_db),
            "manifest_artifact_count": manifest_total,
            "assets_by_type": assets_by_type,
        },
        "stage2": {
            "snapshot_root": str(snapshot_root),
            "current": current_snapshot,
        },
        "serve": {
            "status": "online",
            "snapshot": serve_snapshot,
            "fast_db": str(cfg.fast_db_path),
            "detail_db": str(cfg.detail_db_path),
            "snapshot_mismatch_vs_cache_dir": snapshot_mismatch_vs_cache_dir,
        },
        "flow": {
            "stage1_success_parts": success,
            "stage1_failed_parts": failed,
            "stage2_component_count": stage2_components,
            "serve_snapshot_mismatch": snapshot_mismatch_vs_cache_dir,
        },
    }


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
    payload["pipeline_status"] = _collect_pipeline_status(request)
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


def test_collect_pipeline_status_includes_assets_and_flow(tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    state_db = cache_dir / "fetch" / "roundtrip_state.sqlite3"
    manifest_db = cache_dir / "fetch" / "manifest.sqlite3"
    snap = cache_dir / "snapshots" / "s1"
    current = cache_dir / "snapshots" / "current"
    state_db.parent.mkdir(parents=True, exist_ok=True)
    manifest_db.parent.mkdir(parents=True, exist_ok=True)
    snap.mkdir(parents=True, exist_ok=True)
    current.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(state_db) as conn:
        conn.execute(
            "create table roundtrip_part_state (lcsc_id integer primary key, status text not null)"
        )
        conn.executemany(
            "insert into roundtrip_part_state(lcsc_id,status) values (?,?)",
            [(1, "success"), (2, "success"), (3, "failed"), (4, "running")],
        )
    with sqlite3.connect(manifest_db) as conn:
        conn.execute(
            """
            create table fetch_manifest (
              id integer primary key autoincrement,
              lcsc_id integer not null,
              artifact_type text not null
            )
            """
        )
        conn.executemany(
            "insert into fetch_manifest(lcsc_id,artifact_type) values (?,?)",
            [(1, "model_step"), (1, "model_glb"), (2, "model_step"), (2, "part_image")],
        )
    (snap / "metadata.json").write_text(
        json.dumps({"snapshot_name": "s1", "source_component_count": 2}),
        encoding="utf-8",
    )
    current.symlink_to(snap, target_is_directory=True)

    class _Cfg:
        def __init__(self):
            self.cache_dir = cache_dir
            self.current_snapshot_path = cache_dir / "current"
            self.fast_db_path = cache_dir / "current" / "fast.sqlite"
            self.detail_db_path = cache_dir / "current" / "detail.sqlite"

    class _State:
        def __init__(self):
            self.components_config = _Cfg()

    class _App:
        def __init__(self):
            self.state = _State()

    class _Req:
        def __init__(self):
            self.app = _App()

    status = _collect_pipeline_status(_Req())
    assert status["stage1"]["total_parts_seen"] == 4
    assert status["stage1"]["manifest_artifact_count"] == 4
    assert status["flow"]["stage2_component_count"] == 2
    assert status["stage1"]["assets_by_type"][0]["artifact_count"] >= 1
