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
from faebryk.exporters.pcb.layout.typehierarchy import LayoutTypeHierarchy
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class App(Module):
    led = L.f_field(F.LEDIndicator)(use_mosfet=False)
    mcu: F.RP2040_ReferenceDesign
    usb_power: F.USB_C_PSU_Vertical

    def __preinit__(self) -> None:
        # Parametrize
        self.led.led.led.color.constrain_subset(F.LED.Color.YELLOW)
        self.led.led.led.brightness.constrain_subset(
            TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value
        )

        self.usb_power.power_out.connect(self.mcu.usb.usb_if.buspower)
        self.mcu.rp2040.gpio[25].connect(self.led.logic_in)
        self.mcu.rp2040.pinmux.enable(self.mcu.rp2040.gpio[25])

        self._set_layout()

        # TODO remove when we have a fuse picker
        self.usb_power.fuse.add(F.has_explicit_part.by_supplier("C914087"))

    def _set_layout(self):
        LT = F.has_pcb_position.layer_type
        Point = F.has_pcb_position.Point
        # set center
        self.add(F.has_pcb_position_defined(Point((50, 50, 0, LT.TOP_LAYER))))

        layout = LayoutTypeHierarchy(
            layouts=[
                LayoutTypeHierarchy.Level(
                    mod_type=type(self.led),
                    layout=LayoutAbsolute(Point((0, 0, 0, LT.NONE))),
                    children_layout=LayoutExtrude((0, -5)),
                    direct_children_only=False,
                ),
                LayoutTypeHierarchy.Level(
                    mod_type=type(self.usb_power),
                    layout=LayoutAbsolute(Point((-20, 0, 0, LT.NONE))),
                    children_layout=LayoutExtrude((0, -5)),
                    direct_children_only=False,
                ),
                LayoutTypeHierarchy.Level(
                    mod_type=type(self.mcu),
                    layout=LayoutAbsolute(Point((30, 0, 0, LT.NONE))),
                ),
            ]
        )
        self.add(F.has_pcb_layout_defined(layout))
