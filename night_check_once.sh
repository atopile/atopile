#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/np/projects/atopile_vector_db"
INDEX_DIR="/tmp/vector_proto/index_bge_small_all_parts"
PID_FILE="/tmp/vector_proto/build_bge_small_all.pid"
WATCH_LOG="/tmp/vector_proto/night_watch_full_index.log"
READY_FILE="/tmp/vector_proto/index_bge_small_all_parts.READY"
EVAL_REPORT="/tmp/vector_proto/eval_bge_small_allparts_sample.json"
TOTAL_ROWS=6752713

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$WATCH_LOG"
}

is_running() {
  [[ -f "$PID_FILE" ]] || return 1
  local pid
  pid=$(cat "$PID_FILE" 2>/dev/null || true)
  [[ -n "$pid" ]] || return 1
  ps -p "$pid" >/dev/null 2>&1
}

records_count() {
  if [[ -f "$INDEX_DIR/records.jsonl" ]]; then
    wc -l < "$INDEX_DIR/records.jsonl"
  else
    echo 0
  fi
}

is_complete() {
  [[ -f "$INDEX_DIR/manifest.json" ]] || return 1
  local corpus_size
  corpus_size=$(python - <<'PY'
import json
from pathlib import Path
p = Path('/tmp/vector_proto/index_bge_small_all_parts/manifest.json')
try:
    m = json.loads(p.read_text(encoding='utf-8'))
    print(int(m.get('corpus_size', -1)))
except Exception:
    print(-1)
PY
)
  [[ "$corpus_size" -eq "$TOTAL_ROWS" ]]
}

schedule_next_hour() {
  echo "/home/np/projects/atopile_vector_db/night_check_once.sh" | at now + 1 hour >> "$WATCH_LOG" 2>&1
}

run_post_eval() {
  log "build complete; starting eval + smoke queries"
  cd "$ROOT"
  export PYTHONPATH="$ROOT/src"

  uv run python -m backend.components.research.vector_proto.cli --max-cores 32 eval \
    --index-dir "$INDEX_DIR" \
    --queries-jsonl src/backend/components/research/vector_proto/sample_eval_queries.jsonl \
    --out-report "$EVAL_REPORT" \
    --embedding-backend sentence-transformers \
    --model-name BAAI/bge-small-en-v1.5 \
    --prefer-in-stock \
    --prefer-basic >> "$WATCH_LOG" 2>&1

  uv run python -m backend.components.research.vector_proto.cli query \
    --index-dir "$INDEX_DIR" \
    --embedding-backend sentence-transformers \
    --model-name BAAI/bge-small-en-v1.5 \
    --query 'pressure sensor' \
    --limit 10 \
    --enable-rerank > /tmp/vector_proto/smoke_pressure_sensor.json 2>> "$WATCH_LOG"

  uv run python -m backend.components.research.vector_proto.cli query \
    --index-dir "$INDEX_DIR" \
    --embedding-backend sentence-transformers \
    --model-name BAAI/bge-small-en-v1.5 \
    --query 'battery friendly 3.3V regulator for MCU' \
    --limit 10 \
    --enable-rerank > /tmp/vector_proto/smoke_ldo_mcu.json 2>> "$WATCH_LOG"

  uv run python -m backend.components.research.vector_proto.cli query \
    --index-dir "$INDEX_DIR" \
    --embedding-backend sentence-transformers \
    --model-name BAAI/bge-small-en-v1.5 \
    --query 'CAN transceiver automotive' \
    --limit 10 \
    --enable-rerank > /tmp/vector_proto/smoke_can_auto.json 2>> "$WATCH_LOG"

  {
    echo "ready_at=$(date '+%Y-%m-%d %H:%M:%S')"
    echo "index_dir=$INDEX_DIR"
    echo "eval_report=$EVAL_REPORT"
    echo "smoke_pressure_sensor=/tmp/vector_proto/smoke_pressure_sensor.json"
    echo "smoke_ldo_mcu=/tmp/vector_proto/smoke_ldo_mcu.json"
    echo "smoke_can_auto=/tmp/vector_proto/smoke_can_auto.json"
  } > "$READY_FILE"

  log "done; readiness file written: $READY_FILE"
}

mkdir -p /tmp/vector_proto
: > "$WATCH_LOG"
rows=$(records_count)

if is_complete; then
  log "index already complete (rows=$rows)"
  run_post_eval
  exit 0
fi

if is_running; then
  log "index running (rows=$rows); scheduling next hourly check"
  schedule_next_hour
  exit 0
fi

log "index not running (rows=$rows); restarting and scheduling next check"
cd "$ROOT"
./run_full_index.sh >> "$WATCH_LOG" 2>&1
schedule_next_hour
