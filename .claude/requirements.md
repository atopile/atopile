# Integration

Simulations and Requirements are both fabll Nodes in the ato graph. During an ato build, after the pick-parts stage, the graph is filtered for any simulations, and if any are present, they are run. Once simulations are complete, the verify-requirements build stage searches the graph for requirements, links them to their simulation data, and evaluates pass/fail. After this, a report is generated per requirement with all metadata and graphs available, as well as an overall HTML report that contains all requirements and all plots.

## Two-Phase Architecture

The build pipeline has two registered steps that execute sequentially:

1. **`run-simulations`** (Phase 1): Discovers all nodes with `is_spice_simulation` trait, groups them by simulation scope (nearest ancestor with Electrical children), generates scoped SPICE netlists, and runs each simulation. Results are cached in `ctx._simulation_results` as `dict[name, (result, net_aliases)]`.

2. **`verify-requirements`** (Phase 2): Finds all `Requirement` nodes, looks up cached simulation data by the `simulation` field name, computes measurements, checks pass/fail against `[min_val, max_val]`, generates per-requirement plots and a combined HTML report.

## Build Configuration

To enable simulation verification, add a build target in `ato.yaml` whose entry points to the requirements module:

```yaml
builds:
  simulation:
    entry: requirements.ato:SimulationRequirements
    hide_designators: true
    exclude_checks: [PCB.requires_drc_check]
```

## Output Artifacts

- **Per-requirement HTML plots** — `req_<name_slug>.html` (interactive Plotly charts)
- **Combined HTML report** — `<build>.requirements.html` (cards + embedded plot iframes)
- **JSON data** — `<build>.requirements.json` (machine-readable results with time-series data for the UI)
- **SPICE netlist** — `<scope_slug>.spice` (generated netlist for each simulation scope)

## Key Source Files

| File | Purpose |
|------|---------|
| `src/faebryk/library/Simulations.py` | SimulationTransient, SimulationAC, SimulationDCOP, SimulationSweep node definitions |
| `src/faebryk/library/Requirement.py` | Requirement node definition with measurement/simulation resolution |
| `src/faebryk/library/Measurements.py` | Measurement type marker nodes (FinalValue, Overshoot, etc.) |
| `src/faebryk/library/Plots.py` | LineChart, BodePlotChart, SweepChart, EfficiencySweepChart render logic |
| `src/faebryk/library/is_spice_simulation.py` | Trait marking nodes as SPICE simulations (discovery + result caching) |
| `src/faebryk/library/is_requirement.py` | Trait marking nodes as requirements (discovery) |
| `src/faebryk/exporters/simulation/simulation_runner.py` | Phase 1: run simulations and cache results |
| `src/faebryk/exporters/simulation/requirement.py` | Phase 2: verify requirements, compute measurements, generate plots + reports |
| `src/faebryk/exporters/simulation/ngspice.py` | Circuit class (SPICE wrapper), SpiceNetlist, TransientResult, ACResult, OpResult |
| `src/atopile/build_steps.py` | Build pipeline registration (`run-simulations` + `verify-requirements` steps) |

---

# Simulation

Simulations are fabll Nodes that define how to configure and run a SPICE analysis. Each simulation type has the `is_spice_simulation` trait for uniform discovery.

## Simulation Types

### DC Operating Point (`SimulationDCOP`)
The simplest simulation — computes the DC steady-state of all node voltages and branch currents.

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `spice` | StringParameter | SPICE source line override, e.g. `"V1 node+ node- DC 12"` |
| `extra_spice` | StringParameter | Pipe-delimited extra SPICE lines to add, e.g. `"R_EXTRA n1 n2 100\|.ic V(out)=5"` |
| `remove_elements` | StringParameter | Comma-delimited element names to remove from netlist, e.g. `"R4,C5"` |

**Example ato:**
```ato
sim = new SimulationDCOP
sim.spice = "V1 power_in_hv 0 DC 12"
```

