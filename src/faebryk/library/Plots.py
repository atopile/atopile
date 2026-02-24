# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import faebryk.core.node as fabll
import faebryk.library._F as F

if TYPE_CHECKING:
    import plotly.graph_objects as go


# ---------------------------------------------------------------------------
# Plot context — lightweight data passed from the verification pipeline
# to avoid circular imports with requirement.py
# ---------------------------------------------------------------------------


@dataclass
class PlotContext:
    """Requirement context for annotating plots with pass/fail info.

    Built by the verification pipeline from RequirementResult + Requirement.
    Avoids circular dependency between library/Plots.py and exporters/.
    """

    actual: float
    passed: bool
    min_val: float
    max_val: float
    measurement: str
    req_name: str = ""
    display_net: str = ""
    settling_tolerance: float | None = None
    context_keys: list[str] = field(default_factory=list)
    diff_ref_key: str | None = None
    sweep_param_name: str = ""
    sweep_param_unit: str = ""
    measurement_unit: str = ""
    signal_key: str = ""


# ---------------------------------------------------------------------------
# Utility functions (moved from exporters/simulation/requirement.py)
# ---------------------------------------------------------------------------

_SI_PREFIXES = [
    (1e-15, "f"),
    (1e-12, "p"),
    (1e-9, "n"),
    (1e-6, "u"),
    (1e-3, "m"),
    (1.0, ""),
    (1e3, "k"),
    (1e6, "M"),
    (1e9, "G"),
]


def format_eng(value: float, unit: str) -> str:
    """Format a value in engineering notation with SI prefix.

    Examples:
        format_eng(7.5, "V")   -> "7.500 V"
        format_eng(0.3, "s")   -> "300.0 ms"
        format_eng(12.5, "%")  -> "12.50%"
    """
    if unit == "%":
        return f"{value:.2f}%"

    abs_val = abs(value)
    if abs_val == 0:
        return f"0.000 {unit}"

    for threshold, prefix in _SI_PREFIXES:
        if abs_val < threshold * 1000:
            scaled = value / threshold
            return f"{scaled:.4g} {prefix}{unit}"

    # Fallback for very large values
    return f"{value:.4g} {unit}"


def auto_scale_time(t_max: float) -> tuple[float, str]:
    """Choose time unit scale factor and label."""
    if t_max <= 0:
        return 1.0, "s"
    if t_max < 1e-6:
        return 1e9, "ns"
    if t_max < 1e-3:
        return 1e6, "us"
    if t_max < 1.0:
        return 1e3, "ms"
    return 1.0, "s"


def signal_unit(key: str) -> str:
    """Infer unit type from signal key: 'V' for voltage, 'A' for current."""
    if key.startswith("i("):
        return "A"
    return "V"


def _viridis_hex(n: int) -> list[str]:
    """Return *n* evenly-spaced hex colors from the Viridis colorscale."""
    # 16-stop Viridis LUT — enough for smooth interpolation.
    _LUT = [
        (68, 1, 84), (72, 26, 108), (71, 47, 126), (65, 68, 135),
        (57, 86, 140), (49, 104, 142), (42, 120, 142), (35, 137, 142),
        (31, 154, 138), (34, 170, 127), (53, 186, 109), (86, 199, 83),
        (122, 209, 55), (165, 218, 32), (210, 226, 27), (253, 231, 37),
    ]
    if n <= 0:
        return []
    if n == 1:
        return [f"#{_LUT[8][0]:02x}{_LUT[8][1]:02x}{_LUT[8][2]:02x}"]
    result: list[str] = []
    for i in range(n):
        t = i / (n - 1) * (len(_LUT) - 1)
        lo = int(t)
        hi = min(lo + 1, len(_LUT) - 1)
        frac = t - lo
        r = int(_LUT[lo][0] + frac * (_LUT[hi][0] - _LUT[lo][0]))
        g = int(_LUT[lo][1] + frac * (_LUT[hi][1] - _LUT[lo][1]))
        b = int(_LUT[lo][2] + frac * (_LUT[hi][2] - _LUT[lo][2]))
        result.append(f"#{r:02x}{g:02x}{b:02x}")
    return result


_CTX_COLORS = _viridis_hex(4)


def _compute_settling_milestones(
    signal_data: list[float],
    time_data: list[float],
    final: float,
) -> list[tuple[float, float, str]]:
    """Compute 90%, 95%, 99% settling times.

    Returns list of (time, tolerance_pct, label) tuples.
    """
    if final == 0:
        return []

    milestones = []
    for pct, tol in [(90, 0.10), (95, 0.05), (99, 0.01)]:
        band = abs(final * tol)
        settled_time = 0.0
        for i in range(len(signal_data) - 1, -1, -1):
            if abs(signal_data[i] - final) > band:
                settled_time = time_data[i] if i < len(time_data) else float("inf")
                break
        if settled_time != float("inf"):
            milestones.append((settled_time, pct, f"{pct}%"))
    return milestones


