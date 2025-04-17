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
        self.battery.power.voltage.alias_is(3 * P.V)

        # Parametrize
        self.leds.led.color.constrain_subset(F.LED.Color.YELLOW)
        self.leds.led.brightness.constrain_subset(
            TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value
        )

        self.eeprom.ic.power.voltage.constrain_subset(
            L.Range.from_center_rel(3.3 * P.V, 0.05)
        )
        self.eeprom.ic.set_address(0x0)
        self.eeprom.ic.data.pull_up_sda.resistance.constrain_subset(
            L.Range.from_center_rel(2 * P.kohm, 0.1)
        )
        self.eeprom.ic.data.pull_up_scl.resistance.constrain_subset(
            L.Range.from_center_rel(2 * P.kohm, 0.1)
        )

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

        # TODO: remove when we have a LED picker
        self.leds.led.add(F.has_explicit_part.by_supplier("C965802"))
        self.leds.led.forward_voltage.alias_is(2.4 * P.V)
        self.leds.led.max_brightness.alias_is(435 * P.millicandela)
        self.leds.led.max_current.alias_is(20 * P.mA)
        self.leds.led.color.alias_is(F.LED.Color.YELLOW)

        # TODO remove when we have a battery picker
        self.battery.add(
            F.has_explicit_part.by_supplier(
                "C5239862",
                pinmap={
                    "1": self.battery.power.lv,
                    "2": self.battery.power.hv,
                },
            )
        )
        self.battery.voltage.alias_is(3 * P.V)