### Transient (`SimulationTransient`)
Time-domain simulation with configurable start/stop/step.

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `spice` | StringParameter | SPICE source line, e.g. `"V1 node+ node- PULSE(0 12 0 10u 10u 10 10)"` |
| `extra_spice` | StringParameter | Pipe-delimited extra SPICE lines |
| `remove_elements` | StringParameter | Comma-delimited element names to remove |
| `time_start` | StringParameter | Recording start time in seconds (bare number, e.g. `4e-3`) |
| `time_stop` | StringParameter | Simulation stop time in seconds (bare number, e.g. `5e-3`) |
| `time_step` | StringParameter | Time step in seconds (bare number, e.g. `5e-7`) |

**Example ato:**
```ato
tran_startup = new SimulationTransient
tran_startup.spice = "V1 dut_package_2 0 PULSE(0 12 0 10u 10u 10 10)"
tran_startup.time_step = 5e-7
tran_startup.time_stop = 5e-3
```

**With circuit modifications:**
```ato
tran_light = new SimulationTransient
tran_light.spice = "V1 dut_package_2 0 PULSE(0 12 0 10u 10u 10 10)"
tran_light.time_step = 50e-9
tran_light.time_stop = 6.02e-3
tran_light.time_start = 6e-3
tran_light.remove_elements = "R4"
tran_light.extra_spice = "R4_LIGHT dut_power_out_hv 0 2.5"
```

**With initial conditions:**
```ato
tran_prebias = new SimulationTransient
tran_prebias.spice = "V1 dut_package_2 0 PULSE(0 12 0 10u 10u 10 10)"
tran_prebias.time_step = 5e-7
tran_prebias.time_stop = 4e-3
tran_prebias.extra_spice = ".ic V(dut_power_out_hv)=3"
```

**With multiple extra SPICE lines (pipe-delimited):**
```ato
tran_load_step.extra_spice = "R4_LIGHT dut_power_out_hv 0 10|V_ISENSE load_sense 0 0|I_LOAD dut_power_out_hv load_sense PULSE(0 4.5 4.5e-3 1u 1u 10 10)"
```

### AC Small-Signal (`SimulationAC`)
Frequency-domain analysis for gain, phase, and bandwidth measurements.

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `spice` | StringParameter | AC source definition, e.g. `"V1 node+ node- DC 0 AC 1"` |
| `extra_spice` | StringParameter | Pipe-delimited extra SPICE lines |
| `remove_elements` | StringParameter | Comma-delimited element names to remove |
| `start_freq` | StringParameter | Start frequency in Hz (bare number) |
| `stop_freq` | StringParameter | Stop frequency in Hz (bare number) |
| `points_per_dec` | StringParameter | Points per decade (bare number, default 100) |

**Example ato:**
```ato
sim_ac = new SimulationAC
sim_ac.spice = "V1 input 0 DC 0 AC 1"
sim_ac.start_freq = 1
sim_ac.stop_freq = 10e6
sim_ac.points_per_dec = 100
```

### Parametric Sweep (`SimulationSweep`)
Runs a transient simulation N times varying a parameter. Each sweep point substitutes `{param_name}` in the template strings.

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `param_name` | StringParameter | Name of swept parameter, e.g. `"VIN"` |
| `param_values` | StringParameter | Comma-separated float values, e.g. `"6,8,12,24,48"` |
| `param_unit` | StringParameter | Display unit for plots, e.g. `"V"` |
| `spice_template` | StringParameter | SPICE source with `{param_name}` placeholders |
| `extra_spice_template` | StringParameter | Extra SPICE lines with `{param_name}` placeholders (pipe-delimited) |
| `spice` | StringParameter | Static SPICE source (used if no template) |
| `extra_spice` | StringParameter | Static extra SPICE lines (pipe-delimited) |
| `remove_elements` | StringParameter | Comma-delimited element names to remove |
| `time_start` | StringParameter | Recording start time |
| `time_stop` | StringParameter | Simulation stop time |
| `time_step` | StringParameter | Time step |

**Example ato (VIN sweep):**
```ato
sweep_duty_vin = new SimulationSweep
sweep_duty_vin.param_name = "VIN"
sweep_duty_vin.param_values = "6,8,12,24,48"
sweep_duty_vin.param_unit = "V"
sweep_duty_vin.spice_template = "V1 dut_package_2 0 PULSE(0 {VIN} 0 10u 10u 10 10)"
sweep_duty_vin.time_start = 4e-3
sweep_duty_vin.time_stop = 4.02e-3
sweep_duty_vin.time_step = 50e-9
```

