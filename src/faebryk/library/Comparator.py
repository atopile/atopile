# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class Comparator(Module):
    class OutputType(Enum):
        Differential = auto()
        PushPull = auto()
        OpenDrain = auto()

    common_mode_rejection_ratio = L.p_field(
        unit=P.dB,
        likely_constrained=True,
        soft_set=L.Range(60 * P.dB, 120 * P.dB),
        tolerance_guess=10 * P.percent,
    )
    input_bias_current = L.p_field(
        unit=P.A,
        likely_constrained=True,
        soft_set=L.Range(1 * P.pA, 1 * P.µA),
        tolerance_guess=20 * P.percent,
    )
    input_hysteresis_voltage = L.p_field(
        unit=P.V,
        likely_constrained=True,
        soft_set=L.Range(1 * P.mV, 100 * P.mV),
        tolerance_guess=15 * P.percent,
    )
    input_offset_voltage = L.p_field(
        unit=P.V,
        soft_set=L.Range(10 * P.µV, 10 * P.mV),
        tolerance_guess=20 * P.percent,
    )
    propagation_delay = L.p_field(
        unit=P.s,
        soft_set=L.Range(10 * P.ns, 1 * P.ms),
        tolerance_guess=15 * P.percent,
    )
    output_type = L.p_field(
        domain=L.Domains.ENUM(OutputType),
        likely_constrained=True,
    )

    power: F.ElectricPower
    inverting_input: F.Electrical
    non_inverting_input: F.Electrical
    output: F.Electrical

    @L.rt_field
    def simple_value_representation(self):
        return F.has_simple_value_representation_based_on_params(
            (
                self.common_mode_rejection_ratio,
                self.input_bias_current,
                self.input_hysteresis_voltage,
                self.input_offset_voltage,
                self.propagation_delay,
            ),
            lambda cmrr, ib, vhys, vos, tpd: (
                ", ".join(
                    [
                        f"{cmrr} CMRR",
                        f"{ib.as_unit('A')} Ib",
                        f"{vhys.as_unit('V')} Vhys",
                        f"{vos.as_unit('V')} Vos",
                        f"{tpd.as_unit('s')} tpd",
                    ]
                )
            ),
        )

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.U
    )
