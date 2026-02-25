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

### Plot Design Principles

Good plots follow the scientific standard: a reader who sees only the plot and its title should understand what was tested, what the result was, and whether it passed. Every element on the chart must earn its place.

#### 1. Titles

Titles describe the relationship being shown, not the requirement ID:

| Bad | Good | Why |
|-----|------|-----|
| `"REQ_006: Average Inductor Current"` | `"Average Inductor Current vs Load"` | Tells reader what the axes mean |
| `"Output Voltage"` | `"Output During VIN Drop (14V to 8V)"` | Explains the test condition |
| `"Simulation Result 3"` | `"AC-Coupled Output Ripple vs Capacitance"` | Identifies what was measured and what was varied |

**Pattern**: `"<Y-axis quantity> [during/vs] <X-axis quantity or test condition>"`

#### 2. Choose the right chart type

| Chart type | When to use | Example |
|------------|-------------|---------|
| **LineChart, x=time** | Show waveform shape, transient behavior, time-domain detail | Startup ramp, load step response, ripple waveform |
| **LineChart, x=param** | Show trend of a measurement across sweep points (envelope, settling_time) | Settling time vs frequency, envelope vs load |
| **BarChart, x=param** | Show a single scalar per sweep point with pass/fail coloring | Average voltage vs VIN, peak current vs load |

**Rule of thumb**: If a human reviewer needs to see the *waveform shape* to be convinced the requirement is met, use a time-domain LineChart. If they only need to see that a *number is within bounds*, use a BarChart.

#### 3. Required vs supplementary plots

Each requirement should have:
- **`required_plot`**: The primary evidence. This single plot should answer "did it pass and by how much margin?" at a glance. Typically a BarChart with limit bands or a key time-domain trace.
- **`supplementary_plot`**: Supporting context. Shows the raw waveforms behind the measurement, or alternative views. A reviewer looks here only if they want to understand *why* a value is what it is.

**Example**: For load regulation (average Vout vs load current):
- `required_plot`: BarChart showing average Vout at each load current, with ±2% limit bands and pass/fail coloring
- `supplementary_plot`: LineChart overlay of output voltage waveforms colored by load current — shows the raw time-domain data behind the averages

#### 4. AC-coupling

Use `ac_coupled(net)` whenever the interesting signal variation is small relative to its DC level:

| Scenario | Without AC-coupling | With AC-coupling |
|----------|--------------------|--------------------|
| 50mV ripple on 5V output | Flat line at 5V — ripple invisible | Clear triangle/sawtooth showing ripple |
| Load transient: 200mV dip on 5V | Small dip barely visible | Clear perturbation shape, recovery time visible |
| Startup: 0V → 5V ramp | Perfect — full ramp visible | Bad — shows only the residual above the mean |

**Rule**: AC-couple for ripple, perturbation, and transient analysis. Do NOT AC-couple for startup, regulation (absolute level matters), or envelope measurements.

#### 5. Secondary y-axis

The secondary y-axis adds physical context. It shows the *cause* alongside the *effect*:

| Primary y (effect) | Secondary y (cause) | What it reveals |
|--------------------|--------------------|-----------------|
| `dut.power_out.hv` (output voltage) | `i(l1)` (inductor current) | How inductor current drives voltage |
| `dut.power_out.hv` (output voltage) | `i(vsense)` (load current) | Load step timing vs voltage response |
| `ac_coupled(dut.power_out.hv)` | `i(l1)` | Ripple correlation with switching current |
| `dut.package.SW` (switch node) | `i(l1)` | PWM timing vs current waveform |

**Guidelines**:
- Secondary axis traces render with dashed lines for visual distinction
- Keep to one secondary signal — two secondary axes create visual clutter
- The secondary y-axis auto-labels as "Current (A)" or "Voltage (V)" based on the signal type
- Don't add a secondary axis if the primary already tells the full story

#### 6. Sweep color coding

For sweep simulations rendered as time-domain overlays, the `color` field on LineChart colors each trace by sweep parameter value. A Viridis-derived palette is used automatically:

```ato
plot.color = "ILOAD"    # each load current gets a distinct color
plot.color = "COUT"     # each capacitance value gets a distinct color
plot.color = ""         # no coloring (default sequential colors)
```

Use `color` when the sweep has 3+ points and the reader needs to distinguish which trace belongs to which parameter value.

