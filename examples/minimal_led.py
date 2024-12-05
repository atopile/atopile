# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.examples.pickers import add_example_pickers

logger = logging.getLogger(__name__)


class App(Module):
    led: F.PoweredLED
    battery: F.Battery

    def __preinit__(self) -> None:
        self.led.power.connect(self.battery.power)

        # Parametrize
        self.led.led.color.merge(F.LED.Color.YELLOW)
        self.led.led.brightness.merge(
            TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value.value
        )

    def __postinit__(self) -> None:
        for m in self.get_children_modules(types=Module):
            add_example_pickers(m)
