#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
PYTHONPATH_DIR="$REPO_ROOT/src"
RUNNER="$REPO_ROOT/scripts/run_stage1_fetch_all_from_cache.py"

SOURCE_SQLITE="${SOURCE_SQLITE:-/home/jlc/cache.sqlite3}"
CACHE_DIR="${ATOPILE_COMPONENTS_CACHE_DIR:-/home/jlc/stage1_fetch}"
CHUNK_SIZE="${ATOPILE_COMPONENTS_CHUNK_SIZE:-50000}"
WORKERS="${ATOPILE_COMPONENTS_ROUNDTRIP_WORKERS:-32}"
RETRY_ATTEMPTS="${ATOPILE_COMPONENTS_ROUNDTRIP_RETRY_ATTEMPTS:-3}"
RETRY_BACKOFF_S="${ATOPILE_COMPONENTS_ROUNDTRIP_RETRY_BACKOFF_S:-2.0}"
WHERE_CLAUSE="${ATOPILE_COMPONENTS_WHERE:-stock > 0}"
LOG_PATH="${ATOPILE_COMPONENTS_LOG_PATH:-/tmp/stage1_fetch_all.log}"

echo "source_sqlite=$SOURCE_SQLITE"
echo "cache_dir=$CACHE_DIR"
echo "chunk_size=$CHUNK_SIZE workers=$WORKERS"
echo "log_path=$LOG_PATH"

nohup sudo env \
  PYTHONPATH="$PYTHONPATH_DIR" \
  "$PYTHON_BIN" -u "$RUNNER" \
  --source-sqlite "$SOURCE_SQLITE" \
  --cache-dir "$CACHE_DIR" \
  --chunk-size "$CHUNK_SIZE" \
  --workers "$WORKERS" \
  --retry-attempts "$RETRY_ATTEMPTS" \
  --retry-backoff-s "$RETRY_BACKOFF_S" \
  --where "$WHERE_CLAUSE" \
  >"$LOG_PATH" 2>&1 < /dev/null &

echo "pid=$!"
echo "tail -f $LOG_PATH"
