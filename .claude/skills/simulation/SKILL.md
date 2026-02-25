---
name: simulation
description: "How to add SPICE simulation requirements to an atopile design, run them via `ato build`, interpret results, and iterate on the design until all requirements pass. Use when adding simulation-based verification to a circuit."
---

# Simulation Requirements

Atopile can automatically run SPICE simulations during `ato build` to verify that a circuit meets its requirements. Requirements are declared in `.ato` files, attached to the design, and checked against ngspice simulation results.

## Prerequisites

ngspice must be installed on the build machine:
- macOS: `brew install ngspice`
- Linux: `apt install ngspice`

## Relevant Files

| File | Role |
|------|------|
| `src/faebryk/library/Requirement.py` | The `Requirement` node class — defines all fields and getters |
| `src/faebryk/library/Simulations.py` | Simulation node classes: `SimulationTransient`, `SimulationSweep`, `SimulationAC`, `SimulationDCOP` |
| `src/faebryk/library/Plots.py` | Plot node classes: `LineChart`, `BarChart` |
| `src/faebryk/exporters/simulation/ngspice.py` | SPICE netlist generator and ngspice runner |
| `src/atopile/build_steps.py` | Build step registration, requirement verification, plot rendering |

## Architecture

Requirements reference simulations by name. Two patterns:

1. **1:1 Sim-Per-Requirement** (model-validation style): Each requirement has its own dedicated simulation. Best for independent validation tests.
2. **Shared Simulations** (design-validation style): Multiple requirements reference the same simulation. Best when measuring different aspects of the same circuit state (e.g., inductor current ripple, average current, and duty cycle from one sweep).

```ato
import SimulationTransient
import LineChart
import Requirement

module MyValidation:
    dut = new MyCircuit

    # --- REQ_001: Output Voltage ---
    sim_001 = new SimulationTransient
    sim_001.duts = "dut"
    sim_001.spice = "V1 dut.power_in.hv 0 DC 12"
    sim_001.time_stop = 10ms
    sim_001.time_step = 1us

    plot_001 = new LineChart
    plot_001.title = "Output Voltage"
    plot_001.x = "time"
    plot_001.y = "dut.power_out.hv"
    plot_001.simulation = "sim_001"

    req_001 = new Requirement
    req_001.req_name = "REQ_001: Output Voltage"
    req_001.simulation = "sim_001"
    req_001.net = "dut.power_out.hv"
    req_001.measurement = "final_value"
    assert req_001.limit within 4.75V to 5.25V
    req_001.required_plot = "plot_001"
```

### Pattern structure

Each requirement block has three parts:
1. **Simulation**: defines the circuit stimulus and time window
2. **Plots**: declares visualizations (LineChart, BarChart)
3. **Requirement**: specifies what to measure and the pass/fail bounds

## Simulation Types

### SimulationTransient

Single transient analysis.

```ato
sim = new SimulationTransient
sim.duts = "dut"                    # DUT instance name (enables dot notation)
sim.spice = "V1 dut.power_in.hv 0 PULSE(0 12 0 10u 10u 10 10)"
sim.time_start = 5ms                # measurement window start (sim still runs from t=0)
sim.time_stop = 10ms                # simulation stop time
sim.time_step = 100ns               # timestep
sim.remove_elements = "R5"          # comma-separated elements to remove from netlist
sim.extra_spice = "Iload dut.power_out.hv 0 DC 5"  # pipe-separated extra SPICE lines
```

### SimulationSweep

Parametric sweep — runs transient analysis N times, varying a parameter.

```ato
sweep = new SimulationSweep
sweep.duts = "dut"
sweep.param_name = "ILOAD"                    # parameter name
sweep.param_values = "0.5,1,2,3,4,5"          # comma-separated values
sweep.param_unit = "A"                         # unit for display
sweep.spice = "V1 dut.power_in.hv 0 PULSE(0 12 0 10u 10u 10 10)"  # fixed source
sweep.remove_elements = "R5"
sweep.extra_spice_template = "I_LOAD dut.power_out.hv 0 DC {ILOAD}"  # {PARAM} substituted
sweep.time_start = 5ms
sweep.time_stop = 5.5ms
sweep.time_step = 100ns
```

