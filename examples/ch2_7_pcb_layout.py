# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging

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
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class App(Module):
    leds: F.PoweredLED
    battery: F.Battery
    eeprom: F.M24C08_FMN6TP

    def __preinit__(self) -> None:
        self.leds.power.connect(self.battery.power)

        # Parametrize
        self.leds.led.color.constrain_subset(F.LED.Color.YELLOW)
        self.leds.led.brightness.constrain_subset(
            TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value
        )

        self.eeprom.ic.power.voltage.constrain_subset(
            L.Range.from_center_rel(3.3 * P.V, 0.05)
        )
        self.eeprom.ic.set_address(0x0)

        # Layout
        Point = F.has_pcb_position.Point
        Ly = F.has_pcb_position.layer_type

        layout = LayoutTypeHierarchy(
            layouts=[
                LayoutTypeHierarchy.Level(
                    mod_type=F.PoweredLED,
                    layout=LayoutAbsolute(Point((0, 0, 0, Ly.TOP_LAYER))),
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
                    layout=LayoutAbsolute(Point((0, 20, 0, Ly.BOTTOM_LAYER))),
                ),
                LayoutTypeHierarchy.Level(
                    mod_type=F.M24C08_FMN6TP,
                    layout=LayoutAbsolute(Point((15, 10, 0, Ly.TOP_LAYER))),
                ),
            ]
        )
        self.add(F.has_pcb_layout_defined(layout))
        self.add(F.has_pcb_position_defined(Point((50, 50, 0, Ly.NONE))))

        LayoutHeuristicElectricalClosenessDecouplingCaps.add_to_all_suitable_modules(
            self
        )
        LayoutHeuristicElectricalClosenessPullResistors.add_to_all_suitable_modules(
            self
        )