**Example ato (load current sweep with circuit mods):**
```ato
sweep_load = new SimulationSweep
sweep_load.param_name = "ILOAD"
sweep_load.param_values = "0.5,1,2,3,5"
sweep_load.param_unit = "A"
sweep_load.time_start = 4e-3
sweep_load.time_stop = 4.5e-3
sweep_load.time_step = 5e-7
sweep_load.remove_elements = "R4"
sweep_load.extra_spice_template = "I_LOAD dut_power_out_hv 0 DC {ILOAD}"
```

**Example ato (component value sweep):**
```ato
sweep_ripple_l = new SimulationSweep
sweep_ripple_l.param_name = "L"
sweep_ripple_l.param_values = "1,2.2,4.7,10"
sweep_ripple_l.param_unit = "uH"
sweep_ripple_l.time_start = 4e-3
sweep_ripple_l.time_stop = 4.02e-3
sweep_ripple_l.time_step = 50e-9
sweep_ripple_l.remove_elements = "L1"
sweep_ripple_l.extra_spice_template = "L1_SWEEP dut_package_8 dut_power_out_hv {L}u"
```

## Common Simulation Config Fields

All simulation types share three common fields:

- **`spice`**: A SPICE source line in the format `"NAME NODE+ NODE- SPEC"`. The runner parses this with `split(None, 3)` and calls `circuit.set_source(name, spec)` where spec is everything after the two node names.
- **`extra_spice`**: Pipe-delimited (`|`) list of additional SPICE lines to add to the netlist. Each line is added with `circuit.add_element()`. Supports any SPICE directive including `.ic V(node)=value` for initial conditions.
- **`remove_elements`**: Comma-delimited list of element names to remove from the netlist. Removes by matching the uppercase element name prefix.

## SPICE Source Line Format

The `spice` field expects a full SPICE source definition: `"V1 node+ node- SPEC"`.

Common source specs:
- **DC**: `"V1 n+ n- DC 12"` — constant voltage
- **PULSE**: `"V1 n+ n- PULSE(V1 V2 TD TR TF PW PER)"` — pulsed source
  - V1=initial, V2=peak, TD=delay, TR=rise, TF=fall, PW=pulse width, PER=period
  - For a step from 0 to 12V: `"V1 n+ 0 PULSE(0 12 0 10u 10u 10 10)"`
  - For a step transient: `"V1 n+ 0 PULSE(12 18 4e-3 1u 1u 2e-3 10)"`
- **AC**: `"V1 n+ n- DC 0 AC 1"` — for AC analysis

## Simulation Runner Behavior

- All transient simulations use `uic=True` (Use Initial Conditions) which skips the initial DC operating point and enables `.ic` directives.
- When `signals=None`, the runner detects ALL node voltages AND branch currents (V/L elements) using `_detect_all_signals()`.
- All signal keys in results are **lowercase** — lookup is case-insensitive.
- Circuit state is saved/restored per simulation to isolate modifications between simulations.
- Sweep results are stored as `dict[float, TransientResult]` keyed by parameter value.

## Parameter Value Format

All numeric fields (`time_start`, `time_stop`, `time_step`, etc.) must be bare numbers in scientific notation (e.g. `5e-7`, `4e-3`). The compiler creates `Numbers` literals for these, and `_extract_float()` handles extraction with a fallback path.

**Do NOT use units** on simulation numeric fields — `StringParameter` with bare numbers is the only supported pattern.

## Net Name Conventions

SPICE net names are sanitized from ato addresses:
- Dots, brackets, whitespace become underscores: `power.hv` → `power_hv`, `a[0]` → `a_0`
- SPICE expressions like `i(v1)` are preserved unchanged (lowercased)
- Net aliases map ato addresses to canonical SPICE names via `net_aliases` dict

---

# Requirements

Requirements are fabll Nodes that define pass/fail criteria for simulation results. Each requirement references a simulation by name, specifies a net to measure, a measurement type, and min/max bounds. Requirements are discovered via the `is_requirement` trait.

