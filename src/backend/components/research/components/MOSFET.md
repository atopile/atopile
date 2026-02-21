# MOSFET Autopick Plan

Stdlib component:

- `/Users/narayanpowderly/projects/atopile/src/faebryk/library/MOSFET.py`

## JLC Scope

Category/subcategory:

- `Triode/MOS Tube/Transistor`, `Transistors`, `Transistors/Thyristors`:
  - `MOSFETs`
  - `MOSFET`

Exclude:

- multi-device mixed rows if channel type is ambiguous (`N + P` combos) for MVP single-transistor picker.

## Proposed Filter Strategy

Hard required (MVP fast table):

- `stock > 0`
- package present (`package` not empty, not `-`)
- parseable:
  - `channel_type` (`N_CHANNEL` / `P_CHANNEL`)
  - `max_drain_source_voltage_v` (`Vdss`)
  - `max_continuous_drain_current_a` (`Id`)
  - `on_resistance_ohm` (`Rds(on)`)

Optional:

- `gate_source_threshold_voltage_v` (`Vgs(th)`)
- `max_power_w` (`Pd`)
- `saturation_type` (if we can infer reliably; likely low confidence from JLC text)

## Counts

- raw rows in scope: `61,711`
- in-stock + valid package: `18,803`
- with current parser:
  - hard-required set + Vgs(th): `16`
- with planned normalization:
  - hard-required set: `8,943`
  - hard-required set + Vgs(th): `8,227`
  - split of hard-required set:
    - N-channel: `6,535`
    - P-channel: `2,408`

## Data Notes (Important)

Major parser gap today comes from composite formatting:

- `Rds(on)` examples: `1.5Ω@10V,500mA`, `110mΩ@4.5V,3A`
- channel type examples:
  - `1 N-channel`
  - `1 Piece P-Channel`
  - mixed: `1 N-Channel + 1 P-Channel`

Normalization requirements:

- parse numeric+unit before `@` for resistance/voltage/current fields
- robust channel classifier from noisy `Type` strings
- reject mixed-channel rows for MVP single-device picker
