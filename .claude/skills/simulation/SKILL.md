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
| `src/faebryk/exporters/simulation/requirement.py` | Verification engine — scoped netlist generation, simulation dispatch, plotting |
| `src/faebryk/exporters/simulation/ngspice.py` | SPICE netlist generator and ngspice runner (`Circuit`, `generate_spice_netlist`) |
| `src/atopile/build_steps.py` | Build step registration (`verify-requirements`, `spice-netlist`) |

## How It Works

1. `ato build` finds all `Requirement` nodes in the app tree
2. Groups them by the nearest ancestor that has electrical components (auto-scoping)
3. Generates a scoped SPICE netlist per group (only components in that subtree)
4. Runs DCOP, transient, and/or AC analysis via ngspice
5. Computes measurements, checks against bounds, generates plots
6. Writes `<build>.requirements.json` artifact with pass/fail results

## Step-by-Step: Adding Requirements to a Design

### 1. Create a requirements file

Create a `requirements.ato` file alongside your main `.ato` file:

```ato
import Requirement

module Requirements:
    "Requirements for my circuit."

    req_output_voltage = new Requirement
    req_output_voltage.req_name = "REQ-001: Output voltage"
    req_output_voltage.net = "output"
    req_output_voltage.min_val = "3.2"
    req_output_voltage.typical = "3.3"
    req_output_voltage.max_val = "3.4"
    req_output_voltage.capture = "dcop"
    req_output_voltage.measurement = "final_value"
    req_output_voltage.justification = "LDO must regulate to 3.3V"
```

### 2. Import and instantiate in the main module

```ato
from "requirements.ato" import Requirements

module App:
    # ... circuit definition ...
    reqs = new Requirements
```

### 3. Build

Run `ato build`. The `verify-requirements` step runs automatically as part of the default target.

### 4. Read results

Results are in `build/builds/<name>/<name>.requirements.json`:

```json
{
  "id": "REQ-001_Output_voltage",
  "name": "REQ-001: Output voltage",
  "net": "output",
  "capture": "dcop",
  "measurement": "final_value",
  "minVal": 3.2,
  "typical": 3.3,
  "maxVal": 3.4,
  "actual": 3.298,
  "passed": true,
  "unit": "V",
  "justification": "LDO must regulate to 3.3V"
}
```

Transient and AC requirements also generate interactive HTML plots (Bode plots for AC) in the build output directory.

## Requirement Fields Reference

All fields are strings (the `Requirement` node uses `StringParameter` internally).

### Required fields

| Field | Description | Example |
|-------|-------------|---------|
| `req_name` | Human-readable identifier | `"REQ-001: Output voltage"` |
| `net` | Net name to measure (matches SPICE netlist node names) | `"output"`, `"i(v1)"` |
| `min_val` | Lower bound (inclusive) | `"3.2"` |
| `max_val` | Upper bound (inclusive) | `"3.4"` |
| `capture` | Simulation type: `"dcop"`, `"transient"`, or `"ac"` | `"dcop"` |
| `measurement` | What to compute from simulation data | `"final_value"` |

### Optional fields

| Field | Description | Example |
|-------|-------------|---------|
| `typical` | Expected nominal value (informational) | `"3.3"` |
| `justification` | Why this requirement exists | `"LDO regulation spec"` |
| `context_nets` | Comma-separated nets to include in plots | `"power_hv,input"` |

### Transient-only fields (required when `capture = "transient"`)

| Field | Description | Example |
|-------|-------------|---------|
| `tran_step` | Simulation timestep in seconds | `"1e-4"` |
| `tran_stop` | Simulation stop time in seconds | `"1.0"` |
| `tran_start` | Measurement window start time in seconds (optional, default 0). Simulation still runs from t=0, but measurements only use data from `tran_start` onward. Use this to skip startup transients. | `"0.5"` |
| `source_name` | Voltage source to override for transient stimulus | `"V1"` |
| `source_spec` | SPICE source specification | `"PULSE(0 10 0 1n 1n 10 10)"` |

