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
    tnow: F.ElectricLogic
    gpio_power: F.ElectricPower

    designator = L.f_field(F.has_designator_prefix)(F.has_designator_prefix.Prefix.U)
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://wch-ic.com/downloads/file/79.html"
    )

    def __preinit__(self):
        self.gpio_power.lv.connect(self.usb.usb_if.buspower.lv)

        self.gpio_power.voltage.constrain_subset(L.Range(0 * P.V, 5.3 * P.V))
        self.usb.usb_if.buspower.voltage.constrain_subset(L.Range(4 * P.V, 5.3 * P.V))

        self.gpio_power.lv.connect(self.usb.usb_if.buspower.lv)

    @L.rt_field
    def can_be_decoupled(self):
        class _(F.can_be_decoupled.impl()):
            def decouple(self, owner: Module):
                obj = self.get_obj(CH340x)

                obj.gpio_power.decoupled.decouple(owner=owner)
                obj.usb.usb_if.buspower.decoupled.decouple(owner=owner)
