# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging

import faebryk.library._F as F
import typer
from faebryk.core.core import Module
from faebryk.exporters.pcb.kicad.layout.simple import SimpleLayout
from faebryk.library.has_pcb_layout_defined import has_pcb_layout_defined
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.library.has_pcb_position_defined import has_pcb_position_defined
from faebryk.libs.brightness import TypicalLuminousIntensity
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
        self.NODEs.led.NODEs.led.PARAMs.brightness.merge(
            TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value.value
        )

        # Layout
        Point = has_pcb_position.Point
        L = has_pcb_position.layer_type

        # Powered led layout
        self.NODEs.led.add_trait(
            has_pcb_layout_defined(
                SimpleLayout(
                    layouts=[
                        SimpleLayout.SubLayout(
                            mod_type=F.LED,
                            position=Point((0, 0, 0, L.TOP_LAYER)),
                        ),
                        SimpleLayout.SubLayout(
                            mod_type=F.Resistor,
                            position=Point((10, 0, 0, L.TOP_LAYER)),
                        ),
                    ]
                )
            )
        )

        layout = SimpleLayout(
            layouts=[
                SimpleLayout.SubLayout(
                    mod_type=F.PoweredLED,
                    position=Point((0, 0, 0, L.TOP_LAYER)),
                ),
                SimpleLayout.SubLayout(
                    mod_type=F.Battery,
                    position=Point((0, 30, 180, L.TOP_LAYER)),
                ),
            ]
        )
        self.add_trait(has_pcb_layout_defined(layout))
        self.add_trait(has_pcb_position_defined(Point((100, 100, 0, L.TOP_LAYER))))


def main():
    logger.info("Building app")
    app = App()

    logger.info("Export")
    tag_and_export_module_to_netlist(app, pcb_transform=True)


if __name__ == "__main__":
    setup_basic_logging()
    logger.info("Running experiment")

    typer.run(main)
