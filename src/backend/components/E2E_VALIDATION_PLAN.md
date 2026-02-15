# End-to-End Validation Plan

Date: 2026-02-15
Owner: Components Backend

## Goal

Validate the full pipeline for resistor/capacitor data:

1. Stage 1 `fetch` ingests source data correctly.
2. Stage 2 `transform` builds valid, query-optimized snapshots.
3. Stage 3 `serve` answers parameter and full-detail requests correctly and fast.
4. Publish/cutover/rollback behavior is safe in production-like operation.

## Scope

In scope:

- Resistors and capacitors only.
- JLC OpenAPI ingest path (when API permissions are available).
- `cache.sqlite3` fixture ingest path (current bootstrap path).
- `fast.sqlite` and `detail.sqlite` snapshot correctness.
- API routes:
  - `POST /v1/components/parameters/query`
  - `POST /v1/components/full`
  - `GET /healthz`

Out of scope:

- Other component families.
- Long-term data quality tuning for every rare attribute variant.
- Production observability tooling rollout.

## Environments

Run in two environments:

1. Local dev environment (fast iteration).
2. Container-like environment with writable cache volume mounted at `/var/cache/atopile/components`.

## Prerequisites

```bash
cd /Users/narayanpowderly/projects/atopile
export PYTHONPATH=/Users/narayanpowderly/projects/atopile/src
export ATOPILE_COMPONENTS_CACHE_DIR=/Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground
```

For JLC live fetch path:

```bash
export JLC_APP_ID="..."
export JLC_ACCESS_KEY="..."
export JLC_SECRET_KEY="..."
```

## Test Data Sets

- Fetch `SMOKE`: `--max-pages 1` (and optional `--fetch-details --max-details 50`)
- Transform `SMOKE`: `--max-components 1000`
- Transform `MEDIUM`: `--max-components 50000`
- `FULL`: no limit (production-like)

## Validation Phases

## Input Contract (Stage 3)

- Query inputs must use canonical filter keys and canonical package identifiers.
- Package values are expected to be component-typed (`R0402`, `C0402`, etc.).
- Bare package codes (for example `0402`) are not part of this contract and should be normalized by callers before hitting Stage 3.

## Phase 0: Static and Unit Gates

Commands:

```bash
uv run ruff check src/backend/components
uv run pytest -q src/backend/components
```

Pass criteria:

- Lint clean.
- All tests pass.

## Phase 1: Stage 1 Fetch Validation

### 1A. JLC OpenAPI path (when permissions are active)

Command:

```bash
uv run python -m backend.components.fetch.jobs.fetch_once --max-pages 1
```

Pass criteria:

- Output snapshot directory created under `.../fetch/jlc_api/<timestamp>`.
- `components.ndjson` non-empty.
- `metadata.json` contains `last_trace_id`.
- No credential leakage in metadata.

### 1B. Stage 1 artifact roundtrip path (no JLC credentials required)

Commands:

```bash
uv run python -m backend.components.fetch.jobs.fetch_once \
  --skip-jlc-list \
  --roundtrip-lcsc-id 21190

uv run python -m backend.components.fetch.jobs.fetch_once \
  --skip-jlc-list \
  --roundtrip-lcsc-id 21190 \
  --roundtrip-datasheet-url https://www.lcsc.com/datasheet/C21190.pdf
```

Pass criteria:

- Roundtrip report file created under `.../fetch/roundtrip/<timestamp>/C<id>.json`.
- `compare_ok == true` in report.
- Artifact set includes:
  - `kicad_footprint_mod`
  - `model_obj` (when available)
  - `model_step` (when available)
  - `datasheet_pdf` when datasheet URL is provided
- If EasyEDA footprint conversion fails, command fails (no fallback/degraded success).

### 1C. Fixture source sanity path (current transform baseline)

Command:

