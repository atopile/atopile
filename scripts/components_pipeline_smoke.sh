#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv/bin/python}"
CFG_PATH="${1:-$REPO_ROOT/components-pipeline.toml}"
SMOKE_SNAPSHOT="smoke-$(date -u '+%Y%m%dT%H%M%SZ')"

echo "[smoke] validate config"
"$PYTHON_BIN" "$REPO_ROOT/scripts/components_pipeline_apply.py" --config "$CFG_PATH" --validate

echo "[smoke] stage2 build (partial)"
ATOPILE_COMPONENTS_SNAPSHOT_NAME="$SMOKE_SNAPSHOT" \
"$PYTHON_BIN" -m backend.components.transform.build_snapshot \
  --source-sqlite "${ATOPILE_COMPONENTS_SOURCE_SQLITE:-/home/jlc/cache.sqlite3}" \
  --snapshot-name "$SMOKE_SNAPSHOT" \
  --max-components "${ATOPILE_COMPONENTS_SMOKE_MAX_COMPONENTS:-500}"

echo "[smoke] publish snapshot"
"$PYTHON_BIN" -m backend.components.transform.publish_snapshot \
  "$SMOKE_SNAPSHOT" \
  --keep-snapshots "${ATOPILE_COMPONENTS_KEEP_SNAPSHOTS:-2}" \
  --allow-partial

echo "[smoke] status"
"$PYTHON_BIN" "$REPO_ROOT/scripts/components_pipeline_status.py"

echo "[smoke] done snapshot=$SMOKE_SNAPSHOT"
