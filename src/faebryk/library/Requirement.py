# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.library.Captures import DCOPCapture, TransientCapture
from faebryk.library.Measurements import (
    AverageValue,
    FinalValue,
    Overshoot,
    PeakToPeak,
    RMS,
    SettlingTime,
)

_CAPTURE_KEYS: dict[type, str] = {
    DCOPCapture: "dcop",
    TransientCapture: "transient",
}

_MEASUREMENT_KEYS: dict[type, str] = {
    FinalValue: "final_value",
    AverageValue: "average",
    SettlingTime: "settling_time",
    PeakToPeak: "peak_to_peak",
    Overshoot: "overshoot",
    RMS: "rms",
}

CaptureType = type[DCOPCapture] | type[TransientCapture]
MeasurementType = (
    type[FinalValue]
    | type[AverageValue]
    | type[SettlingTime]
    | type[PeakToPeak]
    | type[Overshoot]
    | type[RMS]
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
    source_name = F.Parameters.StringParameter.MakeChild()
    source_spec = F.Parameters.StringParameter.MakeChild()

    # Settling time config
    settling_tolerance = F.Parameters.StringParameter.MakeChild()

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
        source_override: tuple[str, str] | None = None,
        settling_tolerance: float | None = None,
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
        if source_override is not None:
            self.source_name.get().set_singleton(value=source_override[0])
            self.source_spec.get().set_singleton(value=source_override[1])
        if settling_tolerance is not None:
            self.settling_tolerance.get().set_singleton(value=str(settling_tolerance))

        return self

    # -- Getters --

    def get_name(self) -> str:
        return self.req_name.get().extract_singleton()

    def get_net(self) -> str:
        return self.net.get().extract_singleton()

    def get_min_val(self) -> float:
        return float(self.min_val.get().extract_singleton())

    def get_typical(self) -> float:
        return float(self.typical.get().extract_singleton())

    def get_max_val(self) -> float:
        return float(self.max_val.get().extract_singleton())

    def get_justification(self) -> str | None:
        return self.justification.get().try_extract_singleton()

    def get_context_nets(self) -> list[str]:
        raw = self.context_nets.get().try_extract_singleton()
        if raw is None:
            return []
        return [n.strip() for n in raw.split(",") if n.strip()]

    def get_capture(self) -> str:
        return self.capture.get().extract_singleton()

    def get_measurement(self) -> str:
        return self.measurement.get().extract_singleton()

    def get_tran_step(self) -> float | None:
        v = self.tran_step.get().try_extract_singleton()
        return float(v) if v is not None else None

    def get_tran_stop(self) -> float | None:
        v = self.tran_stop.get().try_extract_singleton()
        return float(v) if v is not None else None

    def get_source_override(self) -> tuple[str, str] | None:
        name = self.source_name.get().try_extract_singleton()
        spec = self.source_spec.get().try_extract_singleton()
        if name is not None and spec is not None:
            return (name, spec)
        return None

    def get_settling_tolerance(self) -> float | None:
        v = self.settling_tolerance.get().try_extract_singleton()
        return float(v) if v is not None else None
