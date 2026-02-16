# Components Backend

Three-stage pipeline:

1. `fetch`: raw upstream ingestion and local cache
2. `transform`: build immutable serving snapshots
3. `serve`: FastAPI endpoints for solver + full component payloads

Primary stage-1 source is JLC OpenAPI (`open.jlcpcb.com`).
`cache.sqlite3` remains a local bootstrap fixture, not canonical input.

See `/Users/narayanpowderly/projects/atopile/src/backend/components/ARCHITECTURE.md` for full design.

## Stage 1 Quick Start

```bash
cd /Users/narayanpowderly/projects/atopile
export PYTHONPATH=/Users/narayanpowderly/projects/atopile/src
export ATOPILE_COMPONENTS_CACHE_DIR=/var/cache/atopile/components
export JLC_APP_ID="<app id>"
export JLC_ACCESS_KEY="<access key>"
export JLC_SECRET_KEY="<secret key>"
uv run python -m backend.components.fetch.jobs.fetch_once --max-pages 1
```

## JLC OpenAPI Signing Rules (Important)

- Every request is a signed `POST`.
- `Authorization` header format:
  - `JOP appid="<APP_ID>",accesskey="<ACCESS_KEY>",timestamp="<UNIX_SECONDS>",nonce="<32-char>",signature="<BASE64_HMAC_SHA256>"`
- Credential mapping:
  - `JLC_APP_ID` = App ID
  - `JLC_ACCESS_KEY` = Access Key
  - `JLC_SECRET_KEY` = Tokenization **Private** Key (signing key)
- String-to-sign is exactly:
  - `METHOD + "\n" + PATH_WITH_QUERY + "\n" + TIMESTAMP + "\n" + NONCE + "\n" + RAW_BODY + "\n"`
- The request body bytes must match the body used during signing.
- Capture `J-Trace-ID` from response headers for debugging/support.

## Known Error Meanings

- `401` + signature/login message: signing or credentials are incorrect.
- `403` + permission denied: auth is valid, but API scope is not granted for that endpoint.

## Stage 2 Quick Start

Build a snapshot from downloaded `cache.sqlite3`:

```bash
cd /Users/narayanpowderly/projects/atopile
export PYTHONPATH=/Users/narayanpowderly/projects/atopile/src
export ATOPILE_COMPONENTS_CACHE_DIR=/Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground
uv run python -m backend.components.transform.build_snapshot \
  --source-sqlite /Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground/raw/cache.sqlite3 \
  --snapshot-name local-dev
```

Promote snapshot atomically:

```bash
uv run python -m backend.components.transform.publish_snapshot local-dev --keep-snapshots 2
```

Notes:

- Snapshots built with `--max-components` are marked as partial in `metadata.json`.
- `publish_snapshot` rejects partial snapshots by default.
- Use `--allow-partial` only for intentional local/dev publishes.

Snapshot outputs:

- `fast.sqlite`
  - `resistor_pick`
  - `capacitor_pick`
  - `capacitor_polarized_pick`
  - `inductor_pick`
  - `diode_pick`
  - `led_pick`
  - `bjt_pick`
  - `mosfet_pick`
  - `crystal_pick`
  - `ferrite_bead_pick`
  - `ldo_pick`
  - prefiltered to pickable rows only (`stock > 0`, valid package, required params present)
- `detail.sqlite`
  - `components_full` (full metadata + normalized numeric fields)
  - `component_assets` (datasheet/footprint/3D reference fields)

Lookup parity with legacy backend:

- Numeric range filters apply the same `1e-5` relative epsilon on request bounds.
- Package filters accept both raw and legacy-prefixed forms for passives:
  - resistor: `0402` and `R0402`
  - capacitor: `0402` and `C0402`
  - ferrite bead: `0603`, `L0603`, and `FB0603`

Validate an existing snapshot:

```bash
uv run python -m backend.components.transform.validate_snapshot \
  /Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground/snapshots/local-dev
```

Stage-2 acceptance review and evidence:

- `/Users/narayanpowderly/projects/atopile/src/backend/components/transform/STAGE2_REVIEW.md`
- `/Users/narayanpowderly/projects/atopile/src/backend/components/E2E_VALIDATION_PLAN.md`

## Stage 3 Lookup Benchmark

Run lookup latency/throughput benchmarks with realistic resistor/capacitor query mixes:

```bash
cd /Users/narayanpowderly/projects/atopile
export PYTHONPATH=/Users/narayanpowderly/projects/atopile/src

# Benchmark against synthetic data (default)
uv run python -m backend.components.serve.lookup_bench \
  --iterations 50000 \
  --warmup 5000

# Benchmark against a real snapshot fast.sqlite (legacy SQLite baseline)
uv run python -m backend.components.serve.lookup_bench \
  --db /var/cache/atopile/components/current/fast.sqlite \
  --iterations 50000 \
  --warmup 5000 \
  --explain
```

## Stage 3 Fast Engine

Stage 3 serve uses Zig fast lookup, reading `fast.sqlite` + `detail.sqlite` from
the active snapshot.

The Zig lookup loader is schema-driven:

- introspects available `*_pick` tables in `fast.sqlite`
- exports compact per-table TSV + `schema.json` into cache
- builds in-memory indexes and serves any discovered component type

Run the API:

```bash
uv run python -m backend.components.serve.main
```

Optional overrides:

```bash
export ATOPILE_COMPONENTS_FAST_DB_FILENAME=fast.sqlite
```

## Deployment-Oriented Orchestration

Use a single declarative file to describe stage1/stage2 dataflow and execution:

```bash
components-pipeline.toml
```

Then plan/apply from that file:

```bash
cd /Users/narayanpowderly/projects/atopile
./scripts/components_pipeline_apply.py --config ./components-pipeline.toml --plan
./scripts/components_pipeline_apply.py --config ./components-pipeline.toml --apply
```

Unified status/monitor snapshot:

```bash
./scripts/components_pipeline_status.py
```

The status report includes:

- stage1 roundtrip state counts (`success/failed/running`)
- stage1 manifest artifact count
- stage2 `snapshots/current` resolution + metadata
- serve `/healthz` check payload (if reachable)

Notes:

- Set `paths.cache_dir` once in `components-pipeline.toml` to keep stage1/stage2/serve aligned.
- Use `workflow.mode` for deployment topology:
  - `processor-once` for processor host
  - `serve` for serve-only host
  - `all-in-one-once` for single host

Compare Zig vs SQLite on the same source rows (offline benchmark only):

```bash
uv run python -m backend.components.serve.lookup_bench_compare \
  --db /Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground/snapshots/current/fast.sqlite \
  --iterations 3000 \
  --warmup 300 \
  --json-out /tmp/lookup-compare.json
```