**Key distinction: `spice` vs `spice_template`, `extra_spice` vs `extra_spice_template`**
- `spice` / `extra_spice`: used as-is (no parameter substitution)
- `spice_template` / `extra_spice_template`: `{PARAM}` placeholders are replaced with sweep values
- Use `_template` variants when the sweep parameter appears in the SPICE source definition
- Pipe `|` separates multiple SPICE lines in any of these fields

You can also sweep ato design parameters:

```ato
sweep.param_name = "dut.switching_frequency"  # ato parameter path
sweep.param_values = "400e3,800e3,1200e3"
sweep.param_unit = "Hz"
```

### SimulationAC

AC small-signal analysis (Bode plots).

```ato
ac_sim = new SimulationAC
ac_sim.duts = "dut"
ac_sim.spice = "V1 dut.power_in.hv 0 DC 12 AC 0"
ac_sim.start_freq = 100
ac_sim.stop_freq = 10e6
ac_sim.points_per_dec = 100
```

### SimulationDCOP

DC operating point analysis.

```ato
dc_sim = new SimulationDCOP
dc_sim.duts = "dut"
dc_sim.spice = "V1 dut.power_in.hv 0 DC 12"
```

### Common Simulation Fields

| Field | Description | Example |
|-------|-------------|---------|
| `duts` | DUT instance name(s), comma-separated. Enables dot notation in SPICE lines. | `"dut"`, `"dut_400k"` |
| `spice` | Fixed SPICE source definition (pipe-separated for multiple lines) | `"V1 net 0 DC 12"` |
| `extra_spice` | Additional fixed SPICE elements (pipe-separated) | `"Iload net 0 DC 5"` |
| `remove_elements` | Comma-separated element names to remove from auto-generated netlist | `"R5,R3"` |
| `time_start` | Measurement window start time (simulation runs from t=0) | `5ms` |
| `time_stop` | Simulation stop time | `10ms` |
| `time_step` | Simulation timestep | `100ns` |

### The `duts` Field

When `duts` is set, the system:
1. Generates a SPICE netlist scoped to the DUT subtree
2. Resolves `dut.power_in.hv` in SPICE lines to actual net names (e.g., `dut_power_in_hv`)
3. Resolves `{dut.power_in.voltage}` to the parameter value (e.g., `12`)
4. Resolves SPICE model parameters via `param_bindings` (e.g., `FS=400000.0`)

**Always use `duts` when your circuit has a DUT wrapper module.**

## Requirement Fields

### Limits — `assert req.limit within X to Y`

Use `assert` with the `limit` NumericParameter for pass/fail bounds:

```ato
assert req.limit within 4.75V to 5.25V       # absolute range
assert req.limit within 5V +/- 10%            # percentage tolerance
assert req.limit within 0s to 5ms             # time range
assert req.limit within 0A to 6A              # current range
```

This replaces the deprecated `min_val`/`max_val`/`typical` string fields.

### Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `req_name` | Human-readable identifier | `"REQ_001: Output voltage"` |
| `simulation` | Name of the simulation node (ato variable name) | `"sim_001"` |
| `net` | Net name to measure (dot notation or SPICE expression) | `"dut.power_out.hv"`, `"i(l1)"` |
| `limit` | Pass/fail bounds via `assert ... within` | See above |
| `measurement` | What to compute from simulation data | `"final_value"` |

### Optional Fields

| Field | Description | Example |
|-------|-------------|---------|
| `justification` | Why this requirement exists | `"DS Table 1: Vout +/-5%"` |
| `required_plot` | Comma-separated plot variable names (shown prominently) | `"plot_001"` |
| `supplementary_plot` | Comma-separated plot variable names (shown secondary) | `"plot_001b,plot_001c"` |

### Transient-specific fields (on Requirement)

| Field | Description | Example |
|-------|-------------|---------|
| `tran_step` | Override simulation timestep | `"1e-4"` |
| `tran_stop` | Override simulation stop time | `"1.0"` |
| `tran_start` | Measurement window start (skip startup transient) | `"0.5"` |
| `settling_tolerance` | Fraction of final value for settling band (default 1%) | `"0.02"` |

### AC-specific fields (on Requirement)

| Field | Description | Example |
|-------|-------------|---------|
| `ac_start_freq` | Start frequency in Hz | `"0.01"` |
| `ac_stop_freq` | Stop frequency in Hz | `"1000"` |
| `ac_points_per_dec` | Points per decade | `"100"` |
| `ac_source_name` | Source to apply `AC 1` to | `"V1"` |
| `ac_measure_freq` | Evaluation frequency for gain_db/phase_deg | `"10"` |
| `ac_ref_net` | Input net for transfer function (Vout/Vin) | `"input"` |
| `diff_ref_net` | Differential reference net | `"ref_neg"` |

### Circuit modification fields (on Requirement or Simulation)

| Field | Description | Example |
|-------|-------------|---------|
| `extra_spice` | Pipe-separated SPICE lines to inject | `"R_LOAD out 0 50"` |
| `remove_elements` | Comma-separated elements to remove | `"R5,C3"` |

## Measurement Types

### Time-domain measurements (transient/DCOP)

| Value | Description | Bounds |
|-------|-------------|--------|
| `"final_value"` | Last data point or operating point | V or A |
| `"average"` | Mean over measurement window | V or A |
| `"settling_time"` | Time to settle within tolerance of final value | seconds |
| `"peak_to_peak"` | Max minus min | V or A |
| `"overshoot"` | Peak above final value as percentage | % |
| `"rms"` | Root mean square | V or A |
| `"frequency"` | Signal frequency via rising-edge counting | Hz |
| `"max"` | Maximum value in measurement window | V or A |
| `"min"` | Minimum value in measurement window | V or A |
| `"envelope"` | Min/max envelope across sweep points | V or A |

### Frequency-domain measurements (AC)

| Value | Description | Bounds |
|-------|-------------|--------|
| `"gain_db"` | Gain in dB at `ac_measure_freq` | dB |
| `"phase_deg"` | Phase in degrees at `ac_measure_freq` | degrees |
| `"bandwidth_3db"` | Frequency where gain drops 3dB | Hz |
| `"bode_plot"` | Full Bode plot; bounds check DC gain | dB |

## Plot Types

### LineChart

```ato
plot = new LineChart
plot.title = "Output Voltage Startup"
plot.x = "time"                           # "time", "frequency", or sweep param name
plot.y = "dut.power_out.hv"               # net, SPICE probe, or signal transform
plot.y_secondary = "i(l1)"               # optional secondary y-axis (dashed)
plot.color = "ILOAD"                      # optional: color by sweep param
plot.simulation = "sim_001"               # which simulation's data to use
plot.plot_limits = "false"                # "true" (default) or "false" to hide limit bands
```

### BarChart

```ato
bar = new BarChart
bar.title = "Peak-to-Peak vs Load"
bar.x = "ILOAD"                           # sweep parameter name
bar.y = "peak_to_peak(dut.power_out.hv)"  # measurement(net)
bar.simulation = "sim_001"
bar.plot_limits = "false"                  # hide limit bands for informational plots
```

### Y-axis signal transforms

These can be used in `plot.y` or `plot.y_secondary`:

| Transform | Description | Example |
|-----------|-------------|---------|
| `ac_coupled(net)` | Strip DC component from signal | `"ac_coupled(dut.power_out.hv)"` |
| `envelope(net)` | Min/max envelope across sweep points | `"envelope(ac_coupled(dut.power_out.hv))"` |
| `settling_time(net)` | Settling time measurement per sweep point | `"settling_time(dut.power_out.hv)"` |
| `peak_to_peak(net)` | Peak-to-peak measurement per sweep point | `"peak_to_peak(dut.power_out.hv)"` |
| `average(net)` | Average measurement per sweep point | `"average(dut.power_out.hv)"` |
| `max(net)` | Max measurement per sweep point | `"max(dut.power_out.hv)"` |
| `min(net)` | Min measurement per sweep point | `"min(dut.power_out.hv)"` |
| `i(element)` | Current through voltage source or inductor | `"i(l1)"`, `"i(v1)"` |

