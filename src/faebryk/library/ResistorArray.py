# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class ResistorArray(Module):
    resistance = L.p_field(units=P.ohm)
    rated_power = L.p_field(units=P.W)
    rated_voltage = L.p_field(units=P.V)

    @L.rt_field
    def resistors(self):
        return times(self._resistor_count, F.Resistor)

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.R
    )

    def __init__(self, resistor_count: int = 4):
        super().__init__()
        self._resistor_count = resistor_count

    def __preinit__(self):
        for resistor in self.resistors:
            resistor.resistance = self.resistance
            resistor.max_power = self.rated_power
            resistor.max_voltage = self.rated_voltage

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        #pragma experiment("BRIDGE_CONNECT")
        #pragma experiment("FOR_LOOP")
        #pragma experiment("MODULE_TEMPLATING")
        import ResistorArray, ElectricPower, ElectricLogic

        module UsageExample:
            # Create resistor array for pull-ups
            pullup_array = new ResistorArray<resistor_count=4>
            pullup_array.lcsc_id = "C29718"
            # pullup_array.resistance = 10kohm +/- 5%
            # pullup_array.rated_power = 125mW
            # pullup_array.rated_voltage = 50V
            # pullup_array.package = "0603"

            # Connect power supply
            power_3v3 = new ElectricPower
            assert power_3v3.voltage within 3.3V +/- 5%

            # Use for GPIO pull-ups
            gpio_signals = new ElectricLogic[4]
            for gpio_signal in gpio_signals:
                gpio_signal.reference ~ power_3v3

            gpio_signals[0].line ~> pullup_array.resistors[0] ~> power_3v3.hv
            gpio_signals[1].line ~> pullup_array.resistors[1] ~> power_3v3.hv
            gpio_signals[2].line ~> pullup_array.resistors[2] ~> power_3v3.lv
            gpio_signals[3].line ~> pullup_array.resistors[3] ~> power_3v3.lv
        """,
        language=F.has_usage_example.Language.ato,
    )
