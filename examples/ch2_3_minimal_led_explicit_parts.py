# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class App(Module):
    led: F.PoweredLED
    battery: F.Battery

    def __preinit__(self) -> None:
        self.led.power.connect(self.battery.power)

        self.led.led.add(F.has_explicit_part.by_supplier("C965802"))
        self.led.current_limiting_resistor.add(
            F.has_explicit_part.by_supplier("C159037")
        )

        buttoncell = self.battery.specialize(F.ButtonCell())
        buttoncell.add(
            F.has_explicit_part.by_supplier(
                "C5239862",
                pinmap={"1": self.battery.power.lv, "2": self.battery.power.hv},
            )
        )
        buttoncell.power.voltage.alias_is(3 * P.V)
