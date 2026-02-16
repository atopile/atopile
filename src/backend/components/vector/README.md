# Vector Search Prototype (Sidebar)

CPU-first prototype for validating hybrid-ready vector retrieval on top of
`detail.sqlite` (`components_full`) before wiring into stage-3 serve.

## Scope

- Export component rows into a canonical JSONL corpus.
- Build vector index using:
  - `hashing` backend (dependency-free baseline)
  - `sentence-transformers` backend (optional, higher quality)
  - optional HNSW ANN candidate index (`hnswlib`) for low-latency retrieval
- Query with metadata filters + lightweight reranking.
- Evaluate with labeled query sets (`hit@k`, `MRR`, `p50/p95 latency`).

## Quick Start From `/home/jlc` (Balanced 10k, Raw Vector)

```bash
cd /home/np/projects/atopile_vector_db
export PYTHONPATH=/home/np/projects/atopile_vector_db/src

# 1) Export balanced stage-1 corpus with progress logs, capped to 32 cores
uv run python -m backend.components.vector.cli --max-cores 32 export-balanced-stage1 \
  --cache-sqlite /home/jlc/cache.sqlite3 \
  --out-jsonl /tmp/vector_proto/corpus_10k.jsonl \
  --target-count 10000 \
  --per-subcategory-cap 600

# 2) Build local vector index (baseline hashing embedder)
uv run python -m backend.components.vector.cli --max-cores 32 build-index \
  --corpus-jsonl /tmp/vector_proto/corpus_10k.jsonl \
  --out-dir /tmp/vector_proto/index_hashing_10k \
  --embedding-backend hashing \
  --embedding-dim 384 \
  --ann-backend auto

# 3) Interactive query (raw vector only by default)
uv run python -m backend.components.vector.cli --max-cores 32 query \
  --index-dir /tmp/vector_proto/index_hashing_10k \
  --query "10k 1% 0402 resistor pull-up" \
  --limit 20 \
  --embedding-backend hashing \
  --embedding-dim 384 \
  --prefer-in-stock \
  --prefer-basic

# 4) Run eval and write report
uv run python -m backend.components.vector.cli --max-cores 32 eval \
  --index-dir /tmp/vector_proto/index_hashing_10k \
  --queries-jsonl src/backend/components/vector/sample_eval_queries.jsonl \
  --out-report /tmp/vector_proto/eval_hashing_10k.json \
  --embedding-backend hashing \
  --embedding-dim 384 \
  --prefer-in-stock \
  --prefer-basic
```

## Optional: Link Existing Commands To `/home/jlc/cache.sqlite3`

If you want to keep using the older `.../.cache/jlcparts_playground/raw/cache.sqlite3`
path from existing notes/scripts:

```bash
mkdir -p src/backend/components/.cache/jlcparts_playground/raw
ln -sfn /home/jlc/cache.sqlite3 src/backend/components/.cache/jlcparts_playground/raw/cache.sqlite3
```

## Prototype `/v1/components/search` Endpoint

Point serve at the built index:

```bash
export ATOPILE_COMPONENTS_VECTOR_INDEX_DIR=/tmp/vector_proto/index_hashing_10k_balanced
export ATOPILE_COMPONENTS_VECTOR_MAX_CORES=32
```

Raw vector search (default mode):

```bash
curl -sS http://127.0.0.1:8079/v1/components/search \
  -H 'content-type: application/json' \
  -d '{
    "query":"battery friendly 3.3V regulator for MCU",
    "limit":20,
    "raw_vector_only":true,
    "in_stock_only":true
  }'
```

Hybrid mode (recommended for sidebar UX):

```bash
curl -sS http://127.0.0.1:8079/v1/components/search \
  -H 'content-type: application/json' \
  -d '{
    "query":"pressure sensor",
    "limit":20,
    "search_mode":"hybrid",
    "in_stock_only":true
  }'
```

## Optional Semantic Embeddings

If you install `sentence-transformers`, switch backend:

```bash
uv run python -m backend.components.vector.cli build-index \
  --corpus-jsonl /tmp/vector_proto/corpus_10k.jsonl \
  --out-dir /tmp/vector_proto/index_minilm_10k \
  --embedding-backend sentence-transformers \
  --model-name sentence-transformers/all-MiniLM-L6-v2
```

Use the same backend/model at query and eval time.

If you install `hnswlib`, `build-index --ann-backend auto` will emit
`ann_hnsw.bin` and search will automatically use ANN candidates with fallback
to brute-force when unavailable.

## Eval Query Format

JSONL, one object per line:

```json
{"query":"C123456","expected_lcsc_ids":[123456],"filters":{"in_stock_only":true}}
{"query":"RC0402FR-0710KL","expected_lcsc_ids":[123456],"filters":{"component_type":"resistor"}}
```

## Notes

- This prototype is intentionally standalone; it does not change stage-3 APIs.
- For strict IDs/MPNs, search includes explicit exact-match boosts.
- Next step after confidence: replace prototype search with a serve endpoint and
  a true ANN backend (Qdrant/HNSW) at larger scales.
