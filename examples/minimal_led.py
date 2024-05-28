# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging

import faebryk.library._F as F
import typer
from faebryk.core.core import Module
from faebryk.libs.experiments.buildutil import (
    tag_and_export_module_to_netlist,
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
        self.NODEs.led.NODEs.led.PARAMs.brightness.merge(F.Range.lower_bound(30e-3))


def main():
    logger.info("Building app")
    app = App()

    logger.info("Export")
    tag_and_export_module_to_netlist(app)


if __name__ == "__main__":
    setup_basic_logging()
    logger.info("Running experiment")

    typer.run(main)
