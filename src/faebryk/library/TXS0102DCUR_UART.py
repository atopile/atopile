# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module


class TXS0102DCUR_UART(Module):
    """
    TXS0102DCUR 2 bit level shifter with UART interfaces
    - Output enabled by default
    """

    voltage_a_power: F.ElectricPower
    voltage_b_power: F.ElectricPower
    voltage_a_bus: F.UART_Base
    voltage_b_bus: F.UART_Base

    buffer: F.TXS0102DCUR

    def __preinit__(self):
        self.voltage_a_power.connect(self.buffer.voltage_a_power)
        self.voltage_b_power.connect(self.buffer.voltage_b_power)

        # enable output by default
        self.buffer.n_oe.set(True)

        # connect UART interfaces to level shifter
        self.voltage_a_bus.rx.connect(self.buffer.shifters[0].io_a)
        self.voltage_a_bus.tx.connect(self.buffer.shifters[1].io_a)
        self.voltage_b_bus.rx.connect(self.buffer.shifters[0].io_b)
        self.voltage_b_bus.tx.connect(self.buffer.shifters[1].io_b)

        # TODO
        # self.add(
        #    can_bridge_defined(self.voltage_a_bus, self.voltage_b_bus)
        # )
