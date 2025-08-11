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

    rated_common_mode_rejection_ratio = L.p_field(
        units=P.dB,
        likely_constrained=True,
        soft_set=L.Range(quantity(60, P.dB), quantity(120, P.dB)),
        tolerance_guess=10 * P.percent,
    )
    rated_input_bias_current = L.p_field(
        units=P.A,
        likely_constrained=True,
        soft_set=L.Range(1 * P.pA, 1 * P.µA),
        tolerance_guess=20 * P.percent,
    )
    rated_input_hysteresis_voltage = L.p_field(
        units=P.V,
        likely_constrained=True,
        soft_set=L.Range(1 * P.mV, 100 * P.mV),
        tolerance_guess=15 * P.percent,
    )
    rated_input_offset_voltage = L.p_field(
        units=P.V,
        soft_set=L.Range(10 * P.µV, 10 * P.mV),
        tolerance_guess=20 * P.percent,
    )
    rated_propagation_delay = L.p_field(
        units=P.s,
        soft_set=L.Range(10 * P.ns, 1 * P.ms),
        tolerance_guess=15 * P.percent,
    )
    rated_output_type = L.p_field(
        domain=L.Domains.ENUM(OutputType),
        likely_constrained=True,
        soft_set=L.Domains.ENUM(OutputType.PushPull),
    )

    @L.rt_field
    def pickable(self):
        return F.is_pickable_by_type(
            endpoint=F.is_pickable_by_type.Endpoint.COMPARATORS,
            params=[
                self.rated_common_mode_rejection_ratio,
                self.rated_input_bias_current,
                self.rated_input_hysteresis_voltage,
                self.rated_input_offset_voltage,
                self.rated_propagation_delay,
                self.rated_output_type,
            ],
        )

    power: F.ElectricPower
    inverting_input: F.Electrical
    non_inverting_input: F.Electrical
    output: F.Electrical

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import Comparator, Resistor, ElectricPower, Electrical

        comparator = new Comparator
        comparator.common_mode_rejection_ratio = 80dB +/- 10%
        comparator.input_bias_current = 1nA +/- 50%
        comparator.input_hysteresis_voltage = 5mV +/- 20%
        comparator.input_offset_voltage = 1mV +/- 30%
        comparator.propagation_delay = 100ns +/- 20%
        comparator.output_type = Comparator.OutputType.PushPull
        comparator.package = "SOIC-8"

        # Power supply connections (dual supply)
        power_pos = new ElectricPower
        power_neg = new ElectricPower
        assert power_pos.voltage within 5V +/- 5%
        assert power_neg.voltage within -5V +/- 5%
        comparator.power.hv ~ power_pos.hv
        comparator.power.lv ~ power_neg.lv

        # Create voltage reference with resistor divider
        ref_resistor_high = new Resistor
        ref_resistor_low = new Resistor
        ref_resistor_high.resistance = 10kohm +/- 1%
        ref_resistor_low.resistance = 10kohm +/- 1%

        # Reference voltage = Vcc/2
        power_pos.hv ~> ref_resistor_high ~> comparator.non_inverting_input
        comparator.non_inverting_input ~> ref_resistor_low ~> power_neg.lv

        # Connect input signal to inverting input
        input_signal ~ comparator.inverting_input
        output_signal ~ comparator.output

        # Output will be HIGH when input_signal > reference_voltage
        """,
        language=F.has_usage_example.Language.ato,
    )
