# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class MCP2221A(Module):
    power: F.ElectricPower
    power_vusb: F.ElectricPower
    uart: F.UART_Base
    i2c: F.I2C
    gpio = L.list_field(4, F.Electrical)
    reset: F.ElectricLogic
    usb: F.USB2_0

    def __preinit__(self):
        self.power.lv.connect(self.power_vusb.lv)

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    @L.rt_field
    def can_be_decoupled(self):
        class _(F.can_be_decoupled.impl()):
            def decouple(self, owner: Module):
                obj = self.get_obj(MCP2221A)
                obj.power.decoupled.decouple(owner=owner)
                obj.power_vusb.decoupled.decouple(owner=owner)

        return _()
