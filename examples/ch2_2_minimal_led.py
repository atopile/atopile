# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class App(Module):
    led: F.PoweredLED
    battery: F.ButtonCell

    def __preinit__(self) -> None:
        self.led.power.connect(self.battery.power)

        # TODO: remove when we have a LED picker
        self.led.led.add(F.has_explicit_part.by_supplier("C965802"))
        self.led.led.forward_voltage.alias_is(2.4 * P.V)
        self.led.led.max_brightness.alias_is(435 * P.millicandela)
        self.led.led.max_current.alias_is(20 * P.mA)
        self.led.led.color.alias_is(F.LED.Color.YELLOW)

        # Parametrize
        self.led.led.color.constrain_subset(F.LED.Color.YELLOW)
        self.led.led.brightness.constrain_subset(
            TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value
        )

        # TODO remove when we have a battery picker
        self.battery.add(
            F.has_explicit_part.by_supplier(
                "C5239862",
                pinmap={
                    "1": self.battery.power.lv,
                    "2": self.battery.power.hv,
                },
            )
        )
        self.battery.voltage.alias_is(3 * P.V)
