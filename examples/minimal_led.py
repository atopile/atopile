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
        self.led.led.color.merge(F.LED.Color.YELLOW)
        self.led.led.brightness.merge(
            TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value.value
        )


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
