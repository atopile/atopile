# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class UART_RS485(Module):
    power: F.ElectricPower
    uart: F.UART_Base
    rs485: F.RS485HalfDuplex
    read_enable: F.ElectricLogic
    write_enable: F.ElectricLogic

    max_data_rate = L.p_field(units=P.baud)

    def __preinit__(self):
        self.max_data_rate.alias_is(self.uart.baud)
        self.power.voltage.constrain_subset(L.Range(3.3 * P.V, 5.0 * P.V))

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )
