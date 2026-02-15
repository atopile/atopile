# Diode Autopick Plan

Stdlib component:

- `/Users/narayanpowderly/projects/atopile/src/faebryk/library/Diode.py`

## JLC Scope

Category/subcategory:

- `Diodes`:
  - `Schottky Barrier Diodes (SBD)`
  - `Schottky Diodes`
  - `Diodes - General Purpose`
  - `Switching Diode`
  - `Switching Diodes`
  - `Diodes - Fast Recovery Rectifiers`
  - `Fast Recovery / High Efficiency Diodes`
  - `Fast Recovery/High Efficiency Diode`
  - `High Effic Rectifier`
  - `Bridge Rectifiers`

Exclude for generic-diode MVP:

- `Zener Diodes`, TVS/ESD-only families, gas discharge types.

## Proposed Filter Strategy

Hard required (MVP fast table):

- `stock > 0`
- package present (`package` not empty, not `-`)
- parseable:
  - `forward_voltage_v`
  - `reverse_working_voltage_v`
  - `max_current_a`

Optional:

- `reverse_leakage_current_a`

## Counts

- raw rows in scope: `58,482`
- in-stock + valid package: `16,103`
- with current parser:
  - hard-required set: `562`
  - with reverse leakage current: `538`
- with planned normalization:
  - hard-required set: `10,976`
  - with reverse leakage current: `10,111`

## Data Notes (Important)

Large parser gap today: values are often in forms like:

- `1.25V@150mA`
- `850mV@3A`

Current parser misses most `@`-suffixed values. We need diode-specific extraction:

- parse numeric+unit before `@`
- keep trailing condition data only in metadata/debug fields, not core numeric column

Key aliases needed:

- `Forward Voltage (Vf@If)` / `Voltage - Forward(Vf@If)` / `Forward Voltage (Vf) @ If`
- `Reverse Voltage (Vr)` / `Voltage - DC Reverse(Vr)`
- `Rectified Current` / `Average Rectified Current (Io)` / `Current - Rectified`
- `Reverse Leakage Current (Ir)` / `Reverse Leakage Current` / `Ir - Reverse Current`