## Requirement Fields

| Field | Type | Description |
|-------|------|-------------|
| `req_name` | StringParameter | Human-readable name, e.g. `"REQ-001: Startup output voltage"` |
| `simulation` | StringParameter | Name of sibling simulation node, e.g. `"tran_startup"` |
| `net` | StringParameter | Net to measure, e.g. `"dut.power_out.hv"` or `"i(L1)"` |
| `measurement` | StringParameter | Measurement type string (see below) |
| `min_val` | StringParameter | Minimum acceptable value (bare number) |
| `typical` | StringParameter | Typical expected value (bare number) |
| `max_val` | StringParameter | Maximum acceptable value (bare number) |
| `context_nets` | StringParameter | Comma-delimited additional nets for plot context, e.g. `"dut.package_2,i(L1)"` |
| `justification` | StringParameter | Free-text rationale for the requirement |
| `settling_tolerance` | StringParameter | Fraction for settling_time measurement, e.g. `0.02` for 2% band |
| `diff_ref_net` | StringParameter | Differential reference net for differential measurements |

### AC-Specific Fields (for requirements referencing SimulationAC)
| Field | Type | Description |
|-------|------|-------------|
| `ac_measure_freq` | StringParameter | Frequency to measure at (Hz) |
| `ac_ref_net` | StringParameter | Reference net for relative gain/phase |

### Sweep-Specific Fields (inline, for requirements not referencing a SimulationSweep node)
| Field | Type | Description |
|-------|------|-------------|
| `sweep_param_name` | StringParameter | Swept parameter name |
| `sweep_param_values` | StringParameter | Comma-separated parameter values |
| `sweep_param_unit` | StringParameter | Parameter display unit |
| `sweep_spice_template` | StringParameter | SPICE template with `{param}` placeholders |
| `sweep_extra_spice_template` | StringParameter | Extra SPICE template with `{param}` placeholders |
| `sweep_time_start/stop/step` | StringParameter | Override time config for sweep |

## Simulation Resolution

Requirements resolve their simulation data source through the `simulation` string field:

1. Read `req.simulation` to get the simulation name (e.g. `"tran_startup"`)
2. Walk up the parent chain looking for a sibling node with `is_spice_simulation` trait whose child name matches
3. In the two-phase architecture, cached results are looked up from `sim_results[sim_name]`

This is enabled by the module inheritance pattern in ato:

```ato
module SimulationRequirements from BuckConverterSims:
    # BuckConverterSims contains tran_startup, tran_ripple, etc.
    # Requirements can reference them by name:
    req.simulation = "tran_startup"
```

## Pass/Fail Criterion

A requirement **passes** when: `min_val <= actual <= max_val`

For sweep requirements, **all** sweep points must pass. The aggregate `actual` value is:
- For worst-case measurements (`peak_to_peak`, `overshoot`, `settling_time`): `max(actuals)`
- For all others: last value in the sweep

## Measurements

Measurements define what to compute from simulation data. Available types:

### Transient Measurements

| Measurement | String Key | Description | Unit |
|-------------|-----------|-------------|------|
| Final Value | `"final_value"` | Last data point of the signal | V or A |
| Average | `"average"` | Mean of signal over capture window | V or A |
| Settling Time | `"settling_time"` | Time for signal to settle within `settling_tolerance` of final value | s |
| Peak-to-Peak | `"peak_to_peak"` | max - min of signal | V or A |
| Overshoot | `"overshoot"` | `(peak - final) / |final| * 100%` | % |
| RMS | `"rms"` | Root mean square of signal | V or A |
| Frequency | `"frequency"` | Rising-edge threshold crossings with linear interpolation | Hz |
| Duty Cycle | `"duty_cycle"` | % time above midpoint threshold | % |
| Max | `"max"` | Maximum value of signal | V or A |
| Min | `"min"` | Minimum value of signal | V or A |
| Sweep | `"sweep"` | Final value (used as generic sweep measurement) | V or A |
| Efficiency | `"efficiency"` | `Pout / Pin * 100%` via energy integration | % |

### AC Measurements

