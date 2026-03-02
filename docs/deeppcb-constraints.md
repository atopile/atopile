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

## What's available in the graph today

### Bypass capacitors on power rails — easy to extract

There is no explicit `decoupled_by` trait in the graph. But bypass capacitors are connected via a well-known pattern:

```ato
power.hv ~> cap ~> power.lv
```

This creates `EdgeInterfaceConnection` edges from the capacitor's two terminals to the power rail's `hv` and `lv` `Electrical` nodes. Every capacitor bridging a power rail is discoverable by:

1. Enumerate all `ElectricPower` instances (via `F.ElectricPower.bind_typegraph(tg).get_instances()`)
2. For each, traverse `hv`/`lv` connected interfaces (via `_is_interface.get().get_connected()`)
3. Walk parents of connected electricals to find `Capacitor` modules
4. Map to KiCad references via `PCB_Transformer.map_footprints()` (matches `atopile_address` property on footprints)

**The ID problem:** DeepPCB constraint pin references use the format `<component_id>-<pin_id>`, where component IDs are `<Reference>@@<atopile_address>` (e.g., `C1@@app.power.bypass`) and pin IDs are pad names (e.g., `P1`, `P2`). The constraint extraction would need to happen _after_ the DeepPCB board JSON is built (since it defines the component/pin IDs), or use the same ID generation logic (`_component_id()` + `_pin_id()`).

**Practical approach:** Extract during `from_kicad_file()` in the transformer, where we already have both the KiCad PCB (with footprints, pads, nets) and are building the DeepPCB board JSON. We know every component's ID and every pin's ID at that point. Walk the nets: if a net connects an IC power pin to a capacitor pad, emit a `decoupled_by` constraint. Return the constraints dict alongside the board JSON.

**Open question:** How do we distinguish "bypass cap on a power rail" from "bulk input cap on a regulator" or "AC coupling cap on a signal"? All are capacitors bridging two nets. Options:
- Only emit `decoupled_by` when both nets are on the same `ElectricPower` interface (hv + lv of the same rail). This is the cleanest signal — a cap bridging `power.hv` to `power.lv` is definitionally a bypass cap.
- Use the graph's `is_source` / `is_sink` traits to identify power supply rails vs signal paths.
- Fall back to KiCad net names: nets named `VCC`, `+3V3`, `GND`, etc.

The first option (same `ElectricPower` interface) is the most reliable and doesn't require heuristics.

### Pull-up/pull-down resistors — easy to extract

The graph has explicit pull-up/pull-down tracking via three traits:

- **`can_be_pulled`** (`library/can_be_pulled.py`) — on `ElectricSignal`/`ElectricLogic` interfaces. Records `reference` (the power rail) and `line` (the signal). The `pull()` method creates a `Resistor` as a composition child of the owner, named `pull_up_<signal>` or `pull_down_<signal>`.
- **`has_pulls`** (`library/has_pulls.py`) — stored on the signal after pulling. Returns `(up_resistor, down_resistor)` via pointers.
- **`requires_pulls`** (`library/requires_pulls.py`) — design check that verifies pulls exist with appropriate resistance.

**Extraction is straightforward:**
1. For all nodes with `has_pulls` trait, call `get_pulls()` -> `(up_resistor, down_resistor)`
2. The resistor's parent in the composition tree (via `get_parent()`) is the owner IC
3. Map both to KiCad references -> emit `supported_by` constraint: the pull resistor "supports" the signal's IC

**This is the easiest win** because the relationship is _already explicit_ in the graph. No heuristics needed. The `has_pulls` trait directly links resistor -> signal -> owner.

### What needs more thought

#### Net-based proximity (no explicit trait)

Many placement-relevant relationships are implicit in net connectivity:
- Series termination resistors (connected in-line on a signal) — no trait, just two-pin connection
- ESD/TVS diodes near connectors — no trait, just shared net
- Filter components (RC, LC) — no trait

These _could_ be extracted by analyzing net topology (short nets = components should be close), but there's no structural marker distinguishing "this resistor terminates a signal" from "this resistor is a voltage divider". We'd need either:
- Heuristics based on component values and net topology
- New traits in the library (e.g., `is_series_termination`, `is_protection`)
- User annotation in `.ato` files

**Recommendation:** Don't try to extract these automatically yet. Focus on the two cases where we have explicit graph data (bypass caps, pull resistors).

#### Constraint pin reference matching

The constraint JSON uses `<component_id>-<pin_id>` references that must exactly match what's in the DeepPCB board JSON. With `provider_strict=True`, component IDs include the `@@atopile_address` suffix. Pin IDs may have a `P` prefix for single-character pad names.

This means constraint extraction must use the same `_component_id()` and `_pin_id()` functions as the board export. The cleanest integration point is inside the transformer's `from_kicad_file()`, where both are available.

#### Placement vs routing job type

Constraints are only applied during Placement jobs (`jobType: "Placement"`). Currently our default is Routing. If we want decoupling constraints, we either need:
- A two-pass flow: Placement first (with constraints), then Routing
- Or acceptance that constraints only apply when users explicitly request Placement jobs

#### Reuse block constraints

Reuse blocks collapse multiple components into a single synthetic footprint. Constraints _within_ a reuse block (e.g., "C1 decouples U1 inside the USB-C block") are meaningless to DeepPCB since those components don't exist in the collapsed board. Constraints _between_ reuse blocks and other components would work, but the pin IDs on synthetic components are synthetic too — they'd need to map to the external-facing pins of the reuse block.

## Path forward

### Phase 1 — bypass cap `decoupled_by` (ready to build)

All data is available. Implementation:

1. In `transformer.py:from_kicad_file()`, after building `pins_by_net`, walk the nets to find capacitors bridging the same power rail (both terminals on same `ElectricPower`'s hv/lv nets).
2. For each IC power pin on that rail, collect the capacitor pin refs -> build `decoupled_by` entries.
3. Return the constraints dict from `from_kicad_file()` (new output alongside the board JSON).
4. In `service.py`, inject into `merged_constraints["decoupling_constraints"]`.

**Challenge:** We operate on the KiCad PCB, not the live graph. The PCB doesn't have `ElectricPower` objects — it just has nets. So we need either:
- (a) Pass graph info into the transformer (adds a dependency)
- (b) Use net name heuristics on the PCB side (e.g., find capacitors where both pads are on nets that share a common power-ground pair)
- (c) Build a separate extraction step that runs on the graph before PCB export and passes results through

Option (c) is cleanest — run extraction on the graph, produce a `decoupling_constraints` dict keyed by atopile addresses, then translate to DeepPCB component IDs in the transformer.

### Phase 2 — pull resistor `supported_by` (ready to build)

1. Query `has_pulls` trait across all signal interfaces.
2. For each pull resistor, identify the owner IC and the signal.
3. Emit `supported_by` constraint: `"<IC_ref>-<signal_pin>": [{"type": "supported_by", "targets": ["<R_ref>-<pin>"]}]`

Same integration pattern as Phase 1.

### Phase 3 — net topology heuristics (needs design)

For components without explicit traits (series termination, ESD, filters), we'd need to either:
- Add new library traits and update standard library modules
- Build heuristic extraction based on component type + net connectivity
- Or expose an ato-level annotation for users to declare proximity relationships

This is lower priority since it requires either library changes or speculative heuristics.