```bash
uv run python - <<'PY'
from pathlib import Path
import sqlite3

db = Path("/Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground/raw/cache.sqlite3")
if not db.exists():
    raise SystemExit(f"missing sqlite fixture: {db}")

with sqlite3.connect(db) as conn:
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
missing = {"components", "categories", "manufacturers"} - tables
if missing:
    raise SystemExit(f"missing tables: {sorted(missing)}")

print("fixture sqlite sanity ok")
PY
```

Pass criteria:

- Downloaded `cache.sqlite3` exists and is readable.
- Source table sanity checks pass (`components`, `categories`, `manufacturers` present).

## Phase 2: Stage 2 Transform Validation

Command:

```bash
uv run python -m backend.components.transform.build_snapshot \
  --source-sqlite /Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground/raw/cache.sqlite3 \
  --snapshot-name e2e-transform-smoke \
  --max-components 50000
```

Then validate:

```bash
uv run python -m backend.components.transform.validate_snapshot \
  /Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground/snapshots/e2e-transform-smoke
```

Pass criteria:

- `fast.sqlite`, `detail.sqlite`, `metadata.json` exist.
- Validation reports:
  - required tables/indexes present
  - bounds integrity passes (`min <= nominal <= max`)
  - `components_full` row count equals `component_assets` row count
- `metadata.json` validation section populated.

## Phase 3: Publish/Cutover Validation

Publish:

```bash
uv run python -m backend.components.transform.publish_snapshot e2e-transform-smoke --keep-snapshots 2
```

Pass criteria:

- `snapshots/current` points to target snapshot.
- `snapshots/previous` updates on second publish.
- Old snapshots are pruned according to retention setting.
- Publish fails if snapshot validation fails.

## Phase 4: Stage 3 Serve Functional Validation

Run API:

```bash
export ATOPILE_COMPONENTS_CACHE_DIR=/Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground
export ATOPILE_COMPONENTS_CURRENT_SNAPSHOT_NAME=snapshots/current
uv run python -m backend.components.serve.main
```

### 4A. Health

```bash
curl -s http://127.0.0.1:8079/healthz | jq .
```

Expect:

- `status == "ok"`
- snapshot and DB paths point to `snapshots/current`.

### 4B. Parameter Query (resistor)

```bash
curl -s http://127.0.0.1:8079/v1/components/parameters/query \
  -H 'content-type: application/json' \
  -d '{
    "component_type": "resistor",
    "qty": 100,
    "limit": 20,
    "package": "R0402",
    "ranges": {
      "resistance_ohm": {"minimum": 900, "maximum": 1100},
      "max_voltage_v": {"minimum": 25}
    }
  }' | jq .
```

Expect:

- HTTP 200.
- `total > 0` for typical values.
- Results sorted with preferred/basic/stock ordering logic.

### 4C. Parameter Query (capacitor)

```bash
curl -s http://127.0.0.1:8079/v1/components/parameters/query \
  -H 'content-type: application/json' \
  -d '{
    "component_type": "capacitor",
    "qty": 100,
    "limit": 20,
    "package": "C0402",
    "exact": {"tempco_code": "X7R"},
    "ranges": {
      "capacitance_f": {"minimum": 9e-8, "maximum": 1.1e-7},
      "max_voltage_v": {"minimum": 16}
    }
  }' | jq .
```

Expect:

- HTTP 200 and non-empty candidates for common ranges.

### 4D. Full Endpoint

1. Take 3-10 candidate `lcsc_id` values from query results.
2. Write request payload:

```bash
cat > /tmp/component_ids.json <<'JSON'
{"component_ids":[<id1>,<id2>,<id3>]}
JSON
```

3. Request:

```bash
curl -i http://127.0.0.1:8079/v1/components/full \
  -H 'content-type: application/json' \
  -d @/tmp/component_ids.json
```

Expect:

- HTTP 200.
- `Content-Type: multipart/mixed; boundary=...`
- JSON metadata part present.
- Zstd bundle part present with `X-Bundle-SHA256`.

## Phase 5: Bundle Integrity Validation

Capture the full endpoint response:

```bash
# Use component IDs selected in Phase 4.
curl -s http://127.0.0.1:8079/v1/components/full \
  -H 'content-type: application/json' \
  -d @/tmp/component_ids.json \
  -D /tmp/components_full.headers \
  -o /tmp/components_full.multipart
```

