# Typed Connector Interfaces for Multiboard Harness Connections

## Process guidelines
**Take your time with this design.** There are no time constraints. This is a foundational architectural change that touches every layer of the multiboard system — from the ato language through the build system to the 3D viewer. Rushing will create technical debt that compounds across all these layers.

- **Verify every assumption** by reading the actual code before implementing. Don't assume patterns — confirm them.
- **Validate each phase with end-to-end tests** before moving to the next. Run `ato dev test` after every meaningful change, not just at the end.
- **Build incrementally**: get traits registered and compiling first; then get the example building; then update the manifest; then the viewer. Each phase must pass tests independently.
- **If you think you're done, you're not.** After "finishing", run the full test suite again, build the example, open the viewer, and manually verify the complete flow. Check edge cases: what happens with unconnected harnesses? Multiple harnesses? Same board connected to two harnesses?
- **Read before writing**: before modifying any file, read it fully. Before creating a new file, read 2-3 existing files that follow the same pattern to ensure consistency.

---

## Context
The multiboard system currently models cables as pure electrical passthroughs (`Electrical[4]` arrays) with no concept of physical connectors. Cable-board connections in the manifest are hardcoded to `boards[0]`→`boards[-1]`. We want to introduce typed connector interfaces that:
- Represent the physical mating point between a PCB and a harness
- Carry both the component (footprint/part) and the electrical pin interface
- Enforce gender compatibility (plug vs receptacle) via DRC
- Flow through to the manifest and 3D viewer for accurate cable endpoint rendering

### Key design decisions (from user interview)
- **Gender**: Same connector type for both genders; `is_plug`/`is_receptacle` type-level traits; DRC validates opposite genders on connected pairs
- **Component**: Connector interface IS a module carrying the footprint/part
- **Naming**: Rename `is_cable` → `is_harness`
- **Mating**: `~` works at the `Electrical` pin level (same type); connector-level DRC validates family + gender
- **Scope**: Full stack (traits → build → manifest → viewer)

### Constraint: `~` requires exact type match
The `~` operator's ERC enforces same-type connections. Two different connector types (e.g. `JST_SH_4_Plug` vs `JST_SH_4_Receptacle`) cannot be directly `~` connected. Instead, system-level wiring connects individual `Electrical` pins through connectors, and a DRC check validates that the connectors on each end have compatible gender and family.

---

## Files to modify/create

### New library traits (Python)
- `src/faebryk/library/is_harness.py` — marker trait (replaces `is_cable`)
- `src/faebryk/library/is_connector.py` — marker trait for connector modules
- `src/faebryk/library/is_plug.py` — gender marker trait
- `src/faebryk/library/is_receptacle.py` — gender marker trait

### Library registration
- `src/faebryk/library/_F.py` — add exports for new traits
- `src/atopile/compiler/ast_visitor.py` — register new symbols in stdlib

### Build system
- `src/atopile/build_steps.py` — rename `is_cable`→`is_harness` references; update manifest generation to include connector info and correct from/to topology
- `src/atopile/cross_board_drc.py` — rename `is_cable`→`is_harness`; add connector gender/family DRC

### Example updates
- `examples/multiboard_led/elec/src/ribbon_cable.ato` — use `is_harness`, add connector types on each end
- `examples/multiboard_led/elec/src/driver_board.ato` — add connector module for harness port
- `examples/multiboard_led/elec/src/led_panel.ato` — add connector module for harness port
- `examples/multiboard_led/elec/src/system.ato` — update wiring to go through connector pins

### Manifest + Viewer
- `src/vscode-atopile/src/ui/multiboard-viewer.ts` — parse connector info; draw cables from connector positions

---

## Implementation

### Phase 1: Define new traits

Create 4 new trait files following the exact pattern of `is_cable.py` / `is_board.py`:

```python
# src/faebryk/library/is_harness.py
class is_harness(fabll.Node):
    """Harnesses are excluded from PCB layout and represent physical wiring between boards."""
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type()).put_on_type()
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()

# is_connector.py, is_plug.py, is_receptacle.py — same pattern
```

Register all 4 in `_F.py` (exports) and `ast_visitor.py` (stdlib symbols, ~line 127).

Keep `is_cable` as a deprecated alias for `is_harness` (both work, DRC checks for either).

### Phase 2: Define connector modules in the example

Create connector types in `.ato` (example-level, not yet library):

```ato
# examples/multiboard_led/elec/src/connectors.ato
#pragma experiment("TRAITS")
import Electrical
import is_connector
import is_plug
import is_receptacle

module JST_SH_4_Receptacle:
    trait is_connector
    trait is_receptacle
    pins = new Electrical[4]

module JST_SH_4_Plug:
    trait is_connector
    trait is_plug
    pins = new Electrical[4]
```

Note: These are the SAME pin structure but different types (with different gender traits). They won't be `~` connected directly — system-level wiring goes through `.pins[i]`.

### Phase 3: Update example modules