### Plot best practices

Make sure each plot clearly shows the information needed to prove the requirement:

| Requirement type | Primary y | Secondary y | Notes |
|---|---|---|---|
| Load transient | `ac_coupled(dut.power_out.hv)` | `i(l1)` | AC-couple to see perturbation; show load current |
| Line transient | `ac_coupled(dut.power_out.hv)` | `dut.power_in.hv` | AC-couple Vout; show VIN step |
| Output/input ripple | `ac_coupled(dut.power_out.hv)` | `i(l1)` | AC-couple to see mV-scale ripple |
| Startup | `dut.power_out.hv` | `i(l1)` | Raw voltage (need to see 0→5V); show inrush |
| Low dropout | `dut.power_out.hv` | `i(l1)` | Raw voltage; show load current |
| Switching frequency | `dut.package.8` (SW) | — | Raw SW node for period counting |
| Load/line regulation | BarChart: `average(net)` | LineChart: `dut.power_out.hv` colored by sweep | Bar for measurement, line for waveforms |

### Plot-Requirement binding

Plots are top-level siblings of requirements. Requirements reference plots by ato variable name:

```ato
plot_vout = new LineChart       # ato variable name = "plot_vout"
plot_bar = new BarChart

req.required_plot = "plot_vout"              # shown prominently
req.supplementary_plot = "plot_bar"          # shown secondary
```

## Net Names

Use **dot notation** in requirement `net` fields and SPICE lines. The system sanitizes them automatically:

| Input | SPICE net name |
|-------|---------------|
| `dut.power_out.hv` | `dut_power_out_hv` |
| `dut.power_in.hv` | `dut_power_in_hv` |
| `dut.package.SW` | `dut_package_sw` |
| `i(l1)` | `i(l1)` (unchanged) |
| `i(v1)` | `i(v1)` (unchanged) |

**Current probes**: `i()` only works for voltage sources (`V*`) and inductors (`L*`). Do NOT probe current sources (`I*`) — this causes ngspice `wrdata` failures.

### CRITICAL: Case sensitivity in SPICE source strings

Net aliases are keyed **lowercase** (from `_sanitize_net_name()`), but `_resolve_dut_references()` preserves original case. This means uppercase pin names in `spice`/`extra_spice` create **ghost nets** that aren't connected to anything.

| Bad (creates ghost net) | Good (resolves correctly) |
|---|---|
| `dut.package.EN` → `dut_package_EN` ≠ alias `dut_package_en` | `dut.enable.line` → `dut_enable_line` ✓ |
| `dut.package.SW` in spice strings | `dut.package.8` or lowercase alternatives |

**Rule**: In `spice`, `extra_spice`, and `extra_spice_template` strings, use lowercase net paths. The `Requirement.net` field is safe because `_sanitize_net_name()` lowercases it.

### Finding element names

To discover SPICE element names (R1, C5, L1, X1, etc.):
1. Run `ato build` once
2. Check `build/builds/<name>/circuit.spice` (or `multidut_<dut>.spice` for multi-DUT)
3. Element names are assigned by component type and traversal order

## SPICE Source Specifications

| Pattern | Description |
|---------|-------------|
| `DC 12` | Constant 12V |
| `PULSE(0 12 0 10u 10u 10 10)` | Step from 0V to 12V (V1 V2 delay rise fall width period) |
| `PULSE(8 40 15e-3 1u 1u 5e-3 20e-3)` | VIN step 8V to 40V at 15ms |
| `DC 0 AC 1` | AC analysis stimulus (0V DC bias, 1V AC amplitude) |

