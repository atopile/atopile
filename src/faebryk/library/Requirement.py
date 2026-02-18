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
    net = F.Parameters.StringParameter.MakeChild()
    context_nets = F.Parameters.StringParameter.MakeChild()
    min_val = F.Parameters.StringParameter.MakeChild()
    typical = F.Parameters.StringParameter.MakeChild()
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
        self.min_val.get().set_singleton(value=str(min_val))
        self.typical.get().set_singleton(value=str(typical))
        self.max_val.get().set_singleton(value=str(max_val))

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

    def get_min_val(self) -> float:
        v = self._extract_float(self.min_val)
        if v is None:
            raise ValueError("min_val is not set")
        return v

    def get_typical(self) -> float:
        v = self._extract_float(self.typical)
        if v is None:
            raise ValueError("typical is not set")
        return v

    def get_max_val(self) -> float:
        v = self._extract_float(self.max_val)
        if v is None:
            raise ValueError("max_val is not set")
        return v

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

    def _extract_float(self, param) -> float | None:
        """Extract a float from a StringParameter, handling solver type coercion.

        The solver may resolve string values like "2e-7" to Numbers.
        This method handles both Strings and Numbers transparently.
        """
        try:
            v = param.get().try_extract_singleton()
            return float(v) if v is not None else None
        except Exception:
            # Solver resolved StringParameter to Numbers — extract numerically
            try:
                from faebryk.library.Literals import Numbers

                nums = param.get().is_parameter_operatable.get().try_extract_superset(
                    lit_type=Numbers
                )
                if nums is not None:
                    return float(nums.get_single())
            except Exception:
                pass
            return None

    def get_tran_step(self) -> float | None:
        return self._extract_float(self.tran_step)

    def get_tran_stop(self) -> float | None:
        return self._extract_float(self.tran_stop)

    def get_tran_start(self) -> float | None:
        return self._extract_float(self.tran_start)

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
        raw = self.extra_spice.get().try_extract_singleton()
        if raw is None:
            return []
        return [line.strip() for line in raw.split("|") if line.strip()]

    def get_remove_elements(self) -> list[str]:
        """Get element names to remove from the netlist (comma-separated)."""
        raw = self.remove_elements.get().try_extract_singleton()
        if raw is None:
            return []
        return [name.strip() for name in raw.split(",") if name.strip()]
