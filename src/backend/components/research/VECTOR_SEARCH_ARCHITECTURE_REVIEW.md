# Vector Search Architecture Review (Fetch/Transform/Serve)

## Goals

1. Keep sidebar search fast and high-quality for natural language queries.
2. Integrate vector search cleanly into the existing 3-stage backend.
3. Avoid unnecessary model downloads (especially not on daily fetch cadence).
4. Make runtime behavior deterministic, observable, and production-friendly.

---

## Current State (As Implemented)

### Stage 1 (`fetch`)

- Fetch jobs ingest and cache raw artifacts + manifest (`fetch_manifest`).
- No vector-specific stage-1 responsibilities today.
- This is good: stage-1 should remain raw ingestion only.

### Stage 2 (`transform`)

- Builds immutable snapshot directories with:
  - `fast.sqlite` (parametric lookup tables)
  - `detail.sqlite` (`components_full`, `component_assets`)
- Snapshot publish uses atomic `current` symlink cutover.
- Vector index build currently lives in `research/vector_proto` and is external to snapshot build/publish.

### Stage 3 (`serve`)

- `serve.main` loads fast/detail stores from `snapshots/current`.
- Vector search is optional via `ATOPILE_COMPONENTS_VECTOR_INDEX_DIR`.
- Current vector implementation is functional, with recent startup improvements:
  - lazy model load
  - lazy lexical index build
  - vector mmap loading

---

## Primary Gaps

1. Vector index lifecycle is not coupled to snapshot lifecycle.
2. No canonical model/version policy for embedding generation and query encoding.
3. Runtime may trigger model downloads depending on environment cache state.
4. No strict compatibility check between snapshot schema and vector index schema.
5. Vector path is still Python-prototype runtime (good for experimentation, not final serving engine).

---

## Recommended Target Architecture

## Stage 1: Keep Raw

No vector embedding/model logic in stage-1.

Stage-1 should only provide source-of-truth raw component data and artifacts used by stage-2.

## Stage 2: Make Vector a First-Class Snapshot Artifact

Extend stage-2 pipeline to produce:

- `snapshot/<name>/fast.sqlite`
- `snapshot/<name>/detail.sqlite`
- `snapshot/<name>/vector/` (new)
  - `manifest.json`
  - vector matrix/index files
  - metadata/filter indexes needed by runtime

Then publish all of the above atomically with `current`.

### Why this matters

- Guarantees vector index and SQL snapshot are consistent.
- Rollbacks become clean (`previous` includes matching vector state).
- Eliminates ad hoc `/tmp` index directories in production.

## Stage 3: Serve From `current` Snapshot Only

Serve should resolve vector index from:

- `current/vector` by default
- explicit override only for dev experiments

Startup should fail fast if:

- vector is configured but missing/incompatible
- snapshot/index manifest versions mismatch

---

## Model Lifecycle Policy (Important)

## Principle

Do **not** fetch "latest" model automatically in daily jobs.

## Policy

1. Pin model by immutable ID + revision/digest:
   - example: `BAAI/bge-small-en-v1.5@<commit-or-digest>`
2. Record this in vector manifest:
   - `embedding_backend`
   - `model_id`
   - `model_revision`
   - `embedding_dim`
3. Stage-2 vector build uses only pinned model config.
4. Runtime uses same pinned model metadata for query encoding.
5. New model rollout is explicit:
   - update config
   - rebuild snapshot+vector
   - validate/eval
   - publish

## Practical download strategy

- Prefer pre-baking model weights in image/artifact layer for production.
- Allow download only if local cache miss.
- Never "auto-upgrade model" during daily fetch or serve startup.

---

## Service & Job Boundaries

## Recommended jobs

1. `components-fetch-daily` (stage-1 only, network I/O)
2. `components-transform-build` (stage-2 SQL + vector artifacts)
3. `components-transform-validate` (quality + schema + compatibility checks)
4. `components-transform-publish` (atomic symlink cutover)
5. `components-serve` (long-running API only; no heavy rebuild work)

## Runtime rule

`serve` must never build embeddings or indexes. It only loads ready artifacts.

---

## Performance Direction

## Near-term (already started)

- lazy model init
- lazy lexical index build
- vector mmap

## Next mergeable improvements

1. Persist lexical/filter indexes at build time (no rebuild at runtime).
2. Minimize Python object materialization from `records.jsonl` (binary metadata layout).
3. Add warmup endpoint/task to pre-initialize model/index after deploy.

## Final serving engine direction

- Keep Python stage-2 builder for flexibility.
- Add Zig runtime loader/query engine for stage-3 (same style as fast parametric lookup).
- Use memory-mapped binary vector/index artifacts.

---

## Data Contract Additions

Add a vector manifest schema (versioned), e.g.:

- `schema_version`
- `snapshot_name`
- `source_component_count`
- `vector_corpus_count`
- `embedding_backend`
- `model_id`
- `model_revision`
- `embedding_dim`
- `build_timestamp_utc`
- `builder_version`
- checksums/sizes for each index file

Serve verifies this manifest against snapshot metadata at startup.

---

## Quality Gates Before Publish

1. Build integrity:
   - file presence + checksum validation
2. Compatibility:
   - snapshot metadata ↔ vector manifest match
3. Retrieval quality:
   - fixed eval suite thresholds (`hit@k`, `MRR`, constraint compliance)
4. Performance:
   - p50/p95 latency thresholds
   - startup time threshold

If any gate fails, block publish.

---

## Concrete Implementation Plan

### Phase 1 (merge now)

1. Add stage-2 vector build command integrated with snapshot build output path.
2. Write vector manifest with strict model/version metadata.
3. Update serve config to default vector dir = `current/vector`.
4. Add startup compatibility checks + clear diagnostics.

### Phase 2

1. Build-time persisted lexical/filter indexes.
2. Remove runtime index reconstruction.
3. Add publish-time vector quality/perf validation report.

### Phase 3

1. Introduce Zig vector runtime interface + implementation.
2. Keep Python runtime as fallback/debug mode.
3. Benchmark and switch default engine once parity is validated.

---

## Summary

The right architecture is:

- Stage-1 stays raw.
- Stage-2 owns vector build (with pinned model policy).
- Publish atomically promotes SQL + vector together.
- Stage-3 only serves prebuilt artifacts.
- No daily "fetch latest model" behavior; model upgrades are explicit release events.

This preserves cleanliness, startup predictability, and performance while keeping room for Zig runtime acceleration.
