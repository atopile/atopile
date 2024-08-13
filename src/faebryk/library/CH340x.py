# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.Range import Range
from faebryk.library.UART import UART
from faebryk.library.USB2_0 import USB2_0

logger = logging.getLogger(__name__)


class CH340x(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            usb = USB2_0()
            uart = UART()
            tnow = Electrical()
            gpio_power = ElectricPower()

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        self.IFs.gpio_power.IFs.lv.connect(self.IFs.usb.IFs.usb_if.IFs.buspower.IFs.lv)

        self.IFs.gpio_power.PARAMs.voltage.merge(Range(0, 5.3))
        self.IFs.gpio_power.get_trait(can_be_decoupled).decouple()
        self.IFs.usb.IFs.usb_if.IFs.buspower.PARAMs.voltage.merge(Range(4.0, 5.3))

        self.add_trait(has_designator_prefix_defined("U"))
        self.add_trait(
            has_datasheet_defined("https://wch-ic.com/downloads/file/79.html")
        )

        self.IFs.usb.IFs.usb_if.IFs.buspower.get_trait(can_be_decoupled).decouple()

        self.IFs.gpio_power.IFs.lv.connect(self.IFs.usb.IFs.usb_if.IFs.buspower.IFs.lv)
