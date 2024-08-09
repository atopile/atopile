# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.TXS0102DCUR import TXS0102DCUR
from faebryk.library.UART_Base import UART_Base


class TXS0102DCUR_UART(Module):
    """
    TXS0102DCUR 2 bit level shifter with UART interfaces
    - Output enabled by default
    """

    def __init__(self) -> None:
        super().__init__()

        class _IFs(Module.IFS()):
            voltage_a_power = ElectricPower()
            voltage_b_power = ElectricPower()
            voltage_a_bus = UART_Base()
            voltage_b_bus = UART_Base()

        self.IFs = _IFs(self)

        class _NODEs(Module.NODES()):
            buffer = TXS0102DCUR()

        self.NODEs = _NODEs(self)

        self.IFs.voltage_a_power.connect(self.NODEs.buffer.IFs.voltage_a_power)
        self.IFs.voltage_b_power.connect(self.NODEs.buffer.IFs.voltage_b_power)

        # enable output by default
        self.NODEs.buffer.IFs.n_oe.set(True)

        # connect UART interfaces to level shifter
        self.IFs.voltage_a_bus.IFs.rx.connect(
            self.NODEs.buffer.NODEs.shifters[0].IFs.io_a
        )
        self.IFs.voltage_a_bus.IFs.tx.connect(
            self.NODEs.buffer.NODEs.shifters[1].IFs.io_a
        )
        self.IFs.voltage_b_bus.IFs.rx.connect(
            self.NODEs.buffer.NODEs.shifters[0].IFs.io_b
        )
        self.IFs.voltage_b_bus.IFs.tx.connect(
            self.NODEs.buffer.NODEs.shifters[1].IFs.io_b
        )

        # TODO
        # self.add_trait(
        #    can_bridge_defined(self.IFs.voltage_a_bus, self.IFs.voltage_b_bus)
        # )
