# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class USB_RS485(Module):
    usb_uart: F.CH340x
    uart_rs485: F.UART_RS485
    termination: F.Resistor
    polarization = L.list_field(2, F.Resistor)
    usb: F.USB2_0
    rs485: F.RS485HalfDuplex

    def __preinit__(self):
        self.usb.connect(self.usb_uart.usb)
        self.usb_uart.uart.base_uart.connect(self.uart_rs485.uart)
        self.rs485.connect(self.uart_rs485.rs485)

        self.usb_uart.tnow.connect(self.uart_rs485.read_enable)
        self.usb_uart.tnow.connect(self.uart_rs485.write_enable)

        self.usb_uart.usb.usb_if.buspower.connect(self.uart_rs485.power)
        self.usb.usb_if.buspower.connect(self.usb_uart.usb.usb_if.buspower)

        # connect termination resistor between RS485 A and B
        self.uart_rs485.rs485.diff_pair.n.line.connect_via(
            self.termination, self.uart_rs485.rs485.diff_pair.p.line
        )

        # connect polarization resistors to RS485 A and B
        self.uart_rs485.rs485.diff_pair.p.line.connect_via(
            self.polarization[0],
            self.uart_rs485.power.hv,
        )
        self.uart_rs485.rs485.diff_pair.n.line.connect_via(
            self.polarization[1],
            self.uart_rs485.power.lv,
        )

        self.termination.resistance.constrain_subset(
            L.Range.from_center(150 * P.ohm, 1.5 * P.ohm)
        )
        self.polarization[0].resistance.constrain_subset(
            L.Range.from_center(680 * P.ohm, 6.8 * P.ohm)
        )
        self.polarization[1].resistance.constrain_subset(
            L.Range.from_center(680 * P.ohm, 6.8 * P.ohm)
        )
