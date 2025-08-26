## PCB Rules Generator Spec (Ato ➜ KiCad)

### Goal

Generate KiCad board rules from atopile/Faebryk design intent so that layout constraints are consistent with the electrical spec. Initial scope:

- Differential impedance-driven width and spacing
- Current-driven single-ended trace width
- Differential signal length matching (time skew in ps)

### Inputs

- **Design graph**: `Module app`, `Solver solver` (resolved values and constraints)
- **Stackup**: An instance of `F.Stackup` (see `src/faebryk/library/Stackup.py`) present in the design
  - `layers[i].material: str` (e.g. "FR4", "Copper", "Solder Mask")
  - `layers[i].thickness: um` (unitful)
- **Fabrication constraints** (optional, composable like Stackup): module carrying vendor minimums/capabilities
  - Examples: `min_track_mm`, `min_space_mm`, `min_drill_mm`, `mask_min_mm`, `copper_weight_oz_per_layer`, `microvia_allowed: bool`
  - Defaults applied if not provided (see Defaults and Formatting)
- **Interface-level requirements** discovered via introspection on known library types (see Detection below). Examples (fields are indicative; actual names come from `Electrical.py`, `Ethernet.py`, etc.):
  - Differential links (e.g., `F.Ethernet`, or any interface exposing a differential pair):
    - `target_impedance_diff: ohm`
    - Optional `target_impedance_single: ohm`
    - `max_skew_ps: ps` (pair skew budget; prefer this name)
  - Single-ended/current-carrying nets (e.g., `F.Electrical`, `F.ElectricPower`):
    - `current: A` on `Electrical` (first milestone)
    - Optional pass-through on `ElectricPower` to forward to `hv`/`lv` (future convenience)
    - Back-compat: accept `required_current_continuous: A` if present
    - Optional `allowed_temp_rise_C: C` (fallback default)
  - Length-matching groups (e.g., clock/data buses):
    - `group_id: str` to correlate nets
    - `match_window_ps: ps` (intra-group timing window)

### Outputs

- A KiCad rules file at: `<layout_dir>/<layout_basename>.kicad_dru`
  - File format per `src/faebryk/exporters/pcb/rules/rule_syntax.txt`
  - First clause: `(version 1)`
  - Then one or more `(rule ...)` clauses with constraints and conditions

### High-level Flow

1. Discover stackup: `stackup = first(app.get_children_modules(types=F.Stackup))`; if none, return (no file written).
2. Collect rule intents by scanning the graph for known interfaces and their annotated parameters.
3. For each intent, compute physical parameters using stackup and solver (widths, gaps, length/skew limits).
4. Emit KiCad rules mapped to the appropriate objects and conditions.
   - Differential pairs: emit per-layer constraints using `(layer "<L>")` (outer: microstrip, inner: stripline default).
5. Write aggregated rules to `.kicad_dru` in the active build's layout folder.

### Detection (Interfaces ➜ Rule Intents)

- Differential pairs:
  - Identify interfaces that either:
    - Are instances of `F.Ethernet` or another library type exposing a differential pair, or
    - Carry a trait like `has_differential_pair` with pins/lines `p`, `n` (implementation detail up to library)
  - Read fields: `target_impedance_diff`, optional `target_impedance_single`, `max_skew_ps`.
  - Resolve which layer/regime applies (external microstrip vs internal stripline) based on routing preference if present.
  - If unspecified:
    - For outer layers: assume microstrip referenced to the adjacent plane (mask + FR4 above/below)
    - For inner layers: assume symmetric stripline with both adjacent planes used as reference planes (default assumption to refine later)
- Current-driven traces:
  - Identify `F.Electrical`/`F.ElectricPower` interfaces that expose `required_current_continuous` (or equivalent).
  - Map those to nets/footprints via graph utilities (`A.hasNetclass`, net names, or component classes) for conditions.
- Length-matching groups:
  - Nets/interfaces that share a `group_id` and specify `match_window_ps`.
  - For differential pairs, `max_skew_ps` applies between the two polarities.

### Calculations

All calculations use unit-safe values extracted via `solver`, falling back to documented defaults when not specified.

- Differential impedance ➜ width/gap

  - Determine regime:
    - External layers (copper adjacent to solder mask and FR4): microstrip with effective dielectric `ε_eff`.
    - Internal layers (copper between dielectrics): symmetric stripline using adjacent dielectric thicknesses.
  - Use closed-form approximations (implementation detail):
    - Microstrip: Hammerstad–Jensen for single-ended; compute odd-mode for differential; iterate to solve width and gap for `Z_diff` target. Use stackup copper thickness and dielectric thickness from the nearest plane reference.
    - Stripline: Wheeler or Hammerstad approximations for single-ended; odd-mode conversion for differential.
  - Output one width (track_width) and one gap (diff_pair_gap). Provide min/opt/max where applicable; at a minimum, set `opt` and mirror to `min` if we want hard enforcement.
  - Emit per-layer rules: generate a rule per layer where the pair may be routed.

- Current ➜ minimum width (IPC-2152-inspired)

  - Inputs: `I` (A), copper thickness `t` (from layer), allowable temp rise `ΔT` (default e.g. 10°C if unspecified), environment (assume external vs internal factor).
  - Use a simplified IPC-2152 curve-fit or lookup to derive minimum width `W_min` for given `I, t, ΔT`. Start with a conservative approximation; later we can refine/replace with a better model.
  - Clamp `W_min` by fabrication minimums if a fabrication module is present; otherwise clamp to a global default (e.g., 0.15 mm).
  - Emit `(constraint track_width (min W_min))` conditions for matched nets/netclasses; optionally add `(layer "<L>")` when per-layer copper thickness differs.

- Time skew (ps) ➜ length window
  - Convert time window to physical length using propagation velocity:
    - `v ≈ c0 / sqrt(ε_eff)`; choose `ε_eff` per regime as above.
    - `ΔL_max = v * Δt`
  - Differential-pair skew: set `(constraint skew (max ΔL_max))` for the pair condition.
  - Bus/group matching: for each `group_id`, set `(constraint length (min L_min) (max L_max))` or `(skew (max ΔL_max))` depending on requirement semantics.
  - Emit per-layer if propagation velocity materially differs across layers (optional, phase 2).

### Defaults and Formatting

- Materials and parameters when missing:
  - FR4 `εr = 4.2`, solder mask `εr = 3.3`
  - Outer copper thickness 1 oz (35 µm) unless otherwise specified
  - Default ΔT = 10°C if not specified
  - Minimum manufacturable width default = 0.15 mm (clamped)
- Numeric formatting:
  - Emit distances in mm with "mm" suffix, rounded to 0.01 mm by default
  - Use ps only in calculations; no ps literals in the .dru file

### Vendor presets (JLCPCB minimal)

- Include minimal JLCPCB stackup presets for 2/4/6/8 layers (single flavor each) in `Stackup.ato`:
  - `JLC2Layer`, `JLC4Layer`, `JLC6Layer`, `JLC8Layer`
  - Each defines materials and thicknesses:
    - Outer: Solder mask (~30 µm), Copper (default 35 µm), FR4 dielectric (remaining thickness)
    - Inner (if present): alternating Copper (~15–35 µm) and FR4 for symmetric striplines
  - Copper defaults: 1 oz outer (35 µm), 0.5–1 oz inner (15–35 µm)
- Add a minimal fabrication constraints module `JLCFabrication` with typical minimums for standard service:
  - `min_track_mm`, `min_space_mm`, `min_drill_mm`, `mask_min_mm`, `copper_weight_oz_per_layer`
- Visual options (silkscreen/mask color) are out-of-scope for this milestone and can be added later.

### Rule Mapping to KiCad Syntax

- File header: `(version 1)`
- Differential impedance:
  - Width: `(constraint track_width (opt <width>))`
  - Gap: `(constraint diff_pair_gap (opt <gap>))`
  - Uncoupled length limit (optional): `(constraint diff_pair_uncoupled (max <len>))`
  - Per-layer scoping: add `(layer "F.Cu")`, `(layer "In1.Cu")`, etc., emitting separate rules per layer as needed
  - Condition examples:
    - By diff-pair name: `(condition "A.inDiffPair('/CLK')")`
    - By netclass: `(condition "A.hasNetclass('HS_DIFF')")`
- Current width:
  - `(constraint track_width (min <width>))`
  - Conditions:
    - By component class (power): `(condition "A.hasNetclass('Power')")`
    - Or by reference patterns: `(condition "A.Reference == 'J*' || A.Reference == 'FUSE*'")`
- Length/skew:
  - Differential skew: `(constraint skew (max <len>))` with condition `A.inDiffPair('*')` scoped to specific pairs
  - Group skew/length: use netclass or explicit list via component class or sheet membership

### Exporter API (Python)

Location: `src/faebryk/exporters/pcb/rules/rules.py`

- `export_rules(app: Module, solver: Solver) -> None`

  - Orchestrates discovery, computation, and writing of the `.kicad_dru` file
  - Steps:
    1. Get stackup; if none, return (no-op)
    2. intents = `collect_rule_intents(app, solver, stackup)`
    3. rules = `generate_rules(intents, stackup, solver)` ➜ list[str]
    4. `write_rules_file(rules, output_path)`

