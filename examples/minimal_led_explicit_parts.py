# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging

import typer

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.examples.buildutil import apply_design_to_pcb
from faebryk.libs.logging import setup_basic_logging

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

        self.led.led.add(F.has_descriptive_properties_defined({"LCSC": "C965802"}))
        self.led.current_limiting_resistor.add(
            F.has_descriptive_properties_defined({"LCSC": "C159037"})
        )

        buttoncell = self.battery.specialize(F.ButtonCell())
        buttoncell.add(F.has_descriptive_properties_defined({"LCSC": "C5239862"}))
        buttoncell.add(
            F.can_attach_to_footprint_via_pinmap(
                {
                    "1": self.battery.power.lv,
                    "2": self.battery.power.hv,
                }
            )
        )

        # Here is the hack: Disables param matching for LCSC & MFR picks
        from faebryk.libs.picker.jlcpcb.picker_lib import _MAPPINGS_BY_TYPE

        _MAPPINGS_BY_TYPE.clear()


# Boilerplate -----------------------------------------------------------------


def main():
    logger.info("Building app")
    app = App()

    logger.info("Export")
    apply_design_to_pcb(app)


if __name__ == "__main__":
    setup_basic_logging()
    logger.info("Running example")

    typer.run(main)
