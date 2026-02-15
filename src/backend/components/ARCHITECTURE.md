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

### Runtime Storage

Default cache root in container:

- `/var/cache/atopile/components`

Config:

- `ATOPILE_COMPONENTS_CACHE_DIR` (default above)
- `ATOPILE_COMPONENTS_JLC_API_BASE_URL` (default `https://jlcpcb.com`)
- `JLC_API_KEY` / `JLC_API_SECRET`

### Fetch Outputs

- Raw JLC component pages/snapshots.
- Raw per-part JSON payloads.
- Raw datasheet PDFs.
- Raw KiCad/EasyEDA/3D files where available.
- Manifest/index records (hash, mime, sizes, timestamps, source).

## Stage 2: Transform (Serve Snapshots)

### Responsibilities

- Build immutable snapshots from stage-1 raw data.
- Produce two serving databases per snapshot:

1. `fast.sqlite` for query-critical lookup only.
2. `detail.sqlite` for full component/detail/asset lookup.

- Both keyed by `lcsc_id` (`INTEGER`), which is the canonical ID.

### Database Split

#### `fast.sqlite`

- `resistor_pick`
- `capacitor_pick`

Contains only:

- `lcsc_id`
- pickable parameters
- `stock`
- `is_basic`
- `is_preferred`

Design target: minimal rows and columns, heavy indexing for range filters.

#### `detail.sqlite`

- `components_full`
- `component_assets`

Contains:

- manufacturer/part metadata
- description
- price JSON
- attributes JSON
- asset references (datasheet/kicad/3d/raw object IDs/keys)

### Publish/Cutover

- Build new snapshot in a versioned directory.
- Validate snapshot.
- Atomically switch `current` symlink to new snapshot.
- API reopens read-only handles to new DB files.
- Keep previous snapshot for rollback, then prune old snapshots.

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

- Input: resistor/capacitor query constraints (`qty`, `limit`, package, pickable params).
- Reads only from `fast.sqlite`.
- Output: lightweight candidate records (includes `lcsc_id`, stock/flags, pick params).

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

This keeps fast lookup backend swappable (SQLite now, Zig/in-memory later).

## Tech Stack

- Language: Python
- API: FastAPI + Uvicorn
- HTTP client: `httpx`
- Data models: `pydantic`
- Compression: `zstandard`
- Databases: SQLite (read-only snapshots during serve)
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

The fast lookup implementation may be replaced by a custom Zig in-memory engine. API contracts remain unchanged by keeping `serve` behind storage-agnostic interfaces and `lcsc_id`-based joins to detail data.

## JLC API

stored as:
JLC_API_KEY
JLC_API_SECRET