| Measurement | String Key | Description | Unit |
|-------------|-----------|-------------|------|
| Gain (dB) | `"gain_db"` | Gain in dB at `ac_measure_freq` | dB |
| Phase (deg) | `"phase_deg"` | Phase in degrees at `ac_measure_freq` | deg |
| 3dB Bandwidth | `"bandwidth_3db"` | Frequency where gain drops 3dB below DC/peak | Hz |
| Bode Plot | `"bode_plot"` | DC gain check with full Bode visualization | dB |

### Measurement Details

**Efficiency** requires `context_nets` with exactly 3 entries:
- `context_nets[0]` = input current (e.g. `i(V1)`, negative in ngspice convention)
- `context_nets[1]` = input voltage (e.g. `dut.package_2`)
- `context_nets[2]` = output current (e.g. `i(V_LSENSE)`)

Efficiency is computed via energy integration: `E = sum(|V(t)*I(t)| * dt)` over the capture window.

**Settling Time** uses `settling_tolerance` as a fraction of the final value. Default is 0.01 (1%). Common values: 0.01 (1%), 0.02 (2%), 0.05 (5%).

**Frequency** counts rising-edge crossings above the midpoint threshold `(sig_min + sig_max) / 2` with linear interpolation for sub-sample accuracy. Requires at least 2 crossings.

**Duty Cycle** computes `% of samples above (sig_min + sig_max) / 2`. For a buck converter SW node, `D ~ Vout/Vin`.

## Requirement Examples

### Basic transient requirement (final value check)
```ato
req_output_voltage = new Requirement
req_output_voltage.req_name = "REQ-001: Startup output voltage"
req_output_voltage.simulation = "tran_startup"
req_output_voltage.net = "dut.power_out.hv"
req_output_voltage.min_val = 4.80
req_output_voltage.typical = 5.0
req_output_voltage.max_val = 5.20
req_output_voltage.measurement = "final_value"
req_output_voltage.context_nets = "dut.package_2,i(L1),dut.package_8"
req_output_voltage.justification = "WEBENCH: Vout=5V within 4%"
```

### Settling time with tolerance
```ato
req_settling = new Requirement
req_settling.req_name = "REQ-004: Startup settling time"
req_settling.simulation = "tran_startup"
req_settling.net = "dut.power_out.hv"
req_settling.min_val = 0
req_settling.typical = 2e-3
req_settling.max_val = 5e-3
req_settling.measurement = "settling_time"
req_settling.settling_tolerance = 0.02
req_settling.context_nets = "dut.package_2,i(L1)"
req_settling.justification = "Settle within 5ms, 2% band"
```

### Current measurement (SPICE expression)
```ato
req_inductor_current = new Requirement
req_inductor_current.req_name = "REQ-005: Inductor current"
req_inductor_current.simulation = "tran_ripple"
req_inductor_current.net = "i(L1)"
req_inductor_current.min_val = 3.0
req_inductor_current.typical = 5.0
req_inductor_current.max_val = 6.0
req_inductor_current.measurement = "final_value"
```

### Sweep requirement (references a SimulationSweep by name)
```ato
sweep_duty_req = new Requirement
sweep_duty_req.req_name = "SWEEP-009: Duty cycle vs VIN"
sweep_duty_req.simulation = "sweep_duty_vin"
sweep_duty_req.net = "dut.package_8"
sweep_duty_req.min_val = 5
sweep_duty_req.typical = 42
sweep_duty_req.max_val = 95
sweep_duty_req.measurement = "duty_cycle"
sweep_duty_req.context_nets = "dut.power_out.hv"
sweep_duty_req.justification = "Duty cycle D ~ Vout/Vin: 5V/48V=10.4% to 5V/6V=83%"
```

### Efficiency sweep requirement
```ato
sweep_eff_fine_req = new Requirement
sweep_eff_fine_req.req_name = "SWEEP-028: Efficiency (fine load sweep)"
sweep_eff_fine_req.simulation = "sweep_eff_fine"
sweep_eff_fine_req.net = "dut.power_out.hv"
sweep_eff_fine_req.min_val = 50
sweep_eff_fine_req.typical = 90
sweep_eff_fine_req.max_val = 100
sweep_eff_fine_req.measurement = "efficiency"
sweep_eff_fine_req.context_nets = "i(V1),dut.package_2,i(V_LSENSE)"
sweep_eff_fine_req.justification = "Efficiency characterization at 8 load points from 100mA to 5A"
```

