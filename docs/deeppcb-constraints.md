# DeepPCB Constraint Capabilities

Reference for how constraints are sent to the DeepPCB API and what we can build on top of them.

## Two constraint mechanisms

DeepPCB has two completely separate constraint systems:

| Mechanism | Scope | Encoding | When sent |
|-----------|-------|----------|-----------|
| `routingType` | Routing jobs | Top-level form field on board creation | `POST /api/v1/boards`, inherited by confirm/resume |
| Placement constraints file | Placement jobs | Separate JSON file, uploaded, URL passed to confirm | `PATCH .../confirm` via `constraintsFileUrl` |

They are independent — `routingType` is never inside the constraints JSON, and placement constraints are never form fields.

## 1. `routingType` (routing jobs)

Controls what happens to existing wires when a routing job runs.

| Value | Behavior |
|-------|----------|
| `EmptyBoard` | Delete all existing wiring, route from scratch |
| `CurrentProtectedWiring` | Keep existing wiring, protect it from modification |
| `CurrentUnprotectedWiring` | Keep existing wiring, allow the router to modify it |

Set at board creation time. Inherited by `confirm` and `resume` (can be overridden).

> **Note:** The API guide section lists `KeepExisting` / `StartFromCurrent` as valid values,
> while the reference section lists `CurrentProtectedWiring` / `CurrentUnprotectedWiring`.
> We use `CurrentProtectedWiring` in production and it works. The guide values may be
> aliases or stale docs — worth confirming with DeepPCB if issues arise.

### Current implementation

In `deeppcb.py:_routing_type()`:

```
options["routingType"] (explicit override)
  -> constraints["preserve_existing_routing"] == True  -> "CurrentProtectedWiring"
  -> default                                           -> "EmptyBoard"
```

In `service.py:start_job()`: auto-detected from reuse block metadata — if any block has `internal_net_ids`, `preserve_existing_routing` is set automatically.

## 2. Placement constraints file (placement jobs)

### Schema (from `GET /api/v1/boards/constraints-schema`)

```json
{
  "decoupling_constraints": {
    "<component_id>-<pin_id>": [
      {
        "type": "decoupled_by | supported_by",
        "targets": ["<component_id>-<pin_id>"]
      }
    ]
  }
}
```

- **`decoupling_constraints`** — required top-level key, dict of pin-ref -> constraint list
- **Pin reference format** — `<component_id>-<pin_id>`, regex `^.+-[^-]+$`
- **Constraint types** — only two exist today:
  - `decoupled_by` — "place these capacitors near this power pin"
  - `supported_by` — semantics unclear from docs alone, likely a softer proximity hint
- **`targets`** — array of pin references, `minItems: 1`

### Example

```json
{
  "decoupling_constraints": {
    "U1-VCC": [
      {"type": "decoupled_by", "targets": ["C1-1", "C2-1"]}
    ],
    "U1-AVCC": [
      {"type": "decoupled_by", "targets": ["C4-1"]}
    ]
  }
}
```

### Workflow

1. Build JSON matching the schema above
2. Validate: `POST /api/v1/boards/check-constraints` (upload file or URL, exactly one)
3. Upload file: `POST /api/v1/files/uploads/board-file` -> get URL
4. Pass URL in confirm: `PATCH /api/v1/boards/{id}/confirm` with `constraintsFileUrl`

### Current implementation

`deeppcb.py:_inject_constraints_file_url()` handles the full pipeline:
- Only runs for Placement jobs
- Reads `request.constraints["decoupling_constraints"]`
- Writes `deeppcb_constraints.json` to work_dir
- Validates via API
- Uploads and injects URL into `request.options["constraintsFileUrl"]`

### What we don't do yet

Nobody populates `decoupling_constraints` automatically. The constraint dict has to be manually provided in `ato.yaml` or via the API `constraints` parameter. The plumbing works end-to-end but there's no automatic extraction from the design.

## 3. Other API endpoints for constraints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/boards/constraints-schema` | GET | Returns the JSON schema (what's documented above) |
| `/api/v1/boards/check-constraints` | POST | Validates a constraints file against the schema |
| `/api/v1/boards/{boardId}/workflow/{workflowId}/constraints` | GET | Downloads constraints applied to a specific workflow run |

The workflow constraints endpoint is useful for debugging — you can see exactly what constraints were active during a particular placement run.

## Path forward

### Short term — wire up decoupling constraints from the graph

The ato compiler already knows which capacitors decouple which power pins (via `decoupled_by` trait / net connectivity). We should:

1. **Extract decoupling relationships from the faebryk graph** after compilation, producing a dict of `{power_pin_ref: [cap_pin_refs]}`.
2. **Map graph node names to DeepPCB component IDs** (the KiCad footprint references that appear in the `.deeppcb` JSON).
3. **Inject into `merged_constraints["decoupling_constraints"]`** in `service.py`, similar to how we auto-detect `preserve_existing_routing`.

This would make every placement job automatically benefit from decoupling-aware placement without any manual constraint authoring.

### Medium term — `supported_by` for other proximity relationships

The `supported_by` constraint type could map to other design relationships:
- Pull-up/pull-down resistors near their associated ICs
- Series termination resistors near drivers
- ESD protection near connectors

Same extraction approach: traverse the graph for known patterns, emit `supported_by` constraints.

### Longer term — richer constraint types

The schema endpoint only returns `decoupled_by` and `supported_by` today. If DeepPCB adds more constraint types (keep-out zones, layer restrictions, spacing rules — all mentioned in their docs as "defines schemas for" but not yet in the actual schema), we'd want to:

- Re-fetch the schema periodically or at startup
- Map new constraint types to ato language constructs (e.g., `assert placement.layer is "F.Cu"`)
- Potentially expose a constraint authoring UI in the sidebar

### Integration with reuse blocks

Reuse blocks already preserve internal routing via `routingType: CurrentProtectedWiring`. A natural extension is to also emit placement constraints for the synthetic reuse block components — e.g., "keep the USB-C block's decoupling caps near its IC" even when those are collapsed into a single synthetic footprint. This would require understanding which pins of the synthetic component correspond to power nets.
