# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.Button import Button
from faebryk.library.Crystal_Oscillator import Crystal_Oscillator
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.ESP32_C3_MINI_1 import ESP32_C3_MINI_1
from faebryk.library.JTAG import JTAG
from faebryk.library.UART_Base import UART_Base
from faebryk.library.USB2_0 import USB2_0

logger = logging.getLogger(__name__)


class ESP32_C3_MINI_1_Reference_Design(Module):
    """ESP32_C3_MINI_1 Module reference design"""

    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()):
            esp32_c3_mini_1 = ESP32_C3_MINI_1()
            # TODO make switch debounced
            boot_switch = Button()  # TODO: this cannot be picked Switch(Electrical)
            reset_switch = Button()  # TODO: this cannot be picked Switch(Electrical)
            low_speed_crystal_clock = Crystal_Oscillator()

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            vdd3v3 = ElectricPower()
            uart = UART_Base()
            jtag = JTAG()
            usb = USB2_0()

        self.IFs = _IFs(self)

        gnd = self.IFs.vdd3v3.IFs.lv

        # connect power
        self.IFs.vdd3v3.connect(self.NODEs.esp32_c3_mini_1.IFs.vdd3v3)

        # TODO: set default boot mode (GPIO[8] pull up with 10k resistor) + (GPIO[2] pull up with 10k resistor)  # noqa: E501
        # boot and enable switches
        # TODO: Fix bridging of (boot and reset) switches
        # self.NODEs.esp32_c3_mini_1.IFs.chip_enable.connect_via(
        #    self.NODEs.boot_switch, gnd
        # )
        # TODO: lowpass chip_enable
        # self.IFs.gpio[9].connect_via(self.NODEs.reset_switch, gnd)

        # connect low speed crystal oscillator
        self.NODEs.low_speed_crystal_clock.IFs.n.connect(
            self.NODEs.esp32_c3_mini_1.IFs.gpio[0].IFs.signal
        )
        self.NODEs.low_speed_crystal_clock.IFs.p.connect(
            self.NODEs.esp32_c3_mini_1.IFs.gpio[1].IFs.signal
        )
        self.NODEs.low_speed_crystal_clock.IFs.power.IFs.lv.connect(gnd)

        # TODO: set the following in the pinmux
        # jtag gpio 4,5,6,7
        # USB gpio 18,19

        # connect USB
        self.IFs.usb.connect(self.NODEs.esp32_c3_mini_1.NODEs.esp32_c3.IFs.usb)

        # connect UART[0]
        self.IFs.uart.connect(self.NODEs.esp32_c3_mini_1.NODEs.esp32_c3.IFs.uart[0])
