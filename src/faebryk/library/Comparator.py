# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.core.node as fabll
import faebryk.library._F as F


class Comparator(fabll.Node):
    class OutputType(Enum):
        Differential = auto()
        PushPull = auto()
        OpenDrain = auto()

    common_mode_rejection_ratio = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Decibel,
    )
    input_bias_current = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Ampere,
    )
    input_hysteresis_voltage = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Volt,
    )
    input_offset_voltage = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Volt,
    )
    propagation_delay = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Second,
    )
    output_type = fabll.Parameter.MakeChild_Enum(
        enum_t=OutputType,
    )

    power = F.ElectricPower.MakeChild()
    inverting_input = F.Electrical.MakeChild()
    non_inverting_input = F.Electrical.MakeChild()
    output = F.Electrical.MakeChild()

    S = F.has_simple_value_representation_based_on_params_chain.Spec
    _simple_repr = F.has_simple_value_representation_based_on_params_chain.MakeChild(
        S(common_mode_rejection_ratio, suffix="CMRR"),
        S(input_bias_current, suffix="Ib"),
        S(input_hysteresis_voltage, suffix="Vhys"),
        S(input_offset_voltage, suffix="Vos"),
        S(propagation_delay, suffix="tpd"),
    ).put_on_type()

    designator_prefix = F.has_designator_prefix.MakeChild(
        F.has_designator_prefix.Prefix.U
    ).put_on_type()

    usage_example = F.has_usage_example.MakeChild(
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
    ).put_on_type()
