#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
PYTHONPATH_DIR="$REPO_ROOT/src"

CACHE_DIR="${ATOPILE_COMPONENTS_CACHE_DIR:-/home/jlc/stage1_fetch}"
WORKERS="${ATOPILE_COMPONENTS_ROUNDTRIP_WORKERS:-8}"
RETRY_ATTEMPTS="${ATOPILE_COMPONENTS_ROUNDTRIP_RETRY_ATTEMPTS:-3}"
RETRY_BACKOFF="${ATOPILE_COMPONENTS_ROUNDTRIP_RETRY_BACKOFF_S:-2.0}"
STATUS_INTERVAL_S="${ATOPILE_COMPONENTS_STATUS_INTERVAL_S:-10}"
STATE_DB="$CACHE_DIR/fetch/roundtrip_state.sqlite3"
MANIFEST_DB="$CACHE_DIR/fetch/manifest.sqlite3"

SNAPSHOT_DIR="${1:-}"
if [[ -z "$SNAPSHOT_DIR" ]]; then
  SNAPSHOT_DIR="$(ls -1dt "$CACHE_DIR"/fetch/jlc_api/* 2>/dev/null | head -n1 || true)"
fi

if [[ -z "$SNAPSHOT_DIR" || ! -d "$SNAPSHOT_DIR" ]]; then
  echo "No valid snapshot directory found."
  echo "Pass one as first arg, e.g."
  echo "  $0 /home/jlc/stage1_fetch/fetch/jlc_api/seed-from-cache-YYYYMMDDTHHMMSSZ"
  exit 1
fi

echo "Using cache dir: $CACHE_DIR"
echo "Using snapshot: $SNAPSHOT_DIR"
echo "Workers: $WORKERS"
echo "Status interval: ${STATUS_INTERVAL_S}s"
echo "State DB: $STATE_DB"

sudo env \
  PYTHONPATH="$PYTHONPATH_DIR" \
  ATOPILE_COMPONENTS_CACHE_DIR="$CACHE_DIR" \
  "$PYTHON_BIN" -m backend.components.fetch.jobs.fetch_daily \
  --skip-jlc-list \
  --roundtrip-from-snapshot \
  --snapshot-dir "$SNAPSHOT_DIR" \
  --roundtrip-workers "$WORKERS" \
  --roundtrip-retry-attempts "$RETRY_ATTEMPTS" \
  --roundtrip-retry-backoff-s "$RETRY_BACKOFF" &

JOB_PID=$!

while kill -0 "$JOB_PID" 2>/dev/null; do
  TS="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  sudo "$PYTHON_BIN" - <<PY
import sqlite3
from pathlib import Path

state_db = Path("$STATE_DB")
manifest_db = Path("$MANIFEST_DB")
summary = {"success": 0, "failed": 0, "running": 0, "total": 0, "artifacts": 0}

if state_db.exists():
    conn = sqlite3.connect(state_db)
    rows = conn.execute(
        "select status, count(*) from roundtrip_part_state group by status"
    ).fetchall()
    conn.close()
    for status, count in rows:
        summary[str(status)] = int(count)
    summary["total"] = sum(summary.get(k, 0) for k in ("success", "failed", "running"))

if manifest_db.exists():
    conn = sqlite3.connect(manifest_db)
    summary["artifacts"] = conn.execute(
        "select count(*) from fetch_manifest"
    ).fetchone()[0]
    conn.close()

print(
    f"[$TS] total={summary['total']} "
    f"success={summary['success']} failed={summary['failed']} "
    f"running={summary['running']} artifacts={summary['artifacts']}"
)
PY
  sleep "$STATUS_INTERVAL_S"
done

wait "$JOB_PID"
