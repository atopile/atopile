# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging

import typer

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.exporters.pcb.layout.absolute import LayoutAbsolute
from faebryk.exporters.pcb.layout.extrude import LayoutExtrude
from faebryk.exporters.pcb.layout.heuristic_decoupling import (
    LayoutHeuristicElectricalClosenessDecouplingCaps,
)
from faebryk.exporters.pcb.layout.heuristic_pulls import (
    LayoutHeuristicElectricalClosenessPullResistors,
)
from faebryk.exporters.pcb.layout.typehierarchy import LayoutTypeHierarchy
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.examples.buildutil import apply_design_to_pcb
from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class App(Module):
    leds: F.PoweredLED
    battery: F.Battery
    eeprom: F.M24C08_FMN6TP

    def __preinit__(self) -> None:
        self.leds.power.connect(self.battery.power)

        # Parametrize
        self.leds.led.color.merge(F.LED.Color.YELLOW)
        self.leds.led.brightness.merge(
            TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value.value
        )

        self.eeprom.power.voltage.merge(3.3 * P.V)
        self.eeprom.set_address(0x0)

        # Layout
        Point = F.has_pcb_position.Point
        L = F.has_pcb_position.layer_type

        layout = LayoutTypeHierarchy(
            layouts=[
                LayoutTypeHierarchy.Level(
                    mod_type=F.PoweredLED,
                    layout=LayoutAbsolute(Point((0, 0, 0, L.TOP_LAYER))),
                    children_layout=LayoutTypeHierarchy(
                        layouts=[
                            LayoutTypeHierarchy.Level(
                                mod_type=(F.LED, F.Resistor),
                                layout=LayoutExtrude((0, 5)),
                            ),
                        ]
                    ),
                ),
                LayoutTypeHierarchy.Level(
                    mod_type=F.Battery,
                    layout=LayoutAbsolute(Point((0, 20, 0, L.BOTTOM_LAYER))),
                ),
                LayoutTypeHierarchy.Level(
                    mod_type=F.M24C08_FMN6TP,
                    layout=LayoutAbsolute(Point((15, 10, 0, L.TOP_LAYER))),
                ),
            ]
        )
        self.add(F.has_pcb_layout_defined(layout))
        self.add(F.has_pcb_position_defined(Point((50, 50, 0, L.NONE))))

        LayoutHeuristicElectricalClosenessDecouplingCaps.add_to_all_suitable_modules(
            self
        )
        LayoutHeuristicElectricalClosenessPullResistors.add_to_all_suitable_modules(
            self
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
