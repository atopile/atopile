# Next 20 Autopick Candidates (JLC Scrub)

Data source:

- `/Users/narayanpowderly/projects/atopile/src/backend/components/.cache/jlcparts_playground/raw/cache.sqlite3`

Method:

- Counted from `v_components` with `stock > 0` (in-stock only).
- Grouped JLC category/subcategory aliases into normalized families.
- Compared against current autopick support (`resistor`, `capacitor`, `capacitor_polarized`, `inductor`, `diode`, `led`, `bjt`, `mosfet`) and current stdlib classes.

Generated:

- 2026-02-15 (UTC)

## Missing Stdlib Definitions (Highest Impact)

These are high-value JLC families where we do not currently have a dedicated atomic stdlib component class.

| Proposed class | JLC family (normalized) | In-stock count |
|---|---|---:|
| `TVS_Diode` | `TVS` | 9,168 |
| `TactileSwitch` | `Tactile Switches` | 7,703 |
| `ESD_Protection_Diode_Array` | `ESD ... (TVS/ESD)` | 4,856 |
| `FerriteBead` | `Ferrite Beads` | 3,008 |
| `USBConnector` | `USB Connectors` | 2,909 |
| `CommonModeChoke` | `Common Mode Filters` | 2,414 |
| `Varistor` | `Varistors` | 2,359 |
| `DIPSwitch` | `DIP Switches` | 1,190 |

Notes:

- `CAN`/`RS485` have protocol-level stdlib definitions, but not dedicated transceiver atomic parts.
- `LDO`/`DC-DC` map to regulator abstractions today; dedicated classes would make autopick schemas cleaner.

## Proposed Next 20 to Implement for Autopick

Ranking balances practical circuit value, in-stock depth, and schema feasibility from JLC attributes.

| Rank | Candidate | Stdlib status | In-stock | Suggested MVP filter params (for fast table) |
|---:|---|---|---:|---|
| 1 | LDO regulator | partial | 9,569 | `output_voltage`, `max_input_voltage`, `output_current`, `dropout_voltage`, `output_type` |
| 2 | TVS diode | no | 9,168 | `vrwm`, `breakdown_voltage`, `clamp_voltage`, `ipp` |
| 3 | Tactile switch | no | 7,703 | `mounting_style`, `actuator_style`, `height`, `pins` |
| 4 | DC-DC converter | partial | 6,822 | `input_voltage_range`, `output_voltage`, `output_current`, `switching_frequency`, `topology` |
| 5 | Crystal (passive) | yes (`Crystal`) | 5,978 | `frequency`, `load_capacitance`, `tolerance_ppm`, `stability_ppm` |
| 6 | ESD protection diode/array | no | 4,856 | `vrwm`, `clamp_voltage`, `channels`, `package` |
| 7 | OpAmp | yes (`OpAmp`) | 4,191 | `supply_range`, `gbw`, `input_offset_voltage`, `output_current`, `channels` |
| 8 | Fuse (resettable/PTC) | yes (`Fuse`) | 3,231 | `hold_current`, `trip_current`, `max_voltage`, `max_current` |
| 9 | Crystal oscillator / TCXO / VCXO | yes (`Crystal_Oscillator`) | 3,074 | `frequency`, `supply_voltage`, `output_type`, `stability_ppm` |
| 10 | Ferrite bead | no | 3,008 | `impedance_at_freq`, `current_rating`, `dcr_max` |
| 11 | USB connector | no | 2,909 | `usb_type`, `contacts`, `mounting_style`, `orientation` |
| 12 | Common-mode choke/filter | no | 2,414 | `current_rating`, `impedance`, `dcr_max`, `lines` |
| 13 | Varistor (MOV) | no | 2,359 | `varistor_voltage`, `clamp_voltage`, `energy`, `surge_current` |
| 14 | Fuse (disposable) | yes (`Fuse`) | 2,035 | `current_rating`, `voltage_rating`, `breaking_capacity`, `time_curve` |
| 15 | Resistor network/array | yes (`ResistorArray`) | 1,456 | `resistance`, `tolerance`, `power`, `array_topology`, `elements` |
| 16 | DIP switch | no | 1,190 | `positions`, `circuit`, `pitch`, `mounting_style` |
| 17 | EEPROM | partial | 1,134 | `memory_size`, `interface`, `vcc_range`, `frequency` |
| 18 | RS-485/RS-422 transceiver | partial | 911 | `data_rate`, `vcc_range`, `driver_receiver_count`, `duplex` |
| 19 | Comparator | yes (`Comparator`) | 595 | `vcc_range`, `input_offset_voltage`, `response_time`, `output_type`, `channels` |
| 20 | CAN transceiver | partial | 535 | `data_rate`, `vcc_range`, `standby_current`, `fault_protection` |

## Why these 20

- They are broadly useful in real boards (power, timing, protection, analog, interface).
- JLC has enough in-stock depth to avoid brittle picks.
- JLC attributes have enough structure to make deterministic prefilters possible.

## Immediate implementation order (suggested)

1. Add pickers for existing stdlib classes first: `Crystal`, `Crystal_Oscillator`, `OpAmp`, `Comparator`, `Fuse`, `ResistorArray`.
2. Add dedicated stdlib classes for: `TVS_Diode`, `ESD_Protection_Diode_Array`, `FerriteBead`, `CommonModeChoke`, `Varistor`.
3. Add regulator subclasses for clear picker schemas: `LDO`, `DCDC`.
4. Add interface-IC atomic classes: `RS485Transceiver`, `CANTransceiver`.
5. Add electromechanical classes last: `TactileSwitch`, `DIPSwitch`, `USBConnector`.

## Caveats

- JLC taxonomy is fragmented (same logical part family appears in multiple category trees).
- Attribute naming varies by family and sometimes by vendor (normalization layer required).
- Counts above are from current local mirror and will move with daily refreshes.
