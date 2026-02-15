# Inductor Autopick Plan

Stdlib component:

- `/Users/narayanpowderly/projects/atopile/src/faebryk/library/Inductor.py`

## JLC Scope

Category/subcategory:

- `Inductors/Coils/Transformers` and `Inductors, Coils, Chokes`:
  - `Power Inductors`
  - `Inductors (SMD)`
  - `Through Hole Inductors`
  - `Color Ring Inductors/Through Hole Inductors`
  - `Color Ring Inductors / Through Hole Inductors`
  - `Adjustable Inductors`
  - `HF Inductors`

Exclude:

- transformers/accessories/pre-ordered rows.

## Proposed Filter Strategy

Hard required (MVP fast table):

- `stock > 0`
- package present (`package` not empty, not `-`)
- parseable:
  - `inductance_h`
  - `max_current_a` (rated current)
  - `dc_resistance_ohm`

Optional (separate nullable columns):

- `saturation_current_a`
- `self_resonant_frequency_hz`
- `inductance_tolerance_pct`

## Counts

- raw rows in scope: `143,486`
- in-stock + valid package: `24,329`
- parseable hard-required set (`L + I + DCR`): `15,163`
- with `saturation_current` added: `6,175`
- with `self_resonant_frequency` added: `2,472`
- with all 5 (`L + I + DCR + Isat + SRF`): `84`

## Data Notes

- SRF data is very sparse; do not make it hard-required initially.
- Saturation current is also sparse enough to keep optional in MVP.
- Main JLC key aliases:
  - `Rated Current` / `Current Rating`
  - `DC Resistance (DCR)` / `DC Resistance` / `DC Resistance(DCR)`
  - `Saturation Current (Isat)` / `Current - Saturation ...`
