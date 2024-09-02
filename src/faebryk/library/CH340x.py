# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class CH340x(Module):
    usb: F.USB2_0
    uart: F.UART
    tnow: F.Electrical
    gpio_power: F.ElectricPower

    designator = L.f_field(F.has_designator_prefix_defined)("U")
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://wch-ic.com/downloads/file/79.html"
    )

    def __preinit__(self):
        self.gpio_power.lv.connect(self.usb.usb_if.buspower.lv)

        self.gpio_power.voltage.merge(F.Range(0 * P.V, 5.3 * P.V))
        self.gpio_power.decoupled.decouple()
        self.usb.usb_if.buspower.voltage.merge(F.Range(4 * P.V, 5.3 * P.V))

        self.usb.usb_if.buspower.decoupled.decouple()

        self.gpio_power.lv.connect(self.usb.usb_if.buspower.lv)
