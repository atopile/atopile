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
