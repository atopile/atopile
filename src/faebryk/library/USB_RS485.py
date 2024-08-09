# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.CH340x import CH340x
from faebryk.library.Range import Range
from faebryk.library.Resistor import Resistor
from faebryk.library.RS485 import RS485
from faebryk.library.UART_RS485 import UART_RS485
from faebryk.library.USB2_0 import USB2_0
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class USB_RS485(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()):
            usb_uart = CH340x()
            uart_rs485 = UART_RS485()
            termination = Resistor()
            polarization = times(2, Resistor)

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            usb = USB2_0()
            rs485 = RS485()

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        self.IFs.usb.connect(self.NODEs.usb_uart.IFs.usb)
        self.NODEs.usb_uart.IFs.uart.IFs.base_uart.connect(
            self.NODEs.uart_rs485.IFs.uart
        )
        self.IFs.rs485.connect(self.NODEs.uart_rs485.IFs.rs485)

        self.NODEs.usb_uart.IFs.tnow.connect(self.NODEs.uart_rs485.IFs.read_enable)
        self.NODEs.usb_uart.IFs.tnow.connect(self.NODEs.uart_rs485.IFs.write_enable)

        self.NODEs.usb_uart.IFs.usb.IFs.buspower.connect(
            self.NODEs.uart_rs485.IFs.power
        )
        self.IFs.usb.IFs.buspower.connect(self.NODEs.usb_uart.IFs.usb.IFs.buspower)

        # connect termination resistor between RS485 A and B
        self.NODEs.uart_rs485.IFs.rs485.IFs.diff_pair.IFs.n.connect_via(
            self.NODEs.termination, self.NODEs.uart_rs485.IFs.rs485.IFs.diff_pair.IFs.p
        )

        # connect polarization resistors to RS485 A and B
        self.NODEs.uart_rs485.IFs.rs485.IFs.diff_pair.IFs.p.connect_via(
            self.NODEs.polarization[0],
            self.NODEs.uart_rs485.IFs.power.IFs.hv,
        )
        self.NODEs.uart_rs485.IFs.rs485.IFs.diff_pair.IFs.n.connect_via(
            self.NODEs.polarization[1],
            self.NODEs.uart_rs485.IFs.power.IFs.lv,
        )

        self.NODEs.termination.PARAMs.resistance.merge(Range.from_center(150, 1.5))
        self.NODEs.polarization[0].PARAMs.resistance.merge(Range.from_center(680, 6.8))
        self.NODEs.polarization[1].PARAMs.resistance.merge(Range.from_center(680, 6.8))
