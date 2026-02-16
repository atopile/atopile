#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="/tmp/vector_proto/build_bge_small_all.log"
RECORDS_FILE="/tmp/vector_proto/index_bge_small_all_parts/records.jsonl"
PID_FILE="/tmp/vector_proto/build_bge_small_all.pid"
TOTAL=6752713
INTERVAL=2

if command -v tput >/dev/null 2>&1; then
  clear_cmd='tput clear'
else
  clear_cmd='clear'
fi

start_ts=$(date +%s)
prev_ts=$start_ts
prev_rows=0

count_rows() {
  if [[ -f "$RECORDS_FILE" ]]; then
    wc -l < "$RECORDS_FILE"
  else
    echo 0
  fi
}

last_log_line() {
  if [[ -f "$LOG_FILE" ]]; then
    tail -n 1 "$LOG_FILE"
  else
    echo "(log not created yet)"
  fi
}

while true; do
  now=$(date +%s)
  rows=$(count_rows)
  elapsed=$((now - start_ts))
  dt=$((now - prev_ts))
  dr=$((rows - prev_rows))

  if (( dt > 0 )); then
    inst_rate=$(awk -v dr="$dr" -v dt="$dt" 'BEGIN { printf "%.1f", (dr<0?0:dr)/dt }')
  else
    inst_rate="0.0"
  fi

  if (( elapsed > 0 )); then
    avg_rate=$(awk -v rows="$rows" -v e="$elapsed" 'BEGIN { printf "%.1f", rows/e }')
  else
    avg_rate="0.0"
  fi

  pct=$(awk -v r="$rows" -v t="$TOTAL" 'BEGIN { if (t<=0) printf "0.00"; else printf "%.2f", (100.0*r)/t }')

  if (( rows > 0 )); then
    eta_sec=$(awk -v r="$rows" -v t="$TOTAL" -v e="$elapsed" 'BEGIN { rem=t-r; if (e<=0 || r<=0 || rem<=0) print 0; else printf "%.0f", rem/(r/e) }')
  else
    eta_sec=0
  fi

  eta_h=$((eta_sec / 3600))
  eta_m=$(((eta_sec % 3600) / 60))
  eta_s=$((eta_sec % 60))

  running="no"
  pid="-"
  if [[ -f "$PID_FILE" ]]; then
    pid=$(cat "$PID_FILE" 2>/dev/null || echo "-")
    if [[ -n "$pid" ]] && ps -p "$pid" >/dev/null 2>&1; then
      running="yes"
    fi
  fi

  eval "$clear_cmd"
  echo "Full Index Monitor"
  echo "time:      $(date '+%Y-%m-%d %H:%M:%S')"
  echo "running:   $running (pid: $pid)"
  echo "rows:      $rows / $TOTAL"
  echo "progress:  ${pct}%"
  echo "rate:      ${inst_rate} rows/s (inst), ${avg_rate} rows/s (avg)"
  echo "elapsed:   ${elapsed}s"
  if (( rows > 0 )); then
    printf 'eta:       %02dh:%02dm:%02ds\n' "$eta_h" "$eta_m" "$eta_s"
  else
    echo "eta:       --"
  fi
  echo "log:       $(last_log_line)"
  echo
  echo "Ctrl+C to exit monitor"

  if [[ "$running" != "yes" ]] && (( rows > 0 )); then
    echo
    echo "Process no longer running; monitor exiting."
    exit 0
  fi

  prev_ts=$now
  prev_rows=$rows
  sleep "$INTERVAL"
done
