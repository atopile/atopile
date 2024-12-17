# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class App(Module):
    led: F.PoweredLED
    battery: F.ButtonCell

    def __preinit__(self) -> None:
        self.led.power.connect(self.battery.power)

        # Parametrize
        self.led.led.color.constrain_subset(F.LED.Color.RED)
        self.led.led.brightness.constrain_subset(
            TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value
        )

        # TODO remove when we have a battery picker
        self.battery.voltage.alias_is(L.Single(3 * P.V))
        self.battery.add(
            F.has_explicit_part.by_supplier(
                "C5239862",
                pinmap={
                    "1": self.battery.power.lv,
                    "2": self.battery.power.hv,
                },
            )
        )