### Settling time field

| Field | Description | Example |
|-------|-------------|---------|
| `settling_tolerance` | Fraction of final value for settling band (default 0.01 = 1%) | `"0.02"` |

### AC-only fields (required when `capture = "ac"`)

| Field | Description | Example |
|-------|-------------|---------|
| `ac_start_freq` | Start frequency in Hz | `"0.01"` |
| `ac_stop_freq` | Stop frequency in Hz | `"1000"` |
| `ac_points_per_dec` | Frequency points per decade (default 100) | `"100"` |
| `ac_source_name` | Voltage source to apply `AC 1` stimulus to | `"V1"` |
| `ac_measure_freq` | Frequency at which to evaluate gain_db/phase_deg (required for those measurements) | `"10"` |
| `ac_ref_net` | Optional input net for Vout/Vin transfer function. If omitted, absolute gain is used. | `"input"` |

## Measurement Types

### Time-domain measurements (DCOP / transient)

| Value | Description | Bounds are |
|-------|-------------|-----------|
| `"final_value"` | Last data point (transient) or operating point (DCOP) | Voltage/current |
| `"average"` | Mean of signal over simulation window | Voltage/current |
| `"settling_time"` | Time for signal to settle within tolerance of final value | Time in seconds |
| `"peak_to_peak"` | Max minus min of signal | Voltage/current |
| `"overshoot"` | Peak above final value as percentage | Percentage |
| `"rms"` | Root mean square of signal | Voltage/current |
| `"frequency"` | Signal frequency via rising-edge counting | Frequency in Hz |

### Frequency-domain measurements (AC)

| Value | Description | Bounds are |
|-------|-------------|-----------|
| `"gain_db"` | Gain in dB at `ac_measure_freq` | dB |
| `"phase_deg"` | Phase in degrees at `ac_measure_freq` | Degrees |
| `"bandwidth_3db"` | Frequency where gain drops 3dB below DC gain | Hz |
| `"bode_plot"` | Full Bode plot (gain + phase); actual = DC gain, bounds check DC gain | dB |

## Net Names

Use **atopile addresses** as net names in requirements. The `Requirement` getters (`get_net()`, `get_context_nets()`) automatically sanitize them to match the SPICE netlist — the same transform applied by `ngspice._sanitize_net_name()` during netlist generation:

| Sanitization rule | Example input | SPICE net name |
|-------------------|---------------|----------------|
| Dots → underscores | `"power.hv"` | `power_hv` |
| Brackets → underscores | `"unnamed[0]"` | `unnamed_0` |
| Spaces → underscores | `"my net"` | `my_net` |
| Consecutive replaced chars collapse | `"a.[0]"` | `a_0` |
| Leading/trailing underscores stripped | `".output."` | `output` |
| Lowercased | `"Power.HV"` | `power_hv` |
| SPICE expressions unchanged | `"i(v1)"` | `i(v1)` |

**How net names are derived from the ato hierarchy:**

- An `Electrical` interface named `output` → net `output`
- `ElectricPower` children: `.hv` → `power_hv`, `.lv` → `power_lv`
- `Resistor` unnamed pins: `r_top.unnamed[0]` → `r_top_unnamed_0`
- Connected nets pick the **shortest** sanitized name among all bus members
- Current through a voltage source: `i(v1)` (SPICE convention — negative = current into circuit)

**In practice**, write the atopile address you'd use to refer to the interface (e.g. `power.hv`, `output`) and the sanitization handles the rest. To verify net names, inspect the generated `.spice` file in `build/builds/<name>/`.

## SPICE Source Specifications

For transient requirements, `source_spec` overrides a voltage source to apply stimulus:

| Pattern | Description |
|---------|-------------|
| `DC 10` | Constant 10V |
| `PULSE(0 10 0 1n 1n 10 10)` | Step from 0V to 10V (V1 V2 delay rise fall width period) |
| `PULSE(0 5 0 0.1 0.1 1 2)` | Slow ramp 0-5V with 100ms rise/fall |

## Auto-Scoping

Requirements are automatically scoped to the nearest ancestor module that contains electrical components. This means:

- Requirements inside a `Requirements` grouping module are scoped up to the parent that has actual R/C/L/power
- Requirements placed directly in a circuit module scope to that module
- For submodule-level requirements, only that submodule's components are simulated (smaller, faster netlists)

## LLM Design Iteration Workflow

When designing a circuit, use simulation requirements to close the feedback loop:

### 1. Define requirements FIRST

Before building the circuit, define what "correct" means. For a voltage divider:
- What output voltage do you expect? (DCOP final_value)
- What current budget? (DCOP final_value on `i(v_source)`)
- How fast must it settle? (transient settling_time)

### 2. Build and read the JSON

After `ato build`, read `<build>.requirements.json`. Each entry has:
- `"passed": true/false` — did the actual value fall within [minVal, maxVal]?
- `"actual"` — the simulated value

### 3. Diagnose failures

If a requirement fails:

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `actual` far from `typical` | Wrong component values | Recalculate R/C/L values |
| `actual` close but outside bounds | Tolerances too tight or component values slightly off | Widen bounds or adjust values |
| `actual = NaN` | Net name doesn't exist in netlist | Check `.spice` file for correct net names |
| Simulation timeout | Circuit too large or convergence issue | Check for floating nodes, add small load resistors |
| `actual` current has wrong sign | SPICE convention: current direction | Negate bounds (SPICE current is negative into circuit) |

### 4. Iterate

Modify component values in the `.ato` file, re-run `ato build`, re-read the JSON. Repeat until all requirements pass.

### Example: fixing a failing voltage divider

```
FAIL: REQ-001: Output voltage = 5.0 [3.2, 3.4]
```

The output is 5V instead of 3.3V. For a divider with Vin=10V:
- Vout = Vin * R_bottom / (R_top + R_bottom)
- Need: 3.3 = 10 * R_bottom / (R_top + R_bottom)
- Ratio: R_bottom/R_top = 3.3/6.7 ~ 0.49

Fix: adjust resistor values to achieve the correct ratio.

## AC Analysis Example

```ato
import Requirement

module ACRequirements:
    "Frequency response requirements for an RC lowpass filter."

    req_gain = new Requirement
    req_gain.req_name = "REQ-005: Low-frequency gain"
    req_gain.net = "output"
    req_gain.min_val = "-3"
    req_gain.typical = "-2.5"
    req_gain.max_val = "-2"
    req_gain.capture = "ac"
    req_gain.measurement = "gain_db"
    req_gain.ac_start_freq = "0.01"
    req_gain.ac_stop_freq = "1000"
    req_gain.ac_points_per_dec = "100"
    req_gain.ac_source_name = "V1"
    req_gain.ac_measure_freq = "0.01"

    req_bw = new Requirement
    req_bw.req_name = "REQ-006: 3dB bandwidth"
    req_bw.net = "output"
    req_bw.min_val = "1.5"
    req_bw.typical = "2.12"
    req_bw.max_val = "3.0"
    req_bw.capture = "ac"
    req_bw.measurement = "bandwidth_3db"
    req_bw.ac_start_freq = "0.01"
    req_bw.ac_stop_freq = "1000"
    req_bw.ac_points_per_dec = "100"
    req_bw.ac_source_name = "V1"
```

AC requirements generate Bode plots (gain + phase) as interactive HTML files.

## Complete Example

See `examples/ngspice/` for a working resistor divider with 7 requirements:
- `resistor_divider.ato` — circuit + requirements import
- `requirements.ato` — 7 requirements (2 DCOP, 2 transient, 3 AC)
- `ato.yaml` — build config
