# Stage 2 Review

Date: 2026-02-15

## Scope

Review of stage-2 transform pipeline for resistor/capacitor snapshots:

- Source ingest from downloaded JLC `cache.sqlite3`
- Build fast TSV artifacts and `detail.sqlite`
- Validate and publish snapshots
- Verify range-query lookup shape for solver

## Architecture Coverage

- [x] Fast TSV + detail DB outputs per snapshot (`resistor_pick.tsv`, `capacitor_pick.tsv`, `detail.sqlite`)
- [x] Canonical key `lcsc_id` in all stage-2 tables
- [x] Fast pick tables contain only query-critical fields + flags/stock/package
- [x] Detail tables contain full metadata + asset references
- [x] Precomputed tolerance bounds for ranged lookup:
  - resistor: `resistance_min_ohm` / `resistance_max_ohm`
  - capacitor: `capacitance_min_f` / `capacitance_max_f`
- [x] Canonical package normalization for passives (`R0402`/`C0402` -> `0402`)
- [x] Snapshot validation before publish
- [x] Atomic `current`/`previous` symlink cutover
- [x] Retention pruning of old snapshots (`--keep-snapshots`)

## Automated Tests

Command:

```bash
uv run pytest -q \
  src/backend/components/transform/config.py \
  src/backend/components/transform/models.py \
  src/backend/components/transform/fast_tsv_builder.py \
  src/backend/components/transform/detail_db_builder.py \
  src/backend/components/transform/validate_snapshot.py \
  src/backend/components/transform/build_snapshot.py \
  src/backend/components/transform/publish_snapshot.py
```

Result:

- `13 passed`

Lint:

```bash
uv run ruff check src/backend/components/transform
```

Result:

- `All checks passed!`

## Manual Validation

### Build + Validate Snapshot

Command:

```bash
PYTHONPATH=/Users/narayanpowderly/projects/atopile/src \
ATOPILE_COMPONENTS_CACHE_DIR=/Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground \
uv run python -m backend.components.transform.build_snapshot \
  --source-sqlite /Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground/raw/cache.sqlite3 \
  --snapshot-name stage2-review-a \
  --max-components 50000
```

Observed metadata:

- `source_component_count=50000`
- `fast_component_count=41461`
- `detail_component_count=50000`
- `validation.fast_total_rows=41461`
- `validation.detail_total_rows=50000`

Validation command:

```bash
uv run python -m backend.components.transform.validate_snapshot \
  /Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground/snapshots/stage2-review-a
```

Result:

- `fast_rows=41461 detail_rows=50000`

### Fast Artifact Contract

- `resistor_pick.tsv` contains canonicalized package + precomputed range bounds.
- `capacitor_pick.tsv` contains canonicalized package + precomputed range bounds.
- Stage-3 Zig lookup loads these TSV artifacts directly.

### Publish Flow

Commands run:

```bash
uv run python -m backend.components.transform.publish_snapshot stage2-review-b --keep-snapshots 2
uv run python -m backend.components.transform.publish_snapshot stage2-review-c --keep-snapshots 2
```

Observed:

- `current -> stage2-review-c`
- `previous -> stage2-review-b`
- older snapshots pruned per retention rule

## Remaining Integration Work

- Stage-2 source adapter currently reads downloaded `cache.sqlite3`.
- When stage-1 JLC OpenAPI fetch is fully live, add/enable an adapter from stage-1 raw mirror artifacts to the same normalization/builder interfaces.