def _interpolate_at_freq(
    freq: list[float], values: list[float], target: float
) -> float:
    """Log-frequency interpolation of values at target frequency."""
    if not freq or target <= 0:
        return float("nan")
    if target <= freq[0]:
        return values[0]
    if target >= freq[-1]:
        return values[-1]
    for i in range(len(freq) - 1):
        if freq[i] <= target <= freq[i + 1]:
            log_f0 = math.log10(freq[i])
            log_f1 = math.log10(freq[i + 1])
            log_ft = math.log10(target)
            t = (log_ft - log_f0) / (log_f1 - log_f0) if log_f1 != log_f0 else 0.0
            return values[i] + t * (values[i + 1] - values[i])
    return values[-1]


# ---------------------------------------------------------------------------
# SweepPoint dataclass (used by build_steps.py for sweep rendering)
# ---------------------------------------------------------------------------


@dataclass
class SweepPoint:
    """A single data point from a parametric sweep."""

    param_value: float
    actual: float
    passed: bool


# ---------------------------------------------------------------------------
# LineChart — declarative chart node with x/y/color fields
# ---------------------------------------------------------------------------


class LineChart(fabll.Node):
    """Declarative line chart: x/y/color specify data axes.

    Usage in ato::

        plot_vout = new LineChart
        plot_vout.title = "Output Voltage Startup"
        plot_vout.x = "time"
        plot_vout.y = "dut.power_out.hv"

        req_001 = new Requirement
        req_001.required_plot = "plot_vout"
    """

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _is_plot = fabll.Traits.MakeEdge(F.is_plot.MakeChild())

    title = F.Parameters.StringParameter.MakeChild()
    x = F.Parameters.StringParameter.MakeChild()              # "time", "frequency", "dut.param"
    y = F.Parameters.StringParameter.MakeChild()               # "dut.net", "measurement(net)"
    y_secondary = F.Parameters.StringParameter.MakeChild()     # secondary y-axis signal
    color = F.Parameters.StringParameter.MakeChild()           # "dut" or omitted
    simulation = F.Parameters.StringParameter.MakeChild()      # simulation name override
    plot_limits = F.Parameters.StringParameter.MakeChild()     # "true" (default) or "false"
    y_range = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)  # y-axis range

    def get_title(self) -> str | None:
        try:
            return self.title.get().try_extract_singleton()
        except Exception:
            return None

    def get_x(self) -> str | None:
        try:
            return self.x.get().try_extract_singleton()
        except Exception:
            return None

    def get_y(self) -> str | None:
        try:
            return self.y.get().try_extract_singleton()
        except Exception:
            return None

    def get_y_secondary(self) -> str | None:
        try:
            return self.y_secondary.get().try_extract_singleton()
        except Exception:
            return None

    def get_color(self) -> str | None:
        try:
            return self.color.get().try_extract_singleton()
        except Exception:
            return None

    def get_simulation(self) -> str | None:
        try:
            return self.simulation.get().try_extract_singleton()
        except Exception:
            return None


# ---------------------------------------------------------------------------
# BarChart — declarative bar chart node with x/y fields
# ---------------------------------------------------------------------------


class BarChart(fabll.Node):
    """Declarative bar chart: x=sweep param, y=measurement(net).

    Usage in ato::

        plot_bar = new BarChart
        plot_bar.title = "Peak-to-Peak vs Capacitance"
        plot_bar.x = "COUT"
        plot_bar.y = "peak_to_peak(dut.power_out.hv)"

        req.required_plot = "plot_bar"
    """

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _is_plot = fabll.Traits.MakeEdge(F.is_plot.MakeChild())

    title = F.Parameters.StringParameter.MakeChild()
    x = F.Parameters.StringParameter.MakeChild()   # sweep param name
    y = F.Parameters.StringParameter.MakeChild()    # "measurement(net)"
    simulation = F.Parameters.StringParameter.MakeChild()    # simulation name override
    plot_limits = F.Parameters.StringParameter.MakeChild()   # "true" (default) or "false"

    def get_title(self) -> str | None:
        try:
            return self.title.get().try_extract_singleton()
        except Exception:
            return None

    def get_x(self) -> str | None:
        try:
            return self.x.get().try_extract_singleton()
        except Exception:
            return None

    def get_y(self) -> str | None:
        try:
            return self.y.get().try_extract_singleton()
        except Exception:
            return None

    def get_simulation(self) -> str | None:
        try:
            return self.simulation.get().try_extract_singleton()
        except Exception:
            return None