### Protection test (UVLO inhibit)
```ato
req_uvlo_vout = new Requirement
req_uvlo_vout.req_name = "REQ-015: UVLO inhibit (VIN=3V)"
req_uvlo_vout.simulation = "tran_uvlo"
req_uvlo_vout.net = "dut.power_out.hv"
req_uvlo_vout.min_val = 0
req_uvlo_vout.typical = 0
req_uvlo_vout.max_val = 0.5
req_uvlo_vout.measurement = "final_value"
req_uvlo_vout.context_nets = "dut.package_2,dut.package_8"
req_uvlo_vout.justification = "VIN=3V below 4.3V UVLO — converter must NOT start"
```

---

# Plotting

All plots are generated using Plotly and rendered as standalone interactive HTML files. The verification pipeline delegates rendering to chart node classes in `Plots.py`.

## Plot Types

### LineChart
Time-domain line chart for transient measurements. Shows the measured signal over time with pass/fail bands, settling milestones, and context net traces.

**Measurement-specific annotations:**
- `final_value`, `average`, `sweep`: horizontal pass/fail band (green shading for `[min, max]`)
- `settling_time`: vertical settling time marker with 90%/95%/99% milestones
- `peak_to_peak`: horizontal lines at signal min/max showing the p2p span
- `overshoot`: marker at the peak with overshoot % annotation
- `frequency`: vertical dashed lines at rising-edge crossings
- `duty_cycle`: horizontal threshold line at midpoint, shaded above/below regions
- `efficiency`: power waveform overlay with input/output power traces

### BodePlotChart
Frequency-domain Bode plot for AC measurements. Dual-axis: gain (dB) and phase (degrees) vs frequency on a log scale.

**Measurement-specific annotations:**
- `gain_db`, `phase_deg`: marker at `ac_measure_freq` showing measured value
- `bandwidth_3db`: marker at the -3dB point with vertical frequency line
- `bode_plot`: full gain + phase curves with DC gain reference line

### SweepChart
XY chart for parametric sweep results. Plots measurement values (Y) vs swept parameter values (X) with pass/fail bands.

- X-axis: swept parameter (labeled with `param_name` and `param_unit`)
- Y-axis: measured value (labeled with measurement unit)
- Green/red markers for pass/fail at each sweep point
- Green shaded band for `[min_val, max_val]`

### EfficiencySweepChart
3-panel chart specifically for efficiency sweep requirements:

1. **Efficiency vs Load Current**: line + markers, pass/fail colored, with green band
2. **Power Breakdown**: stacked area chart showing `Pout + Ploss = Pin`
3. **Summary Table**: tabular data with Load, Pin, Pout, Ploss, Efficiency%

## Plot Formatting Rules

- All plots use the viridis color scale
- All axes have labels with name and unit
- Each trace has a legend entry
- The legend does not overlap data
- Each plot has an informative title
- Time axes auto-scale to appropriate SI prefix (ns, us, ms, s)
- Engineering notation used for all values (e.g. `7.500 V`, `300.0 ms`, `12.50%`)
- Context net traces shown in subdued colors (orange, green, purple, brown)

## Combined HTML Report

The `generate_requirements_report()` function produces a single HTML page with:
- Header showing pass count vs total (color-coded)
- One row per requirement (sorted alphabetically by name):
  - **Left**: Requirement card showing result, bounds, margin bar, configuration, and justification
  - **Right**: Embedded plot iframe showing the interactive Plotly chart
- Responsive layout that stacks vertically below 1200px width

---

# Full Workflow Example

## File Structure
```
examples/buck_converter/
  ato.yaml                 # Build config with simulation target
  buck_converter.ato       # Circuit design (component + connections)
  simulations.ato          # Simulation definitions (19 transient + 17 sweep)
  requirements.ato         # Requirements (47 REQ + 36 SWEEP = 83 total)
```