Multiple SPICE lines are pipe-separated: `"V1 net 0 DC 12|Iload net 0 DC 5"`

## Complete Example — Buck Converter Validation

```ato
import SimulationTransient
import SimulationSweep
import LineChart
import BarChart
import Requirement

from "buck_converter.ato" import TPS54560_Reference

module ModelValidation:
    dut = new TPS54560_Reference

    # --- MV_001: Output Ripple CCM ---
    sim_001 = new SimulationTransient
    sim_001.duts = "dut"
    sim_001.spice = "V1 dut.power_in.hv 0 PULSE(0 12 0 10u 10u 10 10)"
    sim_001.remove_elements = "R5"
    sim_001.extra_spice = "Iload dut.power_out.hv 0 DC 5"
    sim_001.time_start = 10ms
    sim_001.time_stop = 10.1ms
    sim_001.time_step = 25ns

    plot_001 = new LineChart
    plot_001.title = "Output Ripple CCM"
    plot_001.x = "time"
    plot_001.y = "ac_coupled(dut.power_out.hv)"
    plot_001.y_secondary = "i(l1)"
    plot_001.simulation = "sim_001"

    req_001 = new Requirement
    req_001.req_name = "MV_001: Output Ripple CCM"
    req_001.simulation = "sim_001"
    req_001.net = "dut.power_out.hv"
    req_001.measurement = "peak_to_peak"
    assert req_001.limit within 0V to 25mV
    req_001.required_plot = "plot_001"

    # --- MV_002: Load Regulation ---
    sim_002 = new SimulationSweep
    sim_002.duts = "dut"
    sim_002.param_name = "ILOAD"
    sim_002.param_values = "0.5,1,2,3,4,5"
    sim_002.param_unit = "A"
    sim_002.spice = "V1 dut.power_in.hv 0 PULSE(0 12 0 10u 10u 10 10)"
    sim_002.remove_elements = "R5"
    sim_002.extra_spice_template = "I_LOAD dut.power_out.hv 0 DC {ILOAD}"
    sim_002.time_start = 10ms
    sim_002.time_stop = 10.5ms
    sim_002.time_step = 500ns

    plot_002_bar = new BarChart
    plot_002_bar.title = "Vout vs Load Current"
    plot_002_bar.x = "ILOAD"
    plot_002_bar.y = "average(dut.power_out.hv)"
    plot_002_bar.simulation = "sim_002"

    plot_002_vout = new LineChart
    plot_002_vout.title = "Output Voltage vs Load"
    plot_002_vout.x = "time"
    plot_002_vout.y = "dut.power_out.hv"
    plot_002_vout.color = "ILOAD"
    plot_002_vout.simulation = "sim_002"

    req_002 = new Requirement
    req_002.req_name = "MV_002: Load Regulation"
    req_002.simulation = "sim_002"
    req_002.net = "dut.power_out.hv"
    req_002.measurement = "average"
    assert req_002.limit within 4.85V to 5.15V
    req_002.required_plot = "plot_002_bar"
    req_002.supplementary_plot = "plot_002_vout"
```

## Build & Iterate Workflow

1. **Define requirements first** — before building, define what "correct" means
2. **`ato build`** — runs simulations and checks requirements
3. **Read results** — check `<build>.requirements.json` for pass/fail
4. **Diagnose failures**:
   - `actual` far from expected → wrong component values
   - `actual` close but out of bounds → widen bounds or adjust values
   - `actual = NaN` → net name doesn't exist (check `.spice` file)
   - Simulation timeout → check for floating nodes, add small load
5. **Iterate** — modify `.ato`, rebuild, repeat
6. **Check plots** — open generated HTML files in `build/builds/<name>/`

## Known Limitations

- Behavioral SPICE models can't validate power efficiency (ideal switches)
- Input ripple = 0 with ideal voltage source (no source impedance)
- `i()` probes only work for V-sources and inductors, not current sources (I*)
- Solver may widen `assert within` bounds slightly (e.g., 100mV → 200mV)
