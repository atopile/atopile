# Capacitor Autopick Plan

Stdlib component:

- `/Users/narayanpowderly/projects/atopile/src/faebryk/library/Capacitor.py`

## JLC Scope

Category/subcategory:

- `Capacitors`:
  - `Film Capacitors`
  - `Multilayer Ceramic Capacitors MLCC - Leaded`
  - `Through Hole Ceramic Capacitors`
  - `Aluminum Electrolytic Capacitors - Leaded`
  - `Multilayer Ceramic Capacitors MLCC - SMD/SMT`
  - `Polymer Aluminum Capacitors`
  - `Aluminum Electrolytic Capacitors - SMD`
  - `Ceramic Disc Capacitors`
  - `Horn-Type Electrolytic Capacitors`
  - `Polypropylene Film Capacitors (CBB)`
  - `Tantalum Capacitors`

## Required Filters (Fast Table)

- `stock > 0`
- package present (`package` not empty, not `-`)
- parseable:
  - `capacitance_f`
  - `tolerance_pct`
  - `max_voltage_v`

## Optional Filters

- `tempco_code` (important for MLCC; often missing on non-ceramic capacitor families).

## Current Counts

- raw rows in scope: `917,911`
- in-stock + valid package: `40,165`
- strict pickable rows in current fast DB: `30,091`

## Data Notes

- Similar to resistors: parser quality is acceptable.
- Biggest losses are stock/package and missing tolerance/voltage fields.
