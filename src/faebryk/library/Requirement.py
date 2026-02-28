# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

import re
from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.library.Captures import ACCapture, DCOPCapture, TransientCapture
from faebryk.library.Measurements import (
    AverageValue,
    Bandwidth3dB,
    BodePlot,
    FinalValue,
    Frequency,
    GainDB,
    Overshoot,
    PeakToPeak,
    PhaseDeg,
    RMS,
    SettlingTime,
    Sweep,
)

_CAPTURE_KEYS: dict[type, str] = {
    DCOPCapture: "dcop",
    TransientCapture: "transient",
    ACCapture: "ac",
}

_MEASUREMENT_KEYS: dict[type, str] = {
    FinalValue: "final_value",
    AverageValue: "average",
    SettlingTime: "settling_time",
    PeakToPeak: "peak_to_peak",
    Overshoot: "overshoot",
    RMS: "rms",
    GainDB: "gain_db",
    PhaseDeg: "phase_deg",
    Bandwidth3dB: "bandwidth_3db",
    BodePlot: "bode_plot",
    Frequency: "frequency",
    Sweep: "sweep",
}

CaptureType = type[DCOPCapture] | type[TransientCapture] | type[ACCapture]
MeasurementType = (
    type[FinalValue]
    | type[AverageValue]
    | type[SettlingTime]
    | type[PeakToPeak]
    | type[Overshoot]
    | type[RMS]
    | type[GainDB]
    | type[PhaseDeg]
    | type[Bandwidth3dB]
    | type[BodePlot]
    | type[Frequency]
    | type[Sweep]
)


# SI prefix multipliers for parsing limit expressions
_SI_PREFIXES = {
    "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6,
    "m": 1e-3, "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12,
}

# Regex for a number with optional SI prefix and unit
_NUM_RE = r"([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([fpnuµmkKMGT]?)\s*[A-Za-z%]*"


def _parse_si_number(s: str) -> float:
    """Parse a number string with optional SI prefix, e.g. '200mV' → 0.2"""
    m = re.match(_NUM_RE, s.strip())
    if not m:
        raise ValueError(f"Cannot parse number: {s!r}")
    val = float(m.group(1))
    prefix = m.group(2)
    if prefix:
        val *= _SI_PREFIXES.get(prefix, 1.0)
    return val


def _parse_limit_expr(expr: str) -> tuple[float, float] | None:
    """Parse ato limit expressions like '5V +/- 10%', '0A to 5A', '3A +/- 4A'.

    Returns (min_val, max_val) or None if unparseable.
    """
    expr = expr.strip()

    # Pattern 1: "X to Y" → (X, Y)
    m = re.match(
        r"([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\s*[fpnuµmkKMGT]?\s*[A-Za-z]*)"
        r"\s+to\s+"
        r"([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\s*[fpnuµmkKMGT]?\s*[A-Za-z]*)",
        expr,
    )
    if m:
        try:
            return (_parse_si_number(m.group(1)), _parse_si_number(m.group(2)))
        except ValueError:
            pass

    # Pattern 2: "X +/- Y%" → (X*(1-Y/100), X*(1+Y/100))
    m = re.match(
        r"([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\s*[fpnuµmkKMGT]?\s*[A-Za-z]*)"
        r"\s*\+/-\s*"
        r"(\d+(?:\.\d+)?)\s*%",
        expr,
    )
    if m:
        try:
            center = _parse_si_number(m.group(1))
            pct = float(m.group(2))
            return (center * (1 - pct / 100), center * (1 + pct / 100))
        except ValueError:
            pass

    # Pattern 3: "X +/- Y<unit>" → (X-Y, X+Y)
    m = re.match(
        r"([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\s*[fpnuµmkKMGT]?\s*[A-Za-z]*)"
        r"\s*\+/-\s*"
        r"([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\s*[fpnuµmkKMGT]?\s*[A-Za-z]*)",
        expr,
    )
    if m:
        try:
            center = _parse_si_number(m.group(1))
            delta = _parse_si_number(m.group(2))
            return (center - delta, center + delta)
        except ValueError:
            pass

    return None


