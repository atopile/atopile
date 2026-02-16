#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv/bin/python}"
PYTHONPATH_DIR="${PYTHONPATH_DIR:-$REPO_ROOT/src}"

CACHE_DIR="${ATOPILE_COMPONENTS_CACHE_DIR:-/home/jlc/stage1_fetch}"
SNAPSHOT_NAME="${ATOPILE_COMPONENTS_SNAPSHOT_NAME:-$(date -u '+%Y%m%dT%H%M%SZ')}"
KEEP_SNAPSHOTS="${ATOPILE_COMPONENTS_KEEP_SNAPSHOTS:-2}"
ALLOW_PARTIAL="${ATOPILE_COMPONENTS_ALLOW_PARTIAL:-0}"

usage() {
  cat <<'EOF'
Usage:
  scripts/components_pipeline.sh <command> [args]

Commands:
  stage1-all
    Start the stage1 all-from-cache fetch runner in background.

  stage2-build [--max-components N]
    Build a stage2 snapshot from configured source sqlite + stage1 manifest.

  stage2-publish <snapshot-name>
    Publish a built snapshot atomically to snapshots/current.

  processor-once [--max-components N]
    Run stage2-build then stage2-publish for one cycle.

  serve
    Start components serve API in foreground.

  all-in-one-once [--max-components N]
    Start stage1-all and run processor-once.

Notes:
  - This wrapper is deployment-role oriented:
      * processor host: stage1-all + processor-once
      * serve host(s): serve
      * single host: all-in-one-once
  - Reads env defaults from existing fetch/transform/serve config.
EOF
}

run_stage1_all() {
  "$REPO_ROOT/scripts/run_stage1_fetch_all.sh"
}

run_stage2_build() {
  local max_components="${1:-}"
  local extra_args=()
  if [[ -n "$max_components" ]]; then
    extra_args+=(--max-components "$max_components")
  fi
  echo "stage2 build: snapshot_name=$SNAPSHOT_NAME cache_dir=$CACHE_DIR"
  env \
    PYTHONPATH="$PYTHONPATH_DIR" \
    ATOPILE_COMPONENTS_CACHE_DIR="$CACHE_DIR" \
    ATOPILE_COMPONENTS_SNAPSHOT_NAME="$SNAPSHOT_NAME" \
    "$PYTHON_BIN" -m backend.components.transform.build_snapshot \
    "${extra_args[@]}"
}

run_stage2_publish() {
  local snapshot_name="$1"
  local extra_args=()
  if [[ "$ALLOW_PARTIAL" == "1" ]]; then
    extra_args+=(--allow-partial)
  fi
  echo "stage2 publish: snapshot_name=$snapshot_name keep=$KEEP_SNAPSHOTS"
  env \
    PYTHONPATH="$PYTHONPATH_DIR" \
    ATOPILE_COMPONENTS_CACHE_DIR="$CACHE_DIR" \
    "$PYTHON_BIN" -m backend.components.transform.publish_snapshot \
    "$snapshot_name" \
    --keep-snapshots "$KEEP_SNAPSHOTS" \
    "${extra_args[@]}"
}

run_serve() {
  echo "serve start: cache_dir=$CACHE_DIR"
  env \
    PYTHONPATH="$PYTHONPATH_DIR" \
    ATOPILE_COMPONENTS_CACHE_DIR="$CACHE_DIR" \
    "$PYTHON_BIN" -m backend.components.serve.main
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

cmd="$1"
shift || true

case "$cmd" in
  stage1-all)
    run_stage1_all
    ;;
  stage2-build)
    max=""
    if [[ "${1:-}" == "--max-components" ]]; then
      max="${2:-}"
      if [[ -z "$max" ]]; then
        echo "Missing value for --max-components"
        exit 1
      fi
    fi
    run_stage2_build "$max"
    ;;
  stage2-publish)
    if [[ $# -lt 1 ]]; then
      echo "stage2-publish requires <snapshot-name>"
      exit 1
    fi
    run_stage2_publish "$1"
    ;;
  processor-once)
    max=""
    if [[ "${1:-}" == "--max-components" ]]; then
      max="${2:-}"
      if [[ -z "$max" ]]; then
        echo "Missing value for --max-components"
        exit 1
      fi
    fi
    run_stage2_build "$max"
    run_stage2_publish "$SNAPSHOT_NAME"
    ;;
  serve)
    run_serve
    ;;
  all-in-one-once)
    max=""
    if [[ "${1:-}" == "--max-components" ]]; then
      max="${2:-}"
      if [[ -z "$max" ]]; then
        echo "Missing value for --max-components"
        exit 1
      fi
    fi
    run_stage1_all
    run_stage2_build "$max"
    run_stage2_publish "$SNAPSHOT_NAME"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "Unknown command: $cmd"
    usage
    exit 1
    ;;
esac
