#!/usr/bin/env bash
set -euo pipefail

pkill -f 'vector_proto\.cli --max-cores 32 build-index --corpus-jsonl /tmp/vector_proto/corpus_all_stage1\.jsonl' >/dev/null 2>&1 || true

export PYTHONPATH=/home/np/projects/atopile_vector_db/src
export PYTHONUNBUFFERED=1

setsid /bin/bash -lc "exec uv run python -m backend.components.research.vector_proto.cli --max-cores 32 build-index --corpus-jsonl /tmp/vector_proto/corpus_all_stage1.jsonl --out-dir /tmp/vector_proto/index_bge_small_all_parts --embedding-backend sentence-transformers --model-name BAAI/bge-small-en-v1.5 --batch-size 1024 > /tmp/vector_proto/build_bge_small_all.log 2>&1" >/tmp/vector_proto/build_bge_small_all.launch.log 2>&1 < /dev/null & echo $! > /tmp/vector_proto/build_bge_small_all.pid
