#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _read_state_counts(state_db: Path) -> dict[str, int]:
    if not state_db.exists():
        return {}
    out: dict[str, int] = {}
    with sqlite3.connect(state_db) as conn:
        rows = conn.execute(
            "select status, count(*) from roundtrip_part_state group by status"
        ).fetchall()
    for status, count in rows:
        out[str(status)] = int(count)
    return out


def _read_manifest_count(manifest_db: Path) -> int | None:
    if not manifest_db.exists():
        return None
    with sqlite3.connect(manifest_db) as conn:
        return int(conn.execute("select count(*) from fetch_manifest").fetchone()[0])


def _read_current_snapshot(snapshot_root: Path) -> dict[str, Any]:
    current = snapshot_root / "current"
    if not (current.exists() or current.is_symlink()):
        return {}
    resolved = current.resolve(strict=False)
    metadata_path = resolved / "metadata.json"
    metadata: dict[str, Any] = {}
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception:
            metadata = {}
    return {
        "current_link": str(current),
        "resolved_snapshot": str(resolved),
        "metadata": metadata,
    }


def _read_serve_health(health_url: str, timeout_s: float) -> dict[str, Any]:
    req = urllib.request.Request(health_url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(body)
            return {
                "ok": True,
                "status_code": int(resp.status),
                "payload": payload if isinstance(payload, dict) else {"raw": body},
            }
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status_code": int(exc.code), "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> int:
    cache_dir = Path(os.getenv("ATOPILE_COMPONENTS_CACHE_DIR", "/home/jlc/stage1_fetch"))
    serve_health_url = os.getenv(
        "ATOPILE_COMPONENTS_SERVE_HEALTH_URL",
        "http://127.0.0.1:8079/healthz",
    )
    serve_health_timeout_s = float(
        os.getenv("ATOPILE_COMPONENTS_SERVE_HEALTH_TIMEOUT_S", "1.5")
    )

    state_db = cache_dir / "fetch" / "roundtrip_state.sqlite3"
    manifest_db = cache_dir / "fetch" / "manifest.sqlite3"
    snapshot_root = cache_dir / "snapshots"

    state_counts = _read_state_counts(state_db)
    success = state_counts.get("success", 0)
    failed = state_counts.get("failed", 0)
    running = state_counts.get("running", 0)
    total = success + failed + running
    pct_success = round((100.0 * success / total), 3) if total else None

    out = {
        "cache_dir": str(cache_dir),
        "stage1": {
            "state_db": str(state_db),
            "state_counts": state_counts,
            "total_parts_seen": total,
            "success_rate_pct": pct_success,
            "manifest_db": str(manifest_db),
            "manifest_artifact_count": _read_manifest_count(manifest_db),
        },
        "stage2": {
            "snapshot_root": str(snapshot_root),
            "current": _read_current_snapshot(snapshot_root),
        },
        "serve": {
            "health_url": serve_health_url,
            "health": _read_serve_health(serve_health_url, serve_health_timeout_s),
        },
    }
    serve_payload = out["serve"]["health"].get("payload", {})
    serve_snapshot = (
        serve_payload.get("snapshot")
        if isinstance(serve_payload, dict)
        else None
    )
    if isinstance(serve_snapshot, str):
        out["serve"]["snapshot_mismatch_vs_cache_dir"] = not serve_snapshot.startswith(
            str(cache_dir)
        )
    print(json.dumps(out, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
