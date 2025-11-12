# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class ResistorArray(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    resistors_ = F.Collections.PointerSet.MakeChild()
    resistance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ohm)
    rated_power = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Watt)
    rated_voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.is_module.MakeChild()

    designator_prefix = F.has_designator_prefix.MakeChild(
        F.has_designator_prefix.Prefix.R
    )

    # ----------------------------------------
    #                WIP
    # ----------------------------------------
    @classmethod
    def MakeChild(cls, resistor_count: int):
        out = fabll._ChildField(cls)
        for i in range(resistor_count):
            resistor_child_field = F.Resistor.MakeChild()
            out.add_dependant(resistor_child_field)
            out.add_dependant(
                F.Collections.PointerSet.EdgeField(
                    [out, cls.resistors_],
                    [resistor_child_field],
                )
            )
        return out

    @property
    def resistors(self) -> list[F.Resistor]:
        print(self.resistors_.get())
        return [
            F.Resistor.bind_instance(resistor.instance)
            for resistor in self.resistors_.get().as_list()
        ]

    usage_example = F.has_usage_example.MakeChild(
        example="""
        import ResistorArray, ElectricPower, ElectricLogic

        # Create 8-resistor array for pull-ups
        pullup_array = new ResistorArray(resistor_count=8)
        pullup_array.resistance = 10kohm +/- 5%
        pullup_array.rated_power = 125mW
        pullup_array.rated_voltage = 50V
        pullup_array.package = "4816"  # 8-pin SIP package

        # Connect power supply
        power_3v3 = new ElectricPower
        assert power_3v3.voltage within 3.3V +/- 5%

        # Use for GPIO pull-ups
        gpio_signals = new ElectricLogic[8]
        for i in range(8):
            gpio_signals[i].reference ~ power_3v3
            gpio_signals[i].line ~> pullup_array.resistors[i] ~> power_3v3.hv
            microcontroller.gpio[i] ~ gpio_signals[i].line

        # Alternative: 4-resistor array for I2C/SPI bus termination
        termination_array = new ResistorArray(resistor_count=4)
        termination_array.resistance = 33ohm +/- 1%
        termination_array.package = "4806"  # 4-pin array

        # Common applications: pull-up/pull-down networks, bus termination,
        # voltage dividers, current limiting, LED drivers
        """,
        language=F.has_usage_example.Language.ato,
    )
