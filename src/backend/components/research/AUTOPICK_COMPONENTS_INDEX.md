# Autopick Component Research (JLC)

Data source:

- `/Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground/raw/cache.sqlite3`

Generated:

- 2026-02-15 (UTC)

Scope:

- Standard-library discrete components we likely want to add to autopick next:
  - `Resistor`
  - `Capacitor`
  - `CapacitorPolarized`
  - `Inductor`
  - `Diode`
  - `LED`
  - `BJT` (NPN/PNP split)
  - `MOSFET`

## Summary Counts

| Component | Raw scope rows | In-stock + valid package | Pickable with current parsing | Pickable with planned normalization |
|---|---:|---:|---:|---:|
| Resistor | 1,320,456 | 76,115 | 50,800 | 50,800 |
| Capacitor | 917,911 | 40,165 | 30,091 | 30,091 |
| CapacitorPolarized | 193,317 | 17,246 | 13,817 | 13,817 |
| Inductor | 143,486 | 24,329 | 15,163 (core) / 84 (all 5 attrs) | same (field sparsity, not parser-limited) |
| Diode | 58,482 | 16,103 | 538 (all 4 attrs) | 10,111 (all 4 attrs) |
| LED | 49,245 | 4,813 | 513 | 513 (mostly stock/scope-limited) |
| BJT | 17,803 | 5,758 | 47 (with hFE) | 3,718 (with hFE) |
| MOSFET | 61,711 | 18,803 | 16 (with Vgs) | 8,227 (with Vgs) |

Notes:

- `current parsing` means what our existing stage-2 numeric parser can extract today.
- `planned normalization` means adding component-specific normalization for JLC strings like `1.1V@1A` and enum cleanup for type fields.

## Per-Component Docs

- `/Users/narayanpowderly/projects/atopile/src/backend/components/research/components/RESISTOR.md`
- `/Users/narayanpowderly/projects/atopile/src/backend/components/research/components/CAPACITOR.md`
- `/Users/narayanpowderly/projects/atopile/src/backend/components/research/components/CAPACITOR_POLARIZED.md`
- `/Users/narayanpowderly/projects/atopile/src/backend/components/research/components/INDUCTOR.md`
- `/Users/narayanpowderly/projects/atopile/src/backend/components/research/components/DIODE.md`
- `/Users/narayanpowderly/projects/atopile/src/backend/components/research/components/LED.md`
- `/Users/narayanpowderly/projects/atopile/src/backend/components/research/components/BJT.md`
- `/Users/narayanpowderly/projects/atopile/src/backend/components/research/components/MOSFET.md`