#### 7. Limit band visualization

When `plot_limits = "true"` (the default), the chart renders:
- A green shaded rectangle between LSL and USL (light green, 8% opacity)
- Dotted gray horizontal lines at LSL and USL with annotation labels
- Bar charts also color individual bars green (pass) or red (fail)

**Suppress limits** with `plot_limits = "false"` on supplementary or informational plots where the limit bands would be misleading or visually cluttered (e.g., inductor current waveform plots that support a voltage ripple requirement).

#### 8. Y-axis range

The auto-range logic:
- Extends 10% below the data/limit envelope minimum, 20% above (extra headroom for bar chart text labels)
- For non-negative measurements (`peak_to_peak`, `max`, `settling_time`, etc.), the lower bound clamps at 0
- Override with `assert plot.y_range within 5V +/- 10%` for explicit control

Use explicit y-range when:
- Auto-range produces a misleading scale (e.g., zoomed in so far that small noise looks like large variation)
- You want consistent y-axes across multiple related plots

#### Requirement type → plot recipe table

| Requirement type | Primary y | Secondary y | Chart | Notes |
|---|---|---|---|---|
| Load transient (envelope) | `dut.power_out.hv` | `i(vsense)` | LineChart, x=time | Show voltage with current context; limit bands on voltage |
| Line transient (envelope) | `dut.power_out.hv` | `i(l1)` | LineChart, x=time | Shows control loop response to VIN step |
| Startup settling time | `settling_time(dut.power_out.hv)` | — | LineChart, x=param | Scatter/line across sweep points |
| Startup overshoot | `max(dut.power_out.hv)` | — | BarChart, x=param | One bar per sweep point with pass/fail color |
| Output ripple (amplitude) | `ac_coupled(dut.power_out.hv)` | `i(l1)` | LineChart, x=time | AC-couple to see mV-scale ripple; color by sweep |
| Output ripple (envelope) | `envelope(ac_coupled(dut.power_out.hv))` | — | LineChart, x=param | Min/max envelope across sweep points |
| Load/line regulation | `average(dut.power_out.hv)` | — | BarChart, x=param | One bar per operating point, with ±tolerance band |
| Switching node | `dut.package.SW` | `i(l1)` | LineChart, x=time | Raw SW node; shows PWM timing and current shape |
| Inductor current (informational) | `i(l1)` | — | LineChart, x=time, color=param | Overlay waveforms; suppress limits on supplementary |
| Inductor current (measurement) | `peak_to_peak(i(l1))` or `max(i(l1))` | — | BarChart, x=param | Scalar per sweep point; suppress limits if informational |

### How to Review Generated Plots (LLM Procedure)

After each build, verify plot quality programmatically by reading the generated HTML files. Do NOT trust that plots are correct just because the build succeeded — rendering bugs, wrong axis labels, and misleading scales are common.

#### Step 1: Count and list plot files

```bash
ls build/builds/<name>/plot_*.html | wc -l
ls build/builds/<name>/plot_*.html
```

Compare the count to the number of plot definitions in the `.ato` file. Extra files indicate stale artifacts from a previous build (the build directory is not cleaned automatically). Fewer files indicate plots that failed to render (check build warnings).

**Always clean stale artifacts before a final build**:
```bash
rm -f build/builds/<name>/plot_*.html
ato build -b <name>
```

#### Step 2: Extract axis labels and ranges from HTML

Each plot is a self-contained Plotly HTML file. Extract key metadata with regex:

```python
import re
with open("build/builds/<name>/plot_<title>.html") as f:
    html = f.read()

# Find all range values (y-axis bounds)
for m in re.finditer(r'"range":\[([^\]]+)\]', html):
    print(f"range: [{m.group(1)}]")

# Find axis titles
for m in re.finditer(r'"title":\{"text":"([^"]+)"', html):
    print(f"title: {m.group(1)}")
```

#### Step 3: Check for these specific defects

