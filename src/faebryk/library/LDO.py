# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.units import P, quantity
from faebryk.libs.util import assert_once


class LDO(fabll.Node):
    # ----------------------------------------
    #                 enums
    # ----------------------------------------
    @assert_once
    def enable_output(self):
        self.enable.set(True)

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

    max_input_voltage = fabll.Parameter.MakeChild_Numeric(F.Units.Volt)
    output_voltage = fabll.Parameter.MakeChild_Numeric(F.Units.Volt)
    quiescent_current = fabll.Parameter.MakeChild_Numeric(F.Units.Ampere)
    dropout_voltage = fabll.Parameter.MakeChild_Numeric(F.Units.Volt)
    ripple_rejection_ratio = fabll.Parameter.MakeChild_Numeric(F.Units.Decibel)
    output_polarity = fabll.Parameter.MakeChild_Enum(OutputPolarity)
    output_type = fabll.Parameter.MakeChild_Enum(OutputType)
    output_current = fabll.Parameter.MakeChild_Numeric(F.Units.Ampere)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.is_module.MakeChild()

    # ----------------------------------------
    #                WIP
    # ----------------------------------------
    # @fabll.rt_field
    # def pickable(self) -> F.is_pickable_by_type:
    #     return F.is_pickable_by_type(
    #         F.is_pickable_by_type.Type.LDO,
    #         {
    #             "max_input_voltage": self.max_input_voltage,
    #             "output_voltage": self.output_voltage,
    #             "quiescent_current": self.quiescent_current,
    #             "dropout_voltage": self.dropout_voltage,
    #             # TODO: add support in backend
    #             # "ripple_rejection_ratio": self.ripple_rejection_ratio,
    #             "output_polarity": self.output_polarity,
    #             "output_type": self.output_type,
    #             "output_current": self.output_current,
    #         },
    #     )

    def __preinit__(self):
        self.max_input_voltage.constrain_ge(self.power_in.voltage)
        self.power_out.voltage.constrain_subset(self.output_voltage)

        self.enable.enable.reference.connect(self.power_in)
        # TODO: should be implemented differently (see below)
        # if self.output_polarity == self.OutputPolarity.NEGATIVE:
        #    self.power_in.hv.connect(self.power_out.hv)
        # else:
        #    self.power_in.lv.connect(self.power_out.lv)

    _single_electric_reference = fabll.ChildField(F.has_single_electric_reference)

    def can_bridge(self):
        return F.can_bridge(self.power_in, self.power_out)

    def simple_value_representation(self):
        S = F.has_simple_value_representation.Spec
        return F.has_simple_value_representation(
            S(self.output_voltage, tolerance=True),
            S(self.output_current),
            S(self.ripple_rejection_ratio),
            S(self.dropout_voltage),
            S(self.max_input_voltage, prefix="Vin max"),
            S(self.quiescent_current, prefix="Iq"),
            prefix="LDO",
        )

    designator_prefix = F.has_designator_prefix.MakeChild(
        F.has_designator_prefix.Prefix.U
    )

    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic(
            mapping={
                self.power_in.hv: ["Vin", "Vi", "in"],
                self.power_out.hv: ["Vout", "Vo", "out", "output"],
                self.power_in.lv: ["GND", "V-", "ADJ/GND"],
                self.enable.enable.line: ["EN", "Enable"],
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
