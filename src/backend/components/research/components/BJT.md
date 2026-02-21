# BJT Autopick Plan (NPN/PNP)

Stdlib component:

- `/Users/narayanpowderly/projects/atopile/src/faebryk/library/BJT.py`

## JLC Scope

Category/subcategory:

- `Triode/MOS Tube/Transistor`, `Transistors`, `Transistors/Thyristors`:
  - `Bipolar Transistors - BJT`
  - `Bipolar (BJT)`
  - `Transistors (NPN/PNP)`

Exclude:

- digital transistors, darlington arrays, IGBTs, TRIACs.

## Proposed Filter Strategy

Hard required (MVP fast table):

- `stock > 0`
- package present (`package` not empty, not `-`)
- parseable:
  - `doping_type` (`NPN` / `PNP`)
  - `max_collector_emitter_voltage_v` (`Vceo`)
  - `max_collector_current_a` (`Ic`)
  - `max_power_w` (`Pd`)

Optional:

- `dc_gain_hfe`
- `vce_sat_v`

## Counts

- raw rows in scope: `17,803`
- in-stock + valid package: `5,758`
- with current parser:
  - hard-required set + hFE: `47`
- with planned normalization:
  - hard-required set: `3,957`
  - hard-required set + hFE: `3,718`
  - split of hard-required set:
    - NPN: `2,376`
    - PNP: `1,581`

## Data Notes (Important)

Major parser gap today on gain format:

- examples: `100@10mA,1V`, `220@2mA,5V`

Need BJT-specific normalization:

- extract the first numeric token for `hFE`
- preserve full condition string in metadata if needed

Key aliases:

- `Transistor Type` / `Transistor type` / `type`
- `Collector-Emitter Breakdown Voltage (Vceo)` (plus case variants)
- `Collector Current (Ic)` / `Current - Collector(Ic)`
- `Power Dissipation (Pd)` / `Pd - Power Dissipation`
- `DC Current Gain (...)` variants
