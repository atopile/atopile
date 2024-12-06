# This file is part of the atopile project
# SPDX-License-Identifier: MIT

"""
This file contains an atopile sample.
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
    battery: F.Battery

    def __preinit__(self) -> None:
        self.led.power.connect(self.battery.power)

        # Parametrize
        self.led.led.color.constrain_subset(F.LED.Color.YELLOW)
        self.led.led.brightness.constrain_subset(
            TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value
        )

        self.battery.add(F.has_designator_prefix_defined("B"))
        self.battery.power.voltage.constrain_superset(
            L.Range(2.5 * P.volt, 4.2 * P.volt)
        )
        self.battery.add(F.has_descriptive_properties_defined({"LCSC": "C5239862"}))
        self.battery.add(
            F.can_attach_to_footprint_via_pinmap(
                {
                    "1": self.battery.power.lv,
                    "2": self.battery.power.hv,
                }
            )
        )

        self.led.add(F.has_designator_prefix_defined("D"))
        self.led.add(F.has_descriptive_properties_defined({"LCSC": "C72038"}))
        self.led.add(
            F.can_attach_to_footprint_via_pinmap(
                {"1": self.led.led.cathode, "2": self.led.led.anode},
            )
        )
