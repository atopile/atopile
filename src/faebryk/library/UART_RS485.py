# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.Range import Range
from faebryk.library.RS485 import RS485
from faebryk.library.TBD import TBD
from faebryk.library.UART_Base import UART_Base

logger = logging.getLogger(__name__)


class UART_RS485(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            power = ElectricPower()
            uart = UART_Base()
            rs485 = RS485()
            read_enable = Electrical()
            write_enable = Electrical()

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()):
            max_data_rate = TBD[int]()
            gpio_voltage = TBD[float]()

        self.PARAMs = _PARAMs(self)

        self.IFs.power.PARAMs.voltage.merge(Range(3.3, 5.0))

        self.IFs.power.get_trait(can_be_decoupled).decouple()

        self.add_trait(has_designator_prefix_defined("U"))