| Defect | How to detect | Fix |
|--------|---------------|-----|
| **Wrong y-axis unit** ("Voltage (A)" for current) | Extract yaxis title text | Fixed in build_steps.py — auto-detects from signal type |
| **Stray text in title** (trailing numbers, "REQ_xxx:" prefix) | Read title from HTML | Fix the `plot.title` field in `.ato` |
| **Negative y-range for non-negative quantity** | Check range lower bound < 0 when measurement is peak_to_peak/max/settling_time | Fixed in build_steps.py — clamps at 0 for non-negative measurements |
| **Missing legend** | Check for `"showlegend":true` in layout | Legends render automatically for multi-trace charts |
| **Limit bands on informational chart** | Check for `"fillcolor":"green"` shapes | Set `plot_limits = "false"` on the plot |
| **X-axis raw param name** ("ILOAD" instead of "Iload (A)") | Extract xaxis title | BarChart auto-formats: `.replace("_"," ").title()` + unit. For scatter charts, same logic applies. |
| **Unreasonably large point count** | Check trace data length (>50k points per trace) | Reduce simulation time window or increase time_step |

#### Step 4: Verify data makes physical sense

After extracting the plotted data, sanity-check against circuit physics:

| Signal | Expected behavior | Red flag |
|--------|------------------|----------|
| Output voltage (startup) | Monotonic ramp from 0V to target | Oscillation, overshoot >10%, negative voltage |
| Output voltage (regulation) | ~5V ± a few mV across sweep | Voltage increasing/decreasing with load by >2% |
| Inductor current (CCM) | Triangle wave, average ≈ load current | Negative current (DCM expected at light load only) |
| Inductor current (Eco-mode) | Burst pulses separated by zero intervals | Continuous conduction at 0.1A load |
| Settling time vs parameter | Monotonic or smooth trend | Random scatter (measurement noise, wrong time window) |
| Peak-to-peak ripple vs cap | Decreasing with increasing capacitance | Non-monotonic or increasing |
| Duty cycle (on SW node) | ≈ Vout/Vin for CCM | Significantly above or below theoretical |

#### Step 5: Check requirements.json for consistency

```python
import json
with open("build/builds/<name>/<name>.requirements.json") as f:
    data = json.load(f)
for r in data["requirements"]:
    name = r["name"]
    passed = r["passed"]
    actual = r["actual"]
    min_val = r["minVal"]
    max_val = r["maxVal"]
    # Check margin: how close is actual to the limit?
    if passed and max_val is not None and actual is not None:
        margin = min(actual - min_val, max_val - actual) / (max_val - min_val)
        if margin < 0.05:
            print(f"WARNING: {name} passes with <5% margin: actual={actual}")
```

Tight margins (actual within 5% of a limit) warrant investigation — either the limit is too tight or the circuit is operating at the edge of its design space. Both are important to flag.

### Requirement Limit Quality

Limits must be *meaningful*. A requirement with limits so broad it can never fail proves nothing. A requirement with limits so tight it fails on noise is equally useless.

#### Principles for setting good limits

1. **Derive from physics or datasheet, not from measured values.** The limit should represent what the *application requires*, not what the simulator happens to produce. Example: output regulation ±2% comes from the downstream load's tolerance requirement, not from "the sim gives 5.003V so let's set ±2%."

2. **Every limit should be falsifiable.** Ask: "Is there a realistic design change that could cause this to fail?" If the answer is "no, this can literally never fail," the limit is too broad:

| Weak limit (always passes) | Strong limit (actually proves something) |
|---|---|
| `0 to 1` for duty cycle | `0.35 to 0.55` for 12V→5V buck |
| `-1A to 7A` for min inductor current | `-0.5A to 5A` (diode clamp, rated current) |
| `0V to 100V` for output voltage | `5V +/- 2%` (regulation spec) |

3. **Match the measurement semantics.** `peak_to_peak` returns amplitude (always ≥ 0), not absolute voltage. `envelope` checks min/max against limits. `settling_time` returns seconds. Don't set voltage-like limits on a time measurement.

4. **Account for operating modes.** A buck converter at 0.1A load operates in Eco-mode/DCM with very different waveform characteristics than at 5A CCM. If a sweep covers both modes, the limits must accommodate both. If you want to test only CCM, restrict the sweep to loads where CCM is guaranteed.

5. **Flag measurements that don't measure what you think.** The `duty_cycle` measurement computes the fraction of time a signal is above its midpoint. For a symmetric triangular inductor current waveform, this is always ≈ 0.5 regardless of the actual PWM duty cycle. Apply `duty_cycle` only to square-wave signals (switch node voltage).

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
