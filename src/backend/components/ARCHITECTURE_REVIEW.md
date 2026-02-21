# Components Pipeline: Reviewer Architecture Notes

## Scope

This document summarizes current production-intended flow for:

- Stage 1 fetch/materialization (`fetch`)
- Stage 2 snapshot build/publish (`transform`)
- Stage 3 read API (`serve`)

## Single Source of Truth

The pipeline is declared in one file:

- `components-pipeline.toml`

This file defines:

- canonical paths (`cache_dir`, `source_sqlite`)
- stage1/stage2 options
- human-readable stage1->stage2 dataflow
- execution mode (`processor-once`, `serve`, `all-in-one-once`, etc.)

Execution is driven by:

- `scripts/components_pipeline_apply.py --plan|--validate|--apply`

## Dataflow

1. Stage 1 input
- source: `paths.source_sqlite`
- filter: `stage1.where`

2. Stage 1 outputs
- `cache_dir/fetch/manifest.sqlite3`
- `cache_dir/fetch/roundtrip_state.sqlite3`
- `cache_dir/objects/<artifact_type>/<sha256>.zst`

3. Stage 2 inputs
- source sqlite rows (`paths.source_sqlite`)
- stage1 manifest rows (`cache_dir/fetch/manifest.sqlite3`)

4. Stage 2 outputs
- `cache_dir/snapshots/<snapshot>/fast.sqlite`
- `cache_dir/snapshots/<snapshot>/detail.sqlite`
- `cache_dir/snapshots/<snapshot>/metadata.json`

5. Publish
- atomic symlink swap: `cache_dir/snapshots/current -> <snapshot>`

## Optional Transform/Fetch Jobs

Integrated into declarative pipeline:

- Part image scrape job:
  - module: `backend.components.fetch.jobs.fetch_images_from_cache`
  - artifact type: `part_image`
- STEP -> GLB transform job:
  - module: `backend.components.transform.step_to_glb`
  - artifact type: `model_glb`

## Deployment Topologies

1. Single-host
- mode: `all-in-one-once`
- all stages share one `cache_dir`

2. Processor/Serve split
- processor host mode: `processor-once` (or stage-specific commands)
- serve host mode: `serve`
- both point to aligned snapshot root (same path via shared storage or synced copy)

3. Multi-serve
- one processor publishes snapshots
- multiple read-only serve instances mount same snapshot root

## Failure Modes and Recovery

1. Stage 1 interruption
- resume supported by `roundtrip_state.sqlite3`
- rerun continues from state table

2. Stage 2 build failure
- build is snapshot-local; failed build does not alter `current`

3. Publish failure
- no partial switch; `current` remains prior snapshot

4. Serve mismatch
- detectable via status monitor:
  - `scripts/components_pipeline_status.py`
  - `snapshot_mismatch_vs_cache_dir` flag

## Operations and Monitoring

- Plan/validate/apply:
  - `scripts/components_pipeline_apply.py`
- Status:
  - `scripts/components_pipeline_status.py`
- Smoke test:
  - `scripts/components_pipeline_smoke.sh`
- Cleanup:
  - `scripts/components_cleanup.sh`

## Reviewer Checklist

- Confirm `components-pipeline.toml` paths are consistent across stages.
- Confirm stage1 artifacts are compressed blobs under `objects/`.
- Confirm stage2 publish is atomic and rollback-safe.
- Confirm resume state table exists and updates during long runs.
- Confirm serve reads `snapshots/current` expected by processor.
- Confirm optional jobs (`part_image`, `model_glb`) are enabled/disabled intentionally.
