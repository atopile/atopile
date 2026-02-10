# Schematic Symbol Standardization (Research + Initial Plan)

## Scope

Goal: "Drop a part -> it looks like the part" for generic atopile parts, without waiting on PCB footprint generation.

This note covers:

- standards and conventions to align with,
- practical symbol options used in KiCad libraries,
- a concrete replacement list for atopile standard-library categories,
- package-aware variant strategy and fallback behavior.

## Current State In Atopile

Today, the schematic viewer renders leaf parts as rounded cards with pin stubs (not category-specific symbols):

- `src/faebryk/exporters/schematic/schematic.py` exports `bodyWidth/bodyHeight/pins` and category metadata.
- `src/ui-server/src/schematic-viewer/three/ComponentRenderer.tsx` renders generic rounded boxes for all components.

This is a good base for layout, but not for semantic symbol appearance.

## Standards + Common Conventions

There are two practical symbol families teams use:

1. IEC style (global/default in many regions; e.g., rectangular resistor).
2. ANSI/US legacy style (e.g., zig-zag resistor).

For library behavior, KiCad KLC is useful and explicit:

- Generic symbols should keep the `Footprint` field empty.
- Footprint filters should still constrain valid package matches.
- Fully specified package variants can have separate symbols.

This maps well to our plan:

- keep a category default symbol even when package is unknown,
- optionally choose package-aware symbol variants when package is known.

## Recommendation

Use IEC-style as the default style pack, with optional US variants where KiCad provides them (`*_US` for resistor/capacitor families).

### Category defaults (no package yet)

- Resistor: `Device:R` (US alternative: `Device:R_US`)
- Capacitor (non-polarized): `Device:C` (US alternative: `Device:C_US`)
- Capacitor (polarized): `Device:C_Polarized` (US alternative: `Device:C_Polarized_US`)
- Inductor: `Device:L`
- Diode: `Device:D` (specializations: `Device:D_Schottky`, `Device:D_Zener`, `Device:D_TVS`)
- LED: `Device:LED`
- Connector: `Connector_Generic:Conn_01xN` or `Conn_02xN_*` by pin topology
- Testpoint: `Connector:TestPoint_Small` (alternatives: `TestPoint`, `TestPoint_Flag`)

## Package-aware variants

### Two-pin chip families (R/C/L/LED)

Use package suffix to drive geometry/style variant:

- `01005`, `0201`, `0402`, `0603`, `0805`, `1206`, `1210`, `2010`, `2512`
- map from footprint names like:
  - `R_0402_1005Metric`, `C_0603_1608Metric`, `L_0805_2012Metric`, `LED_0402_1005Metric`

Render behavior:

- keep the same schematic family symbol,
- apply package-specific visual modifiers (small/medium/large body profile, label density).

### Diode/TVS packages

Detect package family from footprint:

- `SOD-123`, `SOD-323`, `SOD-523`, `SOD-923`, `SMA`, `SMB`, `SMC`, `SOT-23`.

Render behavior:

- base symbol remains diode family (`D`, `D_Schottky`, `D_Zener`, `D_TVS`),
- add package badge (e.g., `SOD-123`) and keep explicit cathode marker visible.

### Connector packages

Use symbol structure from pin topology + package hints:

- `Conn_01xN` for single-row,
- `Conn_02xN_*` for dual-row,
- specialized package families can still receive package badge (`JST_PH`, `PinHeader_2.54`, `USB_C`, etc.).

### Testpoint packages

Package hint examples:

- `TestPoint_Pad_*`, `TestPoint_THTPad_*`, `TestPoint_Loop_*`, `TestPoint_Plated_Hole_*`.

Render behavior:

- default to `TestPoint_Small`,
- use alternate glyph if loop/plated-hole style is known.

## Polarity + Pin Markers (default-on)

- Diode/LED: clear cathode bar marker and pin-1 marker.
- Polarized capacitor: plus marker at positive pin (pin 1 by convention in chosen seed symbol).
- Connector: pin-1 emphasis by default (dot/notch/first-cell tint).
- Testpoint: single-pin marker always visible.

## Standard Library Component Replacement List (initial)

Map these atopile components/types to custom symbol rendering immediately:

1. `Resistor`
2. `Capacitor`
3. `CapacitorPolarized`
4. `Inductor`
5. `Diode`
6. `LED`
7. `TestPoint`
8. Connector-like components by type/designator (`J*`, `P*`, `USB_C`, pin headers, terminal blocks)

Optional second wave:

1. `ResistorArray`
2. `MultiCapacitor`
3. Multi-diode symbols (dual/bridge variants)

## Implementation Hook (minimal-change path)

Use `module type + optional package trait` resolver at export time and keep rendering deterministic.

### Exporter additions

In `src/faebryk/exporters/schematic/schematic.py`, add per-component fields such as:

- `symbolFamily` (`resistor`, `capacitor`, `capacitor_polarized`, `diode`, `led`, `inductor`, `connector`, `testpoint`)
- `symbolVariant` (`iec`, `us`, `schottky`, `zener`, etc.)
- `packageCode` (normalized: `0402`, `SOD-123`, `SOT-23`, ...)
- `pin1`, `polarity` (`anode/cathode`, `plus/minus`) where relevant

### Renderer

In `src/ui-server/src/schematic-viewer/three/ComponentRenderer.tsx`, replace generic body draw path with:

1. resolve symbol style from `symbolFamily + symbolVariant + packageCode`,
2. draw custom glyph primitives,
3. apply existing theme pack + selection/hover behavior.

Fallback rule:

- if package unknown, still draw the category symbol (never fallback to plain rounded rectangle for standard categories above).

## Primary References

- KiCad KLC S5.1: <https://klc.kicad.org/symbol/s5/s5.1/>
- KiCad KLC S5.2: <https://klc.kicad.org/symbol/s5/s5.2/>
- KiCad KLC S2.3: <https://klc.kicad.org/symbol/s2/s2.3/>
- KiCad KLC F3.1 (SMD chip naming): <https://klc.kicad.org/footprint/f3/f3.1/>
- KiCad KLC F3.2 (resistor naming): <https://klc.kicad.org/footprint/f3/f3.2/>
- KiCad KLC F3.3 (capacitor naming): <https://klc.kicad.org/footprint/f3/f3.3/>
- KiCad KLC F3.6 (connector naming): <https://klc.kicad.org/footprint/f3/f3.6/>
- KiCad symbols repo (examples: `R`, `R_US`, `C`, `C_US`, `C_Polarized`, `D`, `LED`, `TestPoint`): <https://gitlab.com/kicad/libraries/kicad-symbols>
- KiCad footprints repo (examples: `R_0402_1005Metric`, `C_0603_1608Metric`, `D_SOD-123`, `SOT-23-*`, `TestPoint_*`): <https://gitlab.com/kicad/libraries/kicad-footprints>
- IEC 60617 database entry point: <https://std.iec.ch/iec60617>