class Requirement(fabll.Node):
    """A simulation requirement node.

    Carries bounds (min/typical/max), references a net to check,
    and labels context nets for plotting.

    Can be defined from Python via setup() or from .ato via field assignment:

        # Python (type-safe)
        req.setup(
            name="REQ-001: Output DC bias",
            net="output",
            min_val=7.425, typical=7.5, max_val=7.575,
            capture=F.Captures.DCOPCapture,
            measurement=F.Measurements.FinalValue,
        )

        # .ato (string-based)
        req = new Requirement
        req.req_name = "REQ-001: Output DC bias"
        req.net = "output"
        req.min_val = "7.425"
        req.capture = "dcop"
        req.measurement = "final_value"
    """

    has_part_removed = fabll.Traits.MakeEdge(F.has_part_removed.MakeChild())

    # Core fields
    req_name = F.Parameters.StringParameter.MakeChild()
    simulation = F.Parameters.StringParameter.MakeChild()
    net = F.Parameters.StringParameter.MakeChild()
    context_nets = F.Parameters.StringParameter.MakeChild()
    limit = F.Parameters.NumericParameter.MakeChild()
    min_val = F.Parameters.StringParameter.MakeChild()
    max_val = F.Parameters.StringParameter.MakeChild()
    justification = F.Parameters.StringParameter.MakeChild()

    # Capture type: "dcop" or "transient"
    capture = F.Parameters.StringParameter.MakeChild()
    # Measurement type: "final_value", "average", "settling_time",
    #                    "peak_to_peak", "overshoot", "rms"
    measurement = F.Parameters.StringParameter.MakeChild()

    # Transient config (only used when capture=TransientCapture)
    tran_step = F.Parameters.StringParameter.MakeChild()
    tran_stop = F.Parameters.StringParameter.MakeChild()
    tran_start = F.Parameters.StringParameter.MakeChild()
    source_name = F.Parameters.StringParameter.MakeChild()
    source_spec = F.Parameters.StringParameter.MakeChild()

    # Settling time config
    settling_tolerance = F.Parameters.StringParameter.MakeChild()

    # AC analysis config (only used when capture=ACCapture)
    ac_start_freq = F.Parameters.StringParameter.MakeChild()
    ac_stop_freq = F.Parameters.StringParameter.MakeChild()
    ac_points_per_dec = F.Parameters.StringParameter.MakeChild()
    ac_source_name = F.Parameters.StringParameter.MakeChild()
    ac_measure_freq = F.Parameters.StringParameter.MakeChild()
    ac_ref_net = F.Parameters.StringParameter.MakeChild()
    diff_ref_net = F.Parameters.StringParameter.MakeChild()

    # Circuit modifications (inject/remove SPICE elements for load step etc.)
    extra_spice = F.Parameters.StringParameter.MakeChild()
    remove_elements = F.Parameters.StringParameter.MakeChild()

    # Multi-DUT: auto-compute min/max from VOUT as vout*(1 +/- pct/100)
    vout_tolerance_pct = F.Parameters.StringParameter.MakeChild()

    # Proportional sweep limits: each sweep point's pass/fail bounds are
    # (paramValue * scale_min) to (paramValue * scale_max).
    # Plot shows diagonal limit lines instead of horizontal ones.
    limit_scale_min = F.Parameters.StringParameter.MakeChild()
    limit_scale_max = F.Parameters.StringParameter.MakeChild()

    # Plot references (comma-separated ato variable names of LineChart siblings)
    required_plot = F.Parameters.StringParameter.MakeChild()
    supplementary_plot = F.Parameters.StringParameter.MakeChild()

    def setup(
        self,
        name: str,
        net: str,
        min_val: float,
        typical: float,
        max_val: float,
        capture: CaptureType = DCOPCapture,
        measurement: MeasurementType = FinalValue,
        justification: str = "",
        context_nets: list[str] | None = None,
        tran_step: float | None = None,
        tran_stop: float | None = None,
        tran_start: float | None = None,
        source_override: tuple[str, str] | None = None,
        settling_tolerance: float | None = None,
        ac_start_freq: float | None = None,
        ac_stop_freq: float | None = None,
        ac_points_per_dec: int | None = None,
        ac_source_name: str | None = None,
        ac_measure_freq: float | None = None,
        ac_ref_net: str | None = None,
        diff_ref_net: str | None = None,
        extra_spice: str | None = None,
        remove_elements: str | None = None,
    ) -> Self:
        self.req_name.get().set_singleton(value=name)
        self.net.get().set_singleton(value=net)

        # Set limit bounds via NumericParameter range
        from faebryk.library.Literals import Numbers

        self.limit.get().constrain_superset(Numbers(min_val, max_val))

        capture_str = capture if isinstance(capture, str) else _CAPTURE_KEYS[capture]
        measurement_str = (
            measurement if isinstance(measurement, str) else _MEASUREMENT_KEYS[measurement]
        )
        self.capture.get().set_singleton(value=capture_str)
        self.measurement.get().set_singleton(value=measurement_str)

        if justification:
            self.justification.get().set_singleton(value=justification)
        if context_nets:
            self.context_nets.get().set_singleton(value=",".join(context_nets))
        if tran_step is not None:
            self.tran_step.get().set_singleton(value=str(tran_step))
        if tran_stop is not None:
            self.tran_stop.get().set_singleton(value=str(tran_stop))
        if tran_start is not None:
            self.tran_start.get().set_singleton(value=str(tran_start))
        if source_override is not None:
            self.source_name.get().set_singleton(value=source_override[0])
            self.source_spec.get().set_singleton(value=source_override[1])
        if settling_tolerance is not None:
            self.settling_tolerance.get().set_singleton(value=str(settling_tolerance))
        if ac_start_freq is not None:
            self.ac_start_freq.get().set_singleton(value=str(ac_start_freq))
        if ac_stop_freq is not None:
            self.ac_stop_freq.get().set_singleton(value=str(ac_stop_freq))
        if ac_points_per_dec is not None:
            self.ac_points_per_dec.get().set_singleton(value=str(ac_points_per_dec))
        if ac_source_name is not None:
            self.ac_source_name.get().set_singleton(value=ac_source_name)
        if ac_measure_freq is not None:
            self.ac_measure_freq.get().set_singleton(value=str(ac_measure_freq))
        if ac_ref_net is not None:
            self.ac_ref_net.get().set_singleton(value=ac_ref_net)
        if diff_ref_net is not None:
            self.diff_ref_net.get().set_singleton(value=diff_ref_net)
        if extra_spice is not None:
            self.extra_spice.get().set_singleton(value=extra_spice)
        if remove_elements is not None:
            self.remove_elements.get().set_singleton(value=remove_elements)

        return self

    # -- Getters --

    def get_name(self) -> str:
        return self.req_name.get().extract_singleton()

    def get_simulation(self) -> str | None:
        return self.simulation.get().try_extract_singleton()

    @staticmethod
    def _sanitize_net_name(name: str) -> str:
        """Sanitize a net name for SPICE compatibility.

        Applies the same transform as ``ngspice._sanitize_net_name``:
        dots, brackets, and whitespace become underscores.  SPICE
        expressions such as ``i(v1)`` are returned unchanged (lowercased).

        Examples::

            "power.hv"   → "power_hv"
            "output"     → "output"
            "a[0]"       → "a_0"
            "i(v1)"      → "i(v1)"
        """
        if "(" in name:
            return name.lower()
        result = re.sub(r"[\.\[\]\s]+", "_", name)
        result = result.strip("_")
        return (result or "unnamed").lower()

    def get_net(self) -> str:
        raw = self.net.get().extract_singleton()
        return self._sanitize_net_name(raw)

    def _get_limit_bounds(self) -> tuple[float, float] | None:
        """Extract [min, max] from the limit NumericParameter.

        ``assert req.limit within X to Y`` uses constrain_superset(),
        so we try try_extract_superset first, then subset as fallback.
        """
        import math

        # 1) Try superset (set by "assert req.limit within X to Y")
        try:
            numbers = self.limit.get().try_extract_superset()
            if numbers is not None:
                mn = numbers.get_min_value()
                mx = numbers.get_max_value()
                if not math.isinf(mn) and not math.isinf(mx):
                    return (mn, mx)
        except Exception:
            pass

        # 2) Try subset (in case constraint was set differently)
        try:
            numbers = self.limit.get().try_extract_subset()
            if numbers is not None:
                mn = numbers.get_min_value()
                mx = numbers.get_max_value()
                if not math.isinf(mn) and not math.isinf(mx):
                    return (mn, mx)
        except Exception:
            pass

        # 3) Fallback: explicit min_val / max_val string params
        try:
            mn_s = self.min_val.get().try_extract_singleton()
            mx_s = self.max_val.get().try_extract_singleton()
            if mn_s is not None and mx_s is not None:
                return (float(mn_s), float(mx_s))
        except Exception:
            pass

        return None

    def get_min_val(self) -> float:
        bounds = self._get_limit_bounds()
        if bounds is not None:
            return bounds[0]
        raise ValueError("limit bounds not set")

    def get_typical(self) -> float:
        bounds = self._get_limit_bounds()
        if bounds is not None:
            return (bounds[0] + bounds[1]) / 2.0
        raise ValueError("limit bounds not set")

    def get_max_val(self) -> float:
        bounds = self._get_limit_bounds()
        if bounds is not None:
            return bounds[1]
        raise ValueError("limit bounds not set")

    def get_justification(self) -> str | None:
        return self.justification.get().try_extract_singleton()

    def get_context_nets(self) -> list[str]:
        raw = self.context_nets.get().try_extract_singleton()
        if raw is None:
            return []
        return [
            self._sanitize_net_name(n.strip())
            for n in raw.split(",")
            if n.strip()
        ]

    def get_capture(self) -> str:
        return self.capture.get().extract_singleton()

    def get_measurement(self) -> str:
        return self.measurement.get().extract_singleton()

    @staticmethod
    def _extract_float(param) -> float | None:
        from faebryk.library.Simulations import _extract_float
        return _extract_float(param)

    @staticmethod
    def _extract_text(param) -> str | None:
        """Return the raw text value of a StringParameter (as written in .ato)."""
        try:
            return param.get().try_extract_singleton()
        except Exception:
            return None

    def get_tran_step(self) -> float | None:
        return self._extract_float(self.tran_step)

    def get_tran_stop(self) -> float | None:
        return self._extract_float(self.tran_stop)

    def get_tran_start(self) -> float | None:
        return self._extract_float(self.tran_start)

    def get_tran_step_text(self) -> str | None:
        return self._extract_text(self.tran_step)

    def get_tran_stop_text(self) -> str | None:
        return self._extract_text(self.tran_stop)

    def get_tran_start_text(self) -> str | None:
        return self._extract_text(self.tran_start)

    def get_source_override(self) -> tuple[str, str] | None:
        name = self.source_name.get().try_extract_singleton()
        spec = self.source_spec.get().try_extract_singleton()
        if name is not None and spec is not None:
            return (name, spec)
        return None

    def get_settling_tolerance(self) -> float | None:
        return self._extract_float(self.settling_tolerance)

    def get_ac_start_freq(self) -> float | None:
        v = self.ac_start_freq.get().try_extract_singleton()
        return float(v) if v is not None else None

    def get_ac_stop_freq(self) -> float | None:
        v = self.ac_stop_freq.get().try_extract_singleton()
        return float(v) if v is not None else None

    def get_ac_points_per_dec(self) -> int | None:
        v = self.ac_points_per_dec.get().try_extract_singleton()
        return int(v) if v is not None else None

    def get_ac_source_name(self) -> str | None:
        return self.ac_source_name.get().try_extract_singleton()

    def get_ac_measure_freq(self) -> float | None:
        v = self.ac_measure_freq.get().try_extract_singleton()
        return float(v) if v is not None else None

    def get_ac_ref_net(self) -> str | None:
        raw = self.ac_ref_net.get().try_extract_singleton()
        if raw is None:
            return None
        return self._sanitize_net_name(raw)

    def get_diff_ref_net(self) -> str | None:
        raw = self.diff_ref_net.get().try_extract_singleton()
        if raw is None:
            return None
        return self._sanitize_net_name(raw)

    def get_extra_spice(self) -> list[str]:
        """Get extra SPICE lines to inject (pipe-separated)."""
        from faebryk.library.Simulations import _parse_pipe_list

        return _parse_pipe_list(self.extra_spice)

    def get_remove_elements(self) -> list[str]:
        """Get element names to remove from the netlist (comma-separated)."""
        from faebryk.library.Simulations import _parse_comma_list

        return _parse_comma_list(self.remove_elements)

    def get_vout_tolerance_pct(self) -> float | None:
        return self._extract_float(self.vout_tolerance_pct)

    def get_limit_scale_min(self) -> float | None:
        return self._extract_float(self.limit_scale_min)

    def get_limit_scale_max(self) -> float | None:
        return self._extract_float(self.limit_scale_max)

    def get_limit_scale(self) -> tuple[float | None, float | None]:
        return (self.get_limit_scale_min(), self.get_limit_scale_max())

    def get_required_plot_names(self) -> list[str]:
        """Get required plot variable names (comma-separated)."""
        raw = self.required_plot.get().try_extract_singleton()
        if raw is None:
            return []
        return [name.strip() for name in raw.split(",") if name.strip()]

    def get_supplementary_plot_names(self) -> list[str]:
        """Get supplementary plot variable names (comma-separated)."""
        raw = self.supplementary_plot.get().try_extract_singleton()
        if raw is None:
            return []
        return [name.strip() for name in raw.split(",") if name.strip()]

    def get_all_plot_names(self) -> list[str]:
        """Get all plot variable names (required + supplementary)."""
        return self.get_required_plot_names() + self.get_supplementary_plot_names()

    def get_plots(self) -> list:
        """Return all attached plot children (direct children only)."""
        try:
            return [
                p
                for p in self.get_children(
                    direct_only=True, types=fabll.Node, required_trait=F.is_plot
                )
                if p.get_trait(F.is_plot).get_title() is not None
            ]
        except Exception:
            return []
