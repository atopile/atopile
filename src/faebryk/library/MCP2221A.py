# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.I2C import I2C
from faebryk.library.UART_Base import UART_Base
from faebryk.library.USB2_0 import USB2_0
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class MCP2221A(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            power = ElectricPower()
            power_vusb = ElectricPower()
            uart = UART_Base()
            i2c = I2C()
            gpio = times(4, Electrical)
            reset = ElectricLogic()
            usb = USB2_0()

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        self.IFs.power.get_trait(can_be_decoupled).decouple()
        self.IFs.power_vusb.get_trait(can_be_decoupled).decouple()

        self.add_trait(has_designator_prefix_defined("U"))

        self.IFs.power.IFs.lv.connect(self.IFs.power_vusb.IFs.lv)
