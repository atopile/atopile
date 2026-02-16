#!/usr/bin/env bash
set -euo pipefail

CACHE_DIR="${ATOPILE_COMPONENTS_CACHE_DIR:-/var/cache/atopile/components}"
SNAPSHOT_KEEP_DAYS="${ATOPILE_COMPONENTS_CLEANUP_SNAPSHOT_DAYS:-14}"
SEED_KEEP_DAYS="${ATOPILE_COMPONENTS_CLEANUP_SEED_DAYS:-7}"

echo "cache_dir=$CACHE_DIR"
echo "snapshot_keep_days=$SNAPSHOT_KEEP_DAYS"
echo "seed_keep_days=$SEED_KEEP_DAYS"

SNAP_ROOT="$CACHE_DIR/snapshots"
SEED_ROOT="$CACHE_DIR/fetch/jlc_api"

if [[ -d "$SEED_ROOT" ]]; then
  find "$SEED_ROOT" -mindepth 1 -maxdepth 1 -type d -name 'seed-cache-*' \
    -mtime +"$SEED_KEEP_DAYS" -print -exec rm -rf {} +
fi

if [[ -d "$SNAP_ROOT" ]]; then
  find "$SNAP_ROOT" -mindepth 1 -maxdepth 1 -type d \
    ! -name current ! -name previous \
    -mtime +"$SNAPSHOT_KEEP_DAYS" -print -exec rm -rf {} +
fi

find "$CACHE_DIR" -type f -name '*.tmp' -print -delete
find "$CACHE_DIR" -type f -name '*.zst.tmp' -print -delete

echo "cleanup_done=true"
