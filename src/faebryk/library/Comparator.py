# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P, quantity


class Comparator(Module):
    class OutputType(Enum):
        Differential = auto()
        PushPull = auto()
        OpenDrain = auto()

    common_mode_rejection_ratio = L.p_field(
        units=P.dB,
        likely_constrained=True,
        soft_set=L.Range(quantity(60, P.dB), quantity(120, P.dB)),
        tolerance_guess=10 * P.percent,
    )
    input_bias_current = L.p_field(
        units=P.A,
        likely_constrained=True,
        soft_set=L.Range(1 * P.pA, 1 * P.µA),
        tolerance_guess=20 * P.percent,
    )
    input_hysteresis_voltage = L.p_field(
        units=P.V,
        likely_constrained=True,
        soft_set=L.Range(1 * P.mV, 100 * P.mV),
        tolerance_guess=15 * P.percent,
    )
    input_offset_voltage = L.p_field(
        units=P.V,
        soft_set=L.Range(10 * P.µV, 10 * P.mV),
        tolerance_guess=20 * P.percent,
    )
    propagation_delay = L.p_field(
        units=P.s,
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
        S = F.has_simple_value_representation_based_on_params_chain.Spec
        return F.has_simple_value_representation_based_on_params_chain(
            S(self.common_mode_rejection_ratio, suffix="CMRR"),
            S(self.input_bias_current, suffix="Ib"),
            S(self.input_hysteresis_voltage, suffix="Vhys"),
            S(self.input_offset_voltage, suffix="Vos"),
            S(self.propagation_delay, suffix="tpd"),
        )

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )
