# Conflict Resolution Plan (Staging Merge)

This plan summarizes the conflicting files and recommends how to integrate incoming changes while preserving (or relocating) UI needs.

## src/atopile/model/builds.py

### Incoming improvements
- `_compute_active_elapsed(build)` centralizes elapsed time calculation for active builds.
- `_fix_interrupted_build(build)` normalizes stale BUILDING/QUEUED builds to FAILED with an error.
- Build history is sourced from sqlite via `build_history.load_recent_builds_from_history()`, creating a consistent single source of truth.
- Removes legacy conversion of ActiveBuild/HistoricalBuild into Build models.

### UI-driven changes on our branch
- `_convert_stage_dicts()` to normalize raw stage dicts into `BuildStage` objects.
- `_infer_building_status()` to reclassify queued builds as building when stages advance.
- `_active_build_to_build()` / `_historical_build_to_build()` to stitch in missing fields, stage defaults, and display fields needed by the UI.

### Recommended resolution
- Keep incoming build-history–first model and elapsed handling.
- Stage normalization already happens at **write time** (see `build_steps.py` recording `BuildStage` fields into build_history).
  - Active and historical builds read stages from the same sqlite history records.
  - No additional normalization is needed in this domain layer.
- If the UI still needs `display_name` / `project_name` guarantees, add them in the API layer where the response is constructed.

## src/atopile/model/build_queue.py

### Incoming improvements
- Background thread continuously drains `stderr` to avoid pipe-buffer deadlocks.
- Ensures the subprocess never blocks because the parent hasn’t read stderr.
- Keeps stage updates via polling `build_history` (consistent with new logging).

### UI-driven changes on our branch
- Non-blocking `stderr` reads with a tail buffer to avoid blocking.

### Recommended resolution
- Keep incoming stderr drain thread (more robust across platforms).
- If the UI needs only limited error output, truncate `stderr_output` (already done with `[:500]` before storing error).
- Continue to use build_history as the source for stage updates.

## Summary
- Adopt incoming logging/build-history pipeline.
- Relocate stage normalization to the API layer (or build_history writer) instead of core domain logic.
- Keep new stderr drain logic to prevent subprocess deadlocks.
