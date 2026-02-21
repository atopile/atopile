# Resistor Autopick Plan

Stdlib component:

- `/Users/narayanpowderly/projects/atopile/src/faebryk/library/Resistor.py`

## JLC Scope

Category/subcategory:

- `Resistors`:
  - `Chip Resistor - Surface Mount`
  - `Through Hole Resistors`
  - `Current Sense Resistors/Shunt Resistors`
  - `Current Sense Resistors / Shunt Resistors`

## Required Filters (Fast Table)

- `stock > 0`
- package present (`package` not empty, not `-`)
- parseable:
  - `resistance_ohm`
  - `tolerance_pct`
  - `max_power_w`
  - `max_voltage_v`

## Optional Filters

- `tempco_ppm` when available.

## Current Counts

- raw rows in scope: `1,320,456`
- in-stock + valid package: `76,115`
- strict pickable rows in current fast DB: `50,800`

## Data Notes

- Data is already usable enough with current parser and key aliases used in stage-2.
- Main remaining losses are stock/package/parameter absence, not parser format issues.
