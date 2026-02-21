# Components Backend Architecture

## Goals

Build a clean 3-stage backend for component data:

1. `fetch`: raw data ingestion and local mirror.
2. `transform`: convert raw data into serve-optimized snapshots.
3. `serve`: FastAPI service for solver queries and full component payloads.

Initial component scope: **resistors** and **capacitors**.

## Top-Level Layout

```text
src/backend/components/
  ARCHITECTURE.md
  README.md
  __init__.py

  shared/
    __init__.py
    types.py
    paths.py
    logging.py

  fetch/
    __init__.py
    config.py
    models.py
    compression.py
    sources/
      jlc_api.py
      jlcparts.py
      lcsc.py
      easyeda.py
      datasheets.py
    storage/
      object_store.py
      manifest_store.py
    jobs/
      fetch_once.py
      fetch_daily.py

  transform/
    __init__.py
    config.py
    models.py
    build_snapshot.py
    fast_db_builder.py
    detail_db_builder.py
    publish_snapshot.py

  serve/
    __init__.py
    main.py
    routes.py
    schemas.py
    interfaces.py
    fast_lookup_sqlite.py
    detail_store_sqlite.py
    bundle_builder.py
```

## Stage 1: Fetch (Raw Mirror)

### Responsibilities

- Fetch source data from upstream systems (JLC API/LCSC/EasyEDA/datasheets).
- Store artifacts **raw and lossless-compressed** (`zstd`) at rest.
- Keep source-of-truth manifests keyed by `lcsc_id` + content hash.
- Avoid normalization/business logic.

### Source Priority

1. **Primary**: official authenticated JLC API.
2. **Secondary**: LCSC per-part detail API for richer part metadata.
3. **Optional bootstrap/dev fixture**: prebuilt `cache.sqlite3` exports (non-canonical).

### JLC API Contract Notes

- Transport: HTTPS only.
- Method: POST only.
- Standard payloads: JSON (`Content-Type: application/json`, UTF-8).
- Upload payloads: multipart (`Content-Type: multipart/form-data`).
- Treat HTTP `200` as transport success only; check business `code` in body.
- Persist `J-Trace-ID` response header in fetch metadata/logs for support/debugging.
- Component APIs needed now:
  1. paginated public component list
  2. per-component detail by C-number

### JLC Auth Details (Learned)

- Use OpenAPI host: `https://open.jlcpcb.com`.
- Use `Authorization: JOP ...` header on every request.
- Header fields are: `appid`, `accesskey`, `timestamp`, `nonce`, `signature`.
- Credential mapping:
  - `JLC_APP_ID` = App ID
  - `JLC_ACCESS_KEY` = Access Key
  - `JLC_SECRET_KEY` = Tokenization private key (HMAC signing key)
- Signature is `Base64(HMAC_SHA256(secret_key, string_to_sign))`.
- `string_to_sign` must be exactly:
  1. HTTP method (uppercase)
  2. request path (+ query if present)
  3. unix timestamp (seconds)
  4. 32-char nonce
  5. raw JSON body
  6. trailing newline
- The exact body bytes must match the body used in signing.
- `J-Trace-ID` should always be logged/persisted for support.
- Error interpretation:
  - `401` typically means bad credentials/signature.
  - `403` with permission message means auth is valid but API scope is not granted.

### Runtime Storage

Default cache root in container:

- `/var/cache/atopile/components`

Config:

- `ATOPILE_COMPONENTS_CACHE_DIR` (default above)
- `ATOPILE_COMPONENTS_JLC_API_BASE_URL` (default `https://open.jlcpcb.com`)
- `JLC_APP_ID`
- `JLC_ACCESS_KEY`
- `JLC_SECRET_KEY`
- `ATOPILE_COMPONENTS_JLC_COMPONENT_INFOS_PATH` (default `/overseas/openapi/component/getComponentInfos`)
- `ATOPILE_COMPONENTS_JLC_COMPONENT_DETAIL_PATH` (default `/overseas/openapi/component/getComponentDetail`)

### Fetch Outputs