**driver_board.ato** — add a connector:
```ato
from "connectors.ato" import JST_SH_4_Receptacle
module DriverBoard:
    trait is_board
    harness_out = new JST_SH_4_Receptacle
    harness_out.pins[0] ~ power_out.hv
    harness_out.pins[1] ~ power_out.lv
    harness_out.pins[2] ~ data_out
```

**led_panel.ato** — add a connector:
```ato
from "connectors.ato" import JST_SH_4_Receptacle
module LEDPanel:
    trait is_board
    harness_in = new JST_SH_4_Receptacle
    harness_in.pins[0] ~ power.hv
    harness_in.pins[1] ~ power.lv
    harness_in.pins[2] ~ data_in
```

**ribbon_cable.ato** — use `is_harness` + plug connectors:
```ato
from "connectors.ato" import JST_SH_4_Plug
module RibbonCable4:
    trait is_harness
    side_a = new JST_SH_4_Plug
    side_b = new JST_SH_4_Plug
    side_a.pins[0] ~ side_b.pins[0]
    side_a.pins[1] ~ side_b.pins[1]
    side_a.pins[2] ~ side_b.pins[2]
    side_a.pins[3] ~ side_b.pins[3]
```

**system.ato** — wire through connector pins:
```ato
module LEDSystem:
    trait is_multiboard
    driver = new DriverBoard
    panel = new LEDPanel
    cable = new RibbonCable4

    # Board connector pins ↔ cable connector pins
    driver.harness_out.pins[0] ~ cable.side_a.pins[0]
    driver.harness_out.pins[1] ~ cable.side_a.pins[1]
    driver.harness_out.pins[2] ~ cable.side_a.pins[2]

    cable.side_b.pins[0] ~ panel.harness_in.pins[0]
    cable.side_b.pins[1] ~ panel.harness_in.pins[1]
    cable.side_b.pins[2] ~ panel.harness_in.pins[2]
```

### Phase 4: Update build system

**`build_steps.py`** — `generate_system_3d` (line ~945):
1. Replace `is_cable` with `is_harness` (also accept `is_cable` for backward compat)
2. For each harness, trace the graph to find which `is_board` modules its connector pins connect to (replacing the hardcoded `boards[0]`/`boards[-1]`)
3. Include connector names in the manifest:

```json
{
  "version": "1.1",
  "type": "multiboard",
  "boards": [
    { "name": "driver", "build_target": "driver", "glb_path": "..." }
  ],
  "harnesses": [
    {
      "name": "cable",
      "type": "RibbonCable4",
      "from": { "board": "driver", "connector": "harness_out" },
      "to": { "board": "panel", "connector": "harness_in" }
    }
  ]
}
```

**`cross_board_drc.py`**:
1. Update to check for `is_harness` (in addition to `is_cable`)
2. Add new DRC rule: for each pair of connected connectors (one on a board, one on a harness), validate that one has `is_plug` and the other has `is_receptacle`

### Phase 5: Update manifest types + viewer

**`multiboard-viewer.ts`**:
1. Update `CableEntry` interface to match new manifest format (rename to `HarnessEntry`, add connector names)
2. Cable endpoints use board GLB origin for now (connector positions from KiCad PCB extraction is a future enhancement)
3. Rename "cable" references to "harness" in the viewer UI

---

## Verification (after EACH phase, not just at the end)

### After Phase 1 (traits):
- `ato dev test` passes — no regressions from adding new traits
- New traits are importable in a `.ato` file: `import is_harness`, `import is_connector`, etc.
- `is_cable` still works (backward compat)

### After Phase 2 (connector modules):
- The `connectors.ato` file compiles without errors
- `JST_SH_4_Plug` and `JST_SH_4_Receptacle` can be instantiated in a test module
- Both have the expected traits (verify with graph inspection or test)

### After Phase 3 (example modules):
- `ato build -t driver` and `ato build -t led_panel` succeed — individual board builds still work
- `ato build -t system` succeeds — system build compiles with the new wiring
- Cross-board DRC passes (signals still route through harness modules)
- The electrical connectivity is preserved: nets that previously connected through the cable still connect

### After Phase 4 (build system):
- Generated manifest JSON has correct topology: `from`/`to` derived from graph traversal, not hardcoded
- Manifest includes connector names
- Test with: unconnected harness (cable2), multiple harnesses, harness connecting same board twice
- `ato dev test` still passes

### After Phase 5 (viewer):
- Open the Multiboard 3D viewer in VS Code for the multiboard_led example
- Boards render correctly, harness lines connect between the right boards
- Dragging boards still works, harness lines follow
- Labels show correct harness/board names

### DRC validation (manual):
- Temporarily make a gender mismatch (two receptacles connected) → DRC should warn
- Temporarily remove a harness from a cross-board path → existing cross-board DRC should catch it

### Final end-to-end:
- Clean build from scratch: delete build artifacts, rebuild everything
- Full test suite passes
- Viewer works correctly with the rebuilt artifacts