Then validate multipart + bundle integrity:

```bash
uv run python - <<'PY'
import hashlib
import io
import json
import tarfile
from pathlib import Path

import zstd

headers = Path("/tmp/components_full.headers").read_text().splitlines()
content_type = next(
    (line for line in headers if line.lower().startswith("content-type:")),
    None,
)
if content_type is None or "boundary=" not in content_type:
    raise SystemExit("multipart boundary header missing")
boundary = content_type.split("boundary=", 1)[1].strip()

from email import policy
from email.parser import BytesParser

raw = Path("/tmp/components_full.multipart").read_bytes()
wire = (
    f"Content-Type: multipart/mixed; boundary={boundary}\r\n"
    "MIME-Version: 1.0\r\n\r\n"
).encode("utf-8") + raw
msg = BytesParser(policy=policy.default).parsebytes(wire)
parts = msg.get_payload()
metadata = json.loads(parts[0].get_payload(decode=True))
bundle = parts[1].get_payload(decode=True)
sha = hashlib.sha256(bundle).hexdigest()
if sha != metadata["bundle_sha256"]:
    raise SystemExit("bundle sha mismatch")

tar_bytes = zstd.decompress(bundle)
with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:") as tf:
    names = tf.getnames()
    if "manifest.json" not in names:
        raise SystemExit("manifest.json missing")
    manifest = json.loads(tf.extractfile("manifest.json").read())
component_ids = [int(component["lcsc_id"]) for component in metadata["components"]]
if sorted(component_ids) != sorted(manifest.get("components_found", [])):
    raise SystemExit("manifest/components mismatch")
print("bundle integrity ok")
PY
```

Pass criteria:

- No decompression or tar parse failures.
- Manifest references are internally consistent.

## Phase 6: Performance Validation

Use built-in benchmark:

```bash
uv run python -m backend.components.serve.lookup_bench \
  --db /Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground/snapshots/current/fast.sqlite \
  --iterations 50000 \
  --warmup 5000 \
  --explain
```

Pass criteria:

- Query plans show index usage on range/package paths.
- p95 and p99 latencies are recorded and compared to baseline.
- No major regression versus previous validated snapshot.

## Phase 7: Failure and Rollback Drills

Publish invalid snapshot directory and verify reject:

```bash
mkdir -p /Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground/snapshots/invalid-empty
set +e
uv run python -m backend.components.transform.publish_snapshot invalid-empty --keep-snapshots 2
status=$?
set -e
test $status -ne 0
```

Rollback to previous and verify health:

```bash
ln -sfn "$(readlink /Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground/snapshots/previous)" \
  /Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground/snapshots/current
curl -s http://127.0.0.1:8079/healthz | jq .
```

Simulate missing DB file and verify startup error:

```bash
mkdir -p /Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground/snapshots/missing-fast
cp /Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground/snapshots/current/detail.sqlite \
  /Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground/snapshots/missing-fast/detail.sqlite
set +e
ATOPILE_COMPONENTS_CURRENT_SNAPSHOT_NAME=snapshots/missing-fast \
  uv run python -m backend.components.serve.main
status=$?
set -e
rm -rf /Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground/snapshots/missing-fast
test $status -ne 0
```

Pass criteria:

- Failure modes are explicit and safe (no partial publish state).
- Rollback restores healthy service quickly.

## Sign-Off Checklist

- [ ] Phase 0 complete
- [ ] Phase 1 complete
- [ ] Phase 2 complete
- [ ] Phase 3 complete
- [ ] Phase 4 complete
- [ ] Phase 5 complete
- [ ] Phase 6 complete
- [ ] Phase 7 complete
- [ ] All command logs and key outputs stored in run notes

## Evidence Artifacts

Store per run:

- snapshot `metadata.json`
- `validate_snapshot` output
- benchmark summary output
- sample query request/response payloads
- publish/cutover symlink state (`ls -la snapshots/`)