- Raw JLC component pages/snapshots.
- Raw per-part JSON payloads.
- Raw datasheet PDFs.
- Raw KiCad/EasyEDA/3D files where available.
- Manifest/index records (hash, mime, sizes, timestamps, source).

### Stage 1 Implementation TODO

#### Shared Fetch Foundation

- [x] Implement shared artifact model (`lcsc_id`, `artifact_type`, `source_url`, `raw_sha256`, `raw_size`, `mime`, `encoding`, `stored_key`, `fetched_at`, `source_meta`).
- [x] Implement `zstd` compression/decompression helpers.
- [x] Implement stable object-store keying (`objects/<artifact_type>/<sha256>.zst`).
- [x] Implement local object-store write/read API.
- [x] Implement manifest store (append/upsert records keyed by `lcsc_id` + artifact identity).
- [x] Implement compare helpers for byte-identity and JSON semantic-identity.
- [x] Implement reusable round-trip validation helper:
  1. fetch raw bytes
  2. compress and store
  3. load and decompress
  4. compare hash and payload equality
  5. write manifest record

#### Datasheets

- [x] Implement datasource adapter for datasheet URLs.
- [x] Support both direct PDF responses and HTML wrappers that contain embedded PDF URLs.
- [x] Persist raw PDF bytes (lossless `zstd`), no PDF transformations.
- [x] Persist source metadata: original URL, resolved URL, content type, status.
- [x] Add round-trip tests (raw PDF bytes and hash identical after decompress).
- [x] Add negative-path tests (invalid redirect, missing embedded PDF URL, unsupported MIME).
- [x] Handle LCSC JS-escaped `previewPdfUrl` variants (`\/`, `\u002F`, scheme-relative paths).

#### 3D Models (EasyEDA)

- [x] Implement EasyEDA CAD JSON fetch by `lcsc_id`.
- [x] Treat CAD JSON as transient extraction input (do not persist as a stage-1 artifact).
- [x] Extract 3D UUID from CAD JSON shape records.
- [x] Fetch and store OBJ model when available.
- [x] Fetch and store STEP model when available.
- [x] Record partial-success states (e.g. OBJ missing but STEP present).
- [x] Add round-trip tests for KiCad footprint / OBJ / STEP.

#### Footprints

- [x] Convert EasyEDA footprint payload to KiCad `.kicad_mod` server-side.
- [x] Store KiCad footprint artifact as compressed bytes (`zstd`), lossless.
- [x] Fail part fetch if footprint conversion fails (no fallback path).
- [x] Add round-trip tests for KiCad footprint artifacts.

#### Fetch Job Integration

- [x] Extend `fetch_once` orchestration to run datasheet + EasyEDA artifact pipelines for sample inputs.
- [x] Add fetch summary report (`pass/fail` per artifact per `lcsc_id`).
- [x] Wire daily job scaffold for scheduled execution.

#### Stage 1 Validation (Completed)

- [x] Automated tests (`ruff` + `pytest`) for `shared/` + `fetch/`.
- [x] Manual roundtrip (EasyEDA/footprint/3D): `uv run python -m src.backend.components.fetch.jobs.fetch_once --skip-jlc-list --roundtrip-lcsc-id 21190`
- [x] Manual roundtrip (datasheet direct/wrapper resolve): `uv run python -m src.backend.components.fetch.jobs.fetch_once --skip-jlc-list --roundtrip-lcsc-id 21190 --roundtrip-datasheet-url https://www.lcsc.com/datasheet/C21190.pdf`

## Stage 2: Transform (Serve Snapshots)

### Responsibilities

- Build immutable snapshots from stage-1 raw data.
- Produce fast + detail serving artifacts per snapshot:

1. `fast.sqlite` for query-critical lookup tables.
2. `detail.sqlite` for full component/detail/asset lookup.

- Both keyed by `lcsc_id` (`INTEGER`), which is the canonical ID.

### Artifact Split

#### `fast.sqlite`

Contains only pickable rows and query-critical columns, keyed by `lcsc_id`.

Current implementation tables:

- `resistor_pick`
- `capacitor_pick`
- `capacitor_polarized_pick`
- `inductor_pick`
- `diode_pick`
- `led_pick`
- `bjt_pick`
- `mosfet_pick`

#### `detail.sqlite`

- `components_full`
- `component_assets`

Contains:

- manufacturer/part metadata
- description
- price JSON
- attributes JSON
- asset references (datasheet/kicad/3d/raw object IDs/keys)

Current implementation:

- `components_full`
  - canonical metadata + normalized numeric parameter columns
  - raw JSON payload fields (`price_json`, `attributes_json`, `extra_json`)
- `component_assets`
  - `datasheet_url`, `data_manual_url`, `footprint_name`, `model_3d_path`, `easyeda_model_uuid`

### Publish/Cutover

- Build new snapshot in a versioned directory.
- Validate snapshot structure and row integrity.
- Atomically switch `current` symlink to new snapshot.
- API reopens read-only handles to new DB files.
- Keep previous snapshot for rollback, and prune older snapshots by retention policy.

### Stage 2 Acceptance Checklist

- [x] Build immutable snapshot directory with `fast.sqlite` + `detail.sqlite`.
- [x] Normalize resistor/capacitor pick parameters into SI numeric columns.
- [x] Precompute tolerance-aware min/max bounds for fast ranged lookup.
- [x] Store full component metadata and asset references keyed by `lcsc_id`.
- [x] Validate built snapshots before publish.
- [x] Atomic cutover with `current` / `previous` links.
- [x] Retention pruning for old snapshots.
- [x] Automated tests for parsing, builders, snapshot build, validation, and publish flow.
- [x] Manual smoke verification on downloaded `cache.sqlite3`.

### Suggested Snapshot Layout

```text
/var/cache/atopile/components/
  snapshots/
    2026-02-15T00-00-00Z/
      fast.sqlite
      detail.sqlite
      metadata.json
  current -> snapshots/2026-02-15T00-00-00Z
  previous -> snapshots/2026-02-14T00-00-00Z
```

## Stage 3: Serve (FastAPI)

Use **FastAPI** for API serving.

### Endpoints

#### 1) `POST /v1/components/parameters/query`

Fast candidate query endpoint.

- Input: query constraints (`qty`, `limit`, package, pickable params) across supported
  component types.
- Reads from Zig in-memory lookup with `fast.sqlite` as the source snapshot
  artifact.
- Zig lookup is schema-driven over discovered `*_pick` tables, so newly-added
  fast component tables do not require hardcoded Python query glue.
- Output: lightweight candidate records (includes `lcsc_id`, stock/flags, pick params).

#### 1b) `POST /v1/components/parameters/query/batch`

Grouped candidate query endpoint for large designs.

- Input: ordered list of parameter-query payloads (same shape as endpoint 1).
- Output: ordered per-query candidate result list.
- Designed to preserve pick-group semantics while reducing HTTP overhead and enabling
  concurrent fast-lookup execution server-side.
- Implemented as a native Zig batch request (`{"queries":[...]}`) so Python route logic
  remains thin.

#### 2) `POST /v1/components/full`

Full payload endpoint, a strict superset of parameter query data.

- Input: list of `component_ids` (`lcsc_id`).
- Reads from `detail.sqlite` + asset store.
- Returns:
  - full component metadata/parameters manifest (JSON)
  - compressed asset bundle (`tar.zst`)

Bundle may be returned as `multipart/mixed` (JSON part + `application/zstd` part), or as a binary bundle with embedded `manifest.json`.

## Compression Strategy

### At Rest

- Store fetched artifacts in an object store as `zstd` compressed blobs.
- Canonical keying by `sha256` of canonical bytes.

### Semantic Compression

- Canonicalize text-like formats where safe and lossless:
  - JSON: stable key ordering/minified canonical form.
  - KiCad/sexp: canonical emit (future step).
  - STEP/OBJ: line ending/whitespace normalization only.
- Deduplicate by content hash.

### For Full API Responses

- Build deterministic `tar.zst` bundles.
- Include `manifest.json` + checksums.
- Client is expected to decompress.

