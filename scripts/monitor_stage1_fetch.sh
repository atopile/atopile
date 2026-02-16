#!/usr/bin/env bash
set -u

CACHE_DIR="${ATOPILE_COMPONENTS_CACHE_DIR:-/home/jlc/stage1_fetch}"
PYTHON_BIN="${PYTHON_BIN:-/home/np/projects/atopile_parts_backend/.venv/bin/python}"
INITIAL_DELAY_S="${ATOPILE_COMPONENTS_MONITOR_INITIAL_DELAY_S:-3600}"
INTERVAL_S="${ATOPILE_COMPONENTS_MONITOR_INTERVAL_S:-3600}"

STATE_DB="$CACHE_DIR/fetch/roundtrip_state.sqlite3"
MANIFEST_DB="$CACHE_DIR/fetch/manifest.sqlite3"

if [[ "$INITIAL_DELAY_S" -gt 0 ]]; then
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] initial_delay_s=$INITIAL_DELAY_S"
  sleep "$INITIAL_DELAY_S"
fi

prev_success=-1
prev_artifacts=-1
stagnant_intervals=0

while true; do
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  line="$(
    sudo "$PYTHON_BIN" - <<PY
import sqlite3
from pathlib import Path

state_db = Path("$STATE_DB")
manifest_db = Path("$MANIFEST_DB")

success = failed = running = parts = artifacts = 0

if state_db.exists():
    conn = sqlite3.connect(state_db)
    rows = conn.execute(
        "select status, count(*) from roundtrip_part_state group by status"
    ).fetchall()
    conn.close()
    for status, count in rows:
        if status == "success":
            success = int(count)
        elif status == "failed":
            failed = int(count)
        elif status == "running":
            running = int(count)
    parts = success + failed + running

if manifest_db.exists():
    conn = sqlite3.connect(manifest_db)
    artifacts = int(conn.execute("select count(*) from fetch_manifest").fetchone()[0])
    conn.close()

print(
    f"success={success} failed={failed} running={running} parts={parts} artifacts={artifacts}"
)
PY
  )"

  eval "$line"
  echo "[$ts] $line"

  if [[ "$prev_success" -ge 0 ]]; then
    d_success=$((success - prev_success))
    d_artifacts=$((artifacts - prev_artifacts))
    if [[ "$d_success" -gt 0 || "$d_artifacts" -gt 0 ]]; then
      stagnant_intervals=0
      echo "[$ts] status=good delta_success=$d_success delta_artifacts=$d_artifacts timer_reset=true"
    else
      stagnant_intervals=$((stagnant_intervals + 1))
      echo "[$ts] status=stalled stagnant_intervals=$stagnant_intervals"
    fi
  fi

  prev_success="$success"
  prev_artifacts="$artifacts"
  sleep "$INTERVAL_S"
done