## Step 1: Define the Circuit
```ato
# buck_converter.ato
module TI_TPS54560_12V_5V:
    # ... component instantiation, connections, constraints
```

## Step 2: Define Simulations
```ato
# simulations.ato
import SimulationTransient
import SimulationSweep
from "buck_converter.ato" import TI_TPS54560_12V_5V

module BuckConverterSims:
    dut = new TI_TPS54560_12V_5V

    tran_startup = new SimulationTransient
    tran_startup.spice = "V1 dut_package_2 0 PULSE(0 12 0 10u 10u 10 10)"
    tran_startup.time_step = 5e-7
    tran_startup.time_stop = 5e-3

    sweep_duty_vin = new SimulationSweep
    sweep_duty_vin.param_name = "VIN"
    sweep_duty_vin.param_values = "6,8,12,24,48"
    sweep_duty_vin.param_unit = "V"
    sweep_duty_vin.spice_template = "V1 dut_package_2 0 PULSE(0 {VIN} 0 10u 10u 10 10)"
    sweep_duty_vin.time_start = 4e-3
    sweep_duty_vin.time_stop = 4.02e-3
    sweep_duty_vin.time_step = 50e-9
    # ... more simulations
```

## Step 3: Define Requirements
```ato
# requirements.ato
import Requirement
from "simulations.ato" import BuckConverterSims

module SimulationRequirements from BuckConverterSims:
    req_output_voltage = new Requirement
    req_output_voltage.req_name = "REQ-001: Startup output voltage"
    req_output_voltage.simulation = "tran_startup"
    req_output_voltage.net = "dut.power_out.hv"
    req_output_voltage.min_val = 4.80
    req_output_voltage.typical = 5.0
    req_output_voltage.max_val = 5.20
    req_output_voltage.measurement = "final_value"
    req_output_voltage.context_nets = "dut.package_2,i(L1),dut.package_8"
    req_output_voltage.justification = "WEBENCH: Vout=5V within 4%"

    sweep_duty_req = new Requirement
    sweep_duty_req.req_name = "SWEEP-009: Duty cycle vs VIN"
    sweep_duty_req.simulation = "sweep_duty_vin"
    sweep_duty_req.net = "dut.package_8"
    sweep_duty_req.min_val = 5
    sweep_duty_req.typical = 42
    sweep_duty_req.max_val = 95
    sweep_duty_req.measurement = "duty_cycle"
    # ... more requirements
```

## Step 4: Configure Build
```yaml
# ato.yaml
builds:
  simulation:
    entry: requirements.ato:SimulationRequirements
    hide_designators: true
    exclude_checks: [PCB.requires_drc_check]
```

## Step 5: Run
```bash
ato build -b simulation
```

This triggers: pick-parts → run-simulations → verify-requirements → generate reports.

---

# Circuit API Reference

The `Circuit` class in `ngspice.py` is the Python interface to ngspice:

| Method | Description |
|--------|-------------|
| `Circuit.load(path)` | Load a `.spice` file |
| `circuit.op()` | Run DC operating point → `OpResult` |
| `circuit.tran(step, stop, signals, start, uic)` | Run transient → `TransientResult` |
| `circuit.ac(start_freq, stop_freq, points_per_decade, signals)` | Run AC → `ACResult` |
| `circuit.set_source(name, spec)` | Override a source's spec |
| `circuit.get_source_spec(name)` | Read a source's current spec |
| `circuit.add_element(line)` | Add a SPICE element line |
| `circuit.remove_element(name)` | Remove an element by name |
| `circuit.save_state()` | Snapshot netlist lines → `list[str]` |
| `circuit.restore_state(state)` | Restore from snapshot |

### TransientResult
Dict-like access to time-domain signals. Keys are lowercase SPICE signal names (e.g. `v(dut_power_out_hv)`, `i(l1)`). Has `.time` attribute for time vector.

### ACResult
Complex frequency-domain results with methods: `gain_db(net)`, `phase_deg(net)`, `gain_db_relative(net, ref)`, `phase_deg_relative(net, ref)`, `compute_diff(net, ref)`. Has `.freq` attribute for frequency vector.

### OpResult
Dict-like access to DC operating point: `.voltages` and `.currents` dicts.