### Stage 1 Artifact Compression Research (2026-02-15)

Objective: find per-artifact strategies that beat generic `zstd -10` while preserving
round-trip correctness for fetch-stage storage.

Corpus used for local benchmarks in this repo:

- `kicad_mod`: 345 unique files
- `step/stp`: 95 unique files
- `pdf`: 30 unique files
- `obj`: 2 unique stage-1 samples

Measured outcomes versus current baseline (`zstd -10`):

- `kicad_mod`: dictionary compression is a clear win.
  - `zstd -10 -D <dict>` with a 32 KiB trained dictionary: ~37% smaller than baseline.
  - `zstd -14 -D <dict>`: ~45% smaller than baseline.
  - Recommendation: use a versioned per-type dictionary for `.kicad_mod` artifacts.
- `step/stp`: trained dictionaries regressed size in our corpus.
  - `zstd -14` gave ~4% size improvement over baseline.
  - `zstd -16` gave ~8.5% size improvement over baseline at much higher CPU cost.
  - Recommendation: no dictionary; choose level by policy (`-14` balanced, `-16` size-priority).
- `pdf`: only marginal gains from higher levels.
  - `zstd -14` improved size by ~0.4% over baseline.
  - Recommendation: prioritize throughput (`-6` or `-10`), not aggressive compression.
- `obj`: limited local sample count, but higher levels help.
  - `zstd -14` improved size by ~15% vs baseline on available sample.
  - Recommendation: use `-14` for now; evaluate mesh-native encoding (Draco/meshopt)
    if semantic (not byte-identical) round-trip is acceptable.

External references informing strategy:

- Zstandard dictionary guidance and small-data behavior:
  <https://github.com/facebook/zstd/blob/dev/README.md>,
  <https://github.com/facebook/zstd/blob/dev/lib/zdict.h>
- KiCad footprint/file format references:
  <https://docs.kicad.org/master/en/file-formats/file-formats.html>
- OBJ/STEP format references:
  <https://www.loc.gov/preservation/digital/formats/fdd/fdd000507.shtml>,
  <https://www.loc.gov/preservation/digital/formats/fdd/fdd000448.shtml>
- STEP media type variants (`model/step+zip`, etc.):
  <https://www.iana.org/assignments/media-types/media-types.xhtml>
- Mesh-native compression references:
  <https://github.com/zeux/meshoptimizer>,
  <https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Vendor/EXT_meshopt_compression>,
  <https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_draco_mesh_compression>
- PDF optimization/tooling limits:
  <https://qpdf.readthedocs.io/en/stable/cli.html>,
  <https://ghostscript.readthedocs.io/en/latest/VectorDevices.html>

## Internal Interface Boundaries

`serve` should depend on interfaces, not specific storage engines:

- `FastLookupStore`
  - `query_resistors(...) -> list[lcsc_id]`
  - `query_capacitors(...) -> list[lcsc_id]`
- `DetailStore`
  - `get_components(lcsc_ids)`
  - `get_asset_manifest(lcsc_ids)`
- `BundleStore`
  - `build_bundle(lcsc_ids)`

This keeps fast lookup behind stable interfaces while Zig remains the
production implementation.

## Tech Stack

- Language: Python
- API: FastAPI + Uvicorn
- HTTP client: `httpx`
- Data models: `pydantic`
- Compression: `zstandard`
- Databases: SQLite (`detail.sqlite`, read-only snapshots during serve)
- Scheduling: periodic daily fetch/transform jobs

## SQLite Operational Notes

Serve mode:

- Open `mode=ro` (read-only)
- `query_only=ON`
- `immutable=1` where applicable
- tune cache/mmap pragmas for read throughput

Build mode:

- bulk load in transactions
- create indexes after inserts
- run `ANALYZE` and `PRAGMA optimize`

## Testing Convention

Per project preference, tests are co-located in module files (at bottom), not in separate `tests/` directories.

## Future Direction

Explore compact binary or custom in-memory indexes behind the same fast lookup
interface if SQLite becomes the bottleneck.
