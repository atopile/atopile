# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging

import typer

import faebryk.library._F as F
from faebryk.core.core import Module
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.examples.buildutil import (
    apply_design_to_pcb,
)
from faebryk.libs.logging import setup_basic_logging

logger = logging.getLogger(__name__)


class App(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODES(Module.NODES()):
            led = F.PoweredLED()
            battery = F.Battery()

        self.NODEs = _NODES(self)

        self.NODEs.led.IFs.power.connect(self.NODEs.battery.IFs.power)

        # Parametrize
        self.NODEs.led.NODEs.led.PARAMs.color.merge(F.LED.Color.YELLOW)
        self.NODEs.led.NODEs.led.PARAMs.brightness.merge(
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
