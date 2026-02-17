#!/usr/bin/env python3
"""Simulation-based requirements for the resistor divider bias network.

This module feeds the 7.5V reference node to a downstream 10-bit ADC
(0-10V input range) and must settle before the first sample window.

Usage:
    ato build               # generate .spice netlist
    python requirements.py  # verify all requirements
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from faebryk.exporters.simulation.ngspice import Circuit, pulse
from faebryk.exporters.simulation.requirement import (
    Requirement,
    TranConfig,
    plot_results,
    verify,
)

SPICE = Path(__file__).parent / "build" / "builds" / "default" / "default.spice"

if not SPICE.exists():
    print(f"ERROR: {SPICE} not found. Run 'ato build' first.", file=sys.stderr)
    sys.exit(1)

circuit = Circuit.load(SPICE)

requirements = [
    Requirement(
        name="REQ-001: Output DC bias",
        analysis="op",
        net="output",
        min=7.425,
        nominal=7.5,
        max=7.575,
        justification="ADC reference bias within +-1%",
    ),
    Requirement(
        name="REQ-002: Supply current",
        analysis="op",
        net="i(v1)",
        min=-500e-6,
        nominal=-250e-6,
        max=0,
        justification="Power budget for shared 10V rail (SPICE sign: negative = into circuit)",
    ),
    Requirement(
        name="REQ-003: Transient final value",
        analysis="tran",
        net="output",
        min=7.45,
        nominal=7.5,
        max=7.55,
        context_nets=["power_hv"],
        justification="Output converges to DC steady-state",
    ),
]

results, tran_data = verify(
    circuit,
    requirements,
    tran=TranConfig(step=1e-4, stop=1.0, source_override=("V1", pulse(0, 10))),
)

print(f"Circuit: {SPICE}\n")

for r in results:
    tag = "PASS" if r.passed else "FAIL"
    print(f"{r.requirement.name}: {r.actual:.4g}  [{r.requirement.min}, {r.requirement.max}]  {tag}")

print()
passed = sum(1 for r in results if r.passed)
total = len(results)
print(f"{passed}/{total} requirements passed")

plot_path = plot_results(results, tran_data, Path(__file__).parent / "transient_output.png")
if plot_path:
    print(f"Plot saved to {plot_path}")

sys.exit(0 if all(r.passed for r in results) else 1)