- Helper structure (suggested):

  - `@dataclass class DiffPairIntent { name: str; Zdiff: ohm; Zsingle: ohm|None; max_skew_ps: float|None; layer_hint: str|None }`
  - `@dataclass class CurrentIntent { selector: Selector; current_A: float; deltaT_C: float|None; layer_hint: str|None }`
  - `@dataclass class LengthMatchIntent { group_id: str; window_ps: float; selector: Selector }`
  - `class Selector`: encapsulates how to emit a KiCad condition string for the targeted items (e.g., by netclass, by diff-pair name, by component class). Provides `to_condition() -> str`.

- Key functions:
  - `collect_rule_intents(app, solver, stackup) -> list[Intent]`
  - `solve_width_gap_from_impedance(Zdiff, stackup, layer_hint=None) -> tuple[width, gap]`
  - `solve_min_width_from_current(I, stackup, deltaT=None, layer_hint=None) -> width`
  - `time_ps_to_length(ps, stackup, layer_hint=None) -> length`
  - `emit_rule(name: str, clauses: list[str]) -> str` builds one `(rule ...)` s-expression
  - `write_rules_file(rules: list[str], path: Path) -> None`

### targets.py integration

- Target: `rules` (alias: `stackup`)
  - Implementation: call `export_rules(app, solver)`
  - Output path: If `config.build.paths.layout` present, write to `layout.parent / f"{layout.stem}.kicad_dru"`; otherwise fallback to `config.build.paths.output_base.with_suffix('.kicad_dru')`
  - Error policy: if multiple `Stackup` instances exist, raise `NotImplementedError` for now; if none, quietly no-op.

### Rule Ordering

- Emit generic constraints first (global/current-based netclasses), then more specific (per diff-pair, per group), and finally per-layer specializations. Later rules override earlier ones per KiCad precedence.

### Error Handling & Defaults

- If required parameters are missing on an interface:
  - Skip that rule intent and log a warning identifying the interface and missing field(s).
- If stackup data is incomplete:
  - Use conservative defaults: FR4 `εr = 4.2`, solder mask `εr = 3.3`, copper thickness from standard 1 oz if unknown (35 µm), and an external microstrip regime on the top layer.
- Unit handling:
  - Use unit-safe values from `solver`; when emitting values, format in KiCad-friendly units (mm or mil) as strings where necessary.

### Examples

Rule file header:

```
(version 1)
```

Differential pair (Ethernet 100 Ω) on outer layer with computed width/gap:

```
(rule ethernet_dp
  (constraint track_width (opt 0.18mm))
  (constraint diff_pair_gap (opt 0.20mm))
  (condition "A.inDiffPair('/ETH')"))
```

Current-driven width for power netclass:

```
(rule power_width
  (constraint track_width (min 1.00mm))
  (condition "A.hasNetclass('Power')"))
```

Differential skew budget of 10 ps:

```
(rule eth_skew
  (constraint skew (max 1.5mm))
  (condition "A.inDiffPair('/ETH')"))
```

### Testing Strategy

- Unit tests for calculators:
  - `solve_width_gap_from_impedance` returns sane values across regimes (top vs inner) and common Zdiff (85/90/100 Ω)
  - `solve_min_width_from_current` monotonic in I and t, spot-check against IPC-2152 references
  - `time_ps_to_length` correctness for representative ε_eff
- Integration test:
  - Build a tiny app graph with a `Stackup`, one diff-pair with `target_impedance_diff`, and one power net with `required_current_continuous`.
  - Run `export_rules` and assert the `.kicad_dru` file contains expected clauses/values.
  - Current-first milestone tests:
    - Annotate several `Electrical` interfaces with `.current`; verify grouping by net, max current selection, per-layer width calculation with fabrication clamps, and rule emission.

### Future Extensions

- Per-layer overrides and netclass mapping emitted automatically from Ato traits
- Zone connection constraints for high-current pads
- EMI-aware keepouts using `physical_clearance` on zones/edges
- Autogenerated netclasses from interface traits to simplify conditions
- Fabrication presets for common vendors (e.g., JLCPCB 4+/6+/8+ layers with price add options) and a cost model to estimate price impact from selected constraints

### Codebase refactors / housekeeping

- Move `DifferentialSignal`/`DifferentialSignals` out of `Ethernet.py` into their own modules; update imports and re-run `tools/library/gen_F.py` to regenerate `_F.py` stubs.
