#!/usr/bin/env python3
"""Simulation-based requirements for the TPS54560 buck converter average model.

Verifies that the TPS54560 average model regulates a 12V input to ~5V output
using a feedback divider (R_top=52.3k, R_bottom=10k) with Vref=0.8V.

Requirements:
    REQ-001: Output DC voltage ~5V (DCOP)
    REQ-002: Feedback DC voltage ~0.8V (DCOP)
    REQ-003: Power-on — output settles to ~5V after 0→12V input step (Transient)
    REQ-004: Inductor current — steady-state ~5A after power-on (Transient)

Usage:
    ato build               # generate .spice netlist
    python requirements.py  # verify all requirements
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import faebryk.core.faebrykpy as fbrk
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.exporters.simulation.ngspice import Circuit, pulse
from faebryk.exporters.simulation.requirement import (
    _tran_group_key,
    plot_requirement,
    verify_requirements,
)

SPICE = Path(__file__).parent / "build" / "builds" / "default" / "default.spice"

if not SPICE.exists():
    print(f"ERROR: {SPICE} not found. Run 'ato build' first.", file=sys.stderr)
    sys.exit(1)

# --- Set up graph ---
g = graph.GraphView.create()
tg = fbrk.TypeGraph.create(g=g)

req_type = F.Requirement.bind_typegraph(tg)

# --- REQ-001: Output DC voltage (DCOP + FinalValue) ---
req1 = req_type.create_instance(g=g)
req1.setup(
    name="REQ-001: Output DC voltage",
    net="power_out_hv",
    min_val=4.85,
    typical=5.0,
    max_val=5.10,
    capture=F.Captures.DCOPCapture,
    measurement=F.Measurements.FinalValue,
    justification="Buck converter output within 3% of 5V target",
)

# --- REQ-002: Feedback DC voltage (DCOP + FinalValue) ---
req2 = req_type.create_instance(g=g)
req2.setup(
    name="REQ-002: Feedback DC voltage",
    net="fb",
    min_val=0.78,
    typical=0.80,
    max_val=0.82,
    capture=F.Captures.DCOPCapture,
    measurement=F.Measurements.FinalValue,
    justification="FB pin regulates to Vref=0.8V within 2.5%",
)

# --- REQ-003: Power-on — output final value after 0→12V input step ---
# Source V1 steps from 0V to 12V. With UIC the converter starts cold
# and the output should settle to ~5V.
req3 = req_type.create_instance(g=g)
req3.setup(
    name="REQ-003: Power-on output voltage",
    net="power_out_hv",
    min_val=4.80,
    typical=5.0,
    max_val=5.20,
    capture=F.Captures.TransientCapture,
    measurement=F.Measurements.FinalValue,
    context_nets=["buck_vin", "i(L1)"],
    tran_step=10e-6,
    tran_stop=20e-3,
    source_override=("V1", pulse(0, 12)),
    justification="Output converges to regulated voltage after power-on",
)

# --- REQ-004: Inductor current — steady-state after power-on ---
# The inductor current should settle to ~5A (Vout/R_load = 5V/1ohm).
# Current is positive (flows from sw to power_out_hv through L1).
req4 = req_type.create_instance(g=g)
req4.setup(
    name="REQ-004: Inductor current average",
    net="i(L1)",
    min_val=4.0,
    typical=5.0,
    max_val=6.0,
    capture=F.Captures.TransientCapture,
    measurement=F.Measurements.FinalValue,
    context_nets=["power_out_hv"],
    tran_step=10e-6,
    tran_stop=20e-3,
    source_override=("V1", pulse(0, 12)),
    justification="Inductor delivers ~5A load current at steady state",
)

all_reqs = [req1, req2, req3, req4]

# --- Run verification ---
circuit = Circuit.load(SPICE)
results, tran_data = verify_requirements(circuit, all_reqs)

print(f"Circuit: {SPICE}\n")

for r in results:
    tag = "PASS" if r.passed else "FAIL"
    print(
        f"{r.requirement.get_name()}: {r.actual:.4g}  "
        f"[{r.requirement.get_min_val()}, {r.requirement.get_max_val()}]  {tag}"
    )

print()
passed = sum(1 for r in results if r.passed)
total = len(results)
print(f"{passed}/{total} requirements passed")

# --- Generate per-requirement plots (HTML) ---
for r in results:
    if r.requirement.get_capture() != "transient":
        continue
    name_slug = r.requirement.get_name().replace(" ", "_").replace(":", "")
    plot_path = Path(__file__).parent / f"req_{name_slug}.html"
    key = _tran_group_key(r.requirement)
    saved = plot_requirement(r, tran_data.get(key), plot_path)
    if saved:
        print(f"Plot saved to {saved}")

# --- Generate standalone inductor current waveform plot ---
# Use the transient data from REQ-003/REQ-004 group to plot I(L1)
try:
    import plotly.graph_objects as go

    for key, tran_result in tran_data.items():
        if "i(l1)" in tran_result.signals:
            time_ms = [t * 1e3 for t in tran_result.time]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=time_ms, y=tran_result["i(l1)"],
                mode="lines", name="i(L1)",
                line=dict(color="royalblue", width=2),
            ))
            fig.update_layout(
                title="Inductor Current Waveform (Power-on 0→12V)",
                xaxis_title="Time (ms)",
                yaxis_title="Current (A)",
                template="plotly_white",
                width=900, height=500,
            )
            plot_path = Path(__file__).parent / "inductor_current.html"
            fig.write_html(str(plot_path))
            print(f"Inductor current plot saved to {plot_path}")
            break
except ImportError:
    pass

sys.exit(0 if all(r.passed for r in results) else 1)
