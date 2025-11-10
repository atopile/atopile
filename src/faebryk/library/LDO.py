# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.core.node as fabll
import faebryk.library._F as F

# from faebryk.libs.util import assert_once


class LDO(fabll.Node):
    # ----------------------------------------
    #                 enums
    # ----------------------------------------
    # TODO: add this back?
    # @assert_once
    # def enable_output(self):
    #     self.enable.set(True)

    class OutputType(Enum):
        FIXED = auto()
        ADJUSTABLE = auto()

    class OutputPolarity(Enum):
        POSITIVE = auto()
        NEGATIVE = auto()

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    enable = F.EnablePin.MakeChild()
    power_in = F.ElectricPower.MakeChild()
    power_out = F.ElectricPower.MakeChild()

    max_input_voltage = F.Parameters.NumericParameter.MakeChild(F.Units.Volt)
    output_voltage = F.Parameters.NumericParameter.MakeChild(F.Units.Volt)
    quiescent_current = F.Parameters.NumericParameter.MakeChild(F.Units.Ampere)
    dropout_voltage = F.Parameters.NumericParameter.MakeChild(F.Units.Volt)
    ripple_rejection_ratio = F.Parameters.NumericParameter.MakeChild(F.Units.Decibel)
    output_polarity = F.Parameters.EnumParameter.MakeChild(OutputPolarity)
    output_type = F.Parameters.EnumParameter.MakeChild(OutputType)
    output_current = F.Parameters.NumericParameter.MakeChild(F.Units.Ampere)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.is_module.MakeChild()

    # ----------------------------------------
    #                WIP
    # ----------------------------------------

    # def __preinit__(self):
    #     self.max_input_voltage.constrain_ge(self.power_in.voltage)
    #     self.power_out.voltage.constrain_subset(self.output_voltage)

    #     self.enable.enable.reference.connect(self.power_in)
    #     # TODO: should be implemented differently (see below)
    #     # if self.output_polarity == self.OutputPolarity.NEGATIVE:
    #     #    self.power_in.hv.connect(self.power_out.hv)
    #     # else:
    #     #    self.power_in.lv.connect(self.power_out.lv)

    _single_electric_reference = fabll.ChildField(F.has_single_electric_reference)

    _can_bridge = F.can_bridge.MakeChild(in_=power_in, out_=power_out)

    S = F.has_simple_value_representation.Spec
    _simple_repr = F.has_simple_value_representation.MakeChild(
        S(output_voltage, tolerance=True),
        S(output_current),
        S(ripple_rejection_ratio),
        S(dropout_voltage),
        S(max_input_voltage, prefix="Vin max"),
        S(quiescent_current, prefix="Iq"),
    )

    designator_prefix = F.has_designator_prefix.MakeChild(
        F.has_designator_prefix.Prefix.U
    )

    _pin_association_heuristic = F.has_pin_association_heuristic.MakeChild(
        mapping={
            power_in.get().hv: ["Vin", "Vi", "in"],
            power_out.get().hv: ["Vout", "Vo", "out", "output"],
            power_in.get().lv: ["GND", "V-", "ADJ/GND"],
            enable.get().enable.get().line: ["EN", "Enable"],
        },
        accept_prefix=False,
        case_sensitive=False,
    )

    usage_example = F.has_usage_example.MakeChild(
        example="""
        import LDO, ElectricPower, Capacitor

        ldo = new LDO
        ldo.output_voltage = 3.3V +/- 2%
        ldo.max_input_voltage = 6V
        ldo.max_current = 1A
        ldo.dropout_voltage = 300mV +/- 50%
        ldo.output_type = LDO.OutputType.FIXED
        ldo.package = "SOT-223"

        # Connect input power (typically 5V)
        power_5v = new ElectricPower
        assert power_5v.voltage within 5V +/- 5%
        ldo.power_in ~ power_5v

        # Connect output power (regulated 3.3V)
        power_3v3 = new ElectricPower
        ldo.power_out ~ power_3v3

        # Enable the LDO
        ldo.enable_output()

        # Add input and output capacitors
        input_cap = new Capacitor
        output_cap = new Capacitor
        input_cap.capacitance = 1uF +/- 20%
        output_cap.capacitance = 10uF +/- 20%
        ldo.power_in.hv ~> input_cap ~> ldo.power_in.lv
        ldo.power_out.hv ~> output_cap ~> ldo.power_out.lv
        """,
        language=F.has_usage_example.Language.ato,
    ).put_on_type()
