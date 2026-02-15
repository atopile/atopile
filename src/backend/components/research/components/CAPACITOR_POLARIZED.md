# CapacitorPolarized Autopick Plan

Stdlib component:

- `/Users/narayanpowderly/projects/atopile/src/faebryk/library/CapacitorPolarized.py`

## JLC Scope

Category/subcategory:

- `Capacitors`:
  - `Aluminum Electrolytic Capacitors - Leaded`
  - `Aluminum Electrolytic Capacitors - SMD`
  - `Polymer Aluminum Capacitors`
  - `Tantalum Capacitors`
  - `Horn-Type Electrolytic Capacitors`
  - `Solid Capacitors`
  - `Solid Polymer Electrolytic Capacitor`
  - `Hybrid Aluminum Electrolytic Capacitors`
  - `Niobium Oxide Capacitors`

## Required Filters (Fast Table Candidate)

- `stock > 0`
- package present (`package` not empty, not `-`)
- parseable:
  - `capacitance_f`
  - `tolerance_pct`
  - `max_voltage_v`

## Optional Filters

- ESR / ripple-current fields (if we add these to the stdlib constraints later).

## Current Counts

- raw rows in scope: `193,317`
- in-stock + valid package: `17,246`
- strict pickable (capacitance+tolerance+voltage): `13,817`

## Data Notes

- This pool is healthy enough to implement soon.
- Treat this as a separate component family from generic `Capacitor` for better solver behavior around polarized constraints.
