# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class ESP32_C3_MINI_1_Reference_Design(Module):
    """ESP32_C3_MINI_1 Module reference design"""

    esp32_c3_mini_1: F.ESP32_C3_MINI_1
    # TODO make switch debounced
    boot_switch: F.Button  # TODO: this cannot be picked Switch(F.Electrical)
    reset_switch: F.Button  # TODO: this cannot be picked Switch(F.Electrical)
    low_speed_crystal_clock: F.Crystal_Oscillator

    vdd3v3: F.ElectricPower
    uart: F.UART_Base
    jtag: F.JTAG
    usb: F.USB2_0

    def __preinit__(self):
        gnd = self.vdd3v3.lv

        # connect power
        self.vdd3v3.connect(self.esp32_c3_mini_1.vdd3v3)

        # TODO: set default boot mode (GPIO[8] pull up with 10k resistor) + (GPIO[2] pull up with 10k resistor)  # noqa: E501
        self.esp32_c3_mini_1.esp32_c3
        # boot and enable switches
        # TODO: Fix bridging of (boot and reset) switches
        self.esp32_c3_mini_1.chip_enable.signal.connect_via(self.boot_switch, gnd)
        # TODO: lowpass chip_enable
        self.esp32_c3_mini_1.gpio[9].signal.connect_via(self.reset_switch, gnd)

        # connect low speed crystal oscillator
        self.low_speed_crystal_clock.n.connect(self.esp32_c3_mini_1.gpio[0].signal)
        self.low_speed_crystal_clock.p.connect(self.esp32_c3_mini_1.gpio[1].signal)
        self.low_speed_crystal_clock.power.connect(self.vdd3v3)

        # TODO: set the following in the pinmux
        # jtag gpio 4,5,6,7
        # USB gpio 18,19

        # connect USB
        self.usb.connect(self.esp32_c3_mini_1.esp32_c3.usb)

        # connect UART[0]
        self.uart.connect(self.esp32_c3_mini_1.esp32_c3.uart[0])

        # default to SPI flash boot mode
        self.esp32_c3_mini_1.esp32_c3.set_default_boot_mode()

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.low_speed_crystal_clock.crystal.frequency.merge(32.768 * P.kHz)
        self.low_speed_crystal_clock.crystal.frequency_tolerance.merge(
            F.Range.lower_bound(20 * P.ppm)
        )
