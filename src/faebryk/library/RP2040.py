# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.I2C import I2C
from faebryk.library.MultiSPI import MultiSPI
from faebryk.library.SWD import SWD
from faebryk.library.UART_Base import UART_Base
from faebryk.library.USB2_0 import USB2_0
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class RP2040(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            io_vdd = ElectricPower()
            adc_vdd = ElectricPower()
            core_vdd = ElectricPower()
            vreg_in = ElectricPower()
            vreg_out = ElectricPower()
            power_vusb = ElectricPower()
            gpio = times(30, Electrical)
            run = ElectricLogic()
            usb = USB2_0()
            qspi = MultiSPI(data_lane_count=4)
            xin = Electrical()
            xout = Electrical()
            test = Electrical()
            swd = SWD()
            # TODO: these peripherals and more can be mapped to different pins
            i2c = I2C()
            uart = UART_Base()

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        # decouple power rails and connect GNDs toghether
        gnd = self.IFs.io_vdd.IFs.lv
        for pwrrail in [
            self.IFs.io_vdd,
            self.IFs.adc_vdd,
            self.IFs.core_vdd,
            self.IFs.vreg_in,
            self.IFs.vreg_out,
            self.IFs.usb.IFs.usb_if.IFs.buspower,
        ]:
            pwrrail.IFs.lv.connect(gnd)
            pwrrail.get_trait(can_be_decoupled).decouple()

        self.add_trait(has_designator_prefix_defined("U"))

        self.add_trait(
            has_datasheet_defined(
                "https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf"
            )
        )

        # set parameters
        # self.IFs.io_vdd.PARAMs.voltage.merge(Range(1.8*P.V, 3.63*P.V))
