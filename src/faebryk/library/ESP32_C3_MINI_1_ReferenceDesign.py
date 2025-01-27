# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class ESP32_C3_MINI_1_ReferenceDesign(Module):
    """ESP32_C3_MINI_1 Module reference design"""

    class DebouncedButton(Module):
        button: F.Button
        lp_filter: F.FilterElectricalRC

        logic_out: F.ElectricLogic

        def __preinit__(self):
            self.lp_filter.in_.line.connect_via(
                self.button, self.logic_out.reference.lv
            )
            self.lp_filter.cutoff_frequency.constrain_subset(
                L.Range(100 * P.Hz, 200 * P.Hz)
            )
            self.lp_filter.response.constrain_subset(F.Filter.Response.LOWPASS)

    esp32_c3_mini_1: F.ESP32_C3_MINI_1
    boot_switch: DebouncedButton
    reset_switch: DebouncedButton
    low_speed_crystal_clock: F.Crystal_Oscillator

    vdd3v3: F.ElectricPower
    uart: F.UART_Base
    jtag: F.JTAG
    usb: F.USB2_0

    def __preinit__(self):
        esp32c3mini1 = self.esp32_c3_mini_1.ic
        esp32c3 = esp32c3mini1.esp32_c3

        # connect power
        self.vdd3v3.connect(esp32c3mini1.vdd3v3)

        esp32c3.set_default_boot_mode(self)
        # boot and enable switches
        esp32c3mini1.chip_enable.connect(self.boot_switch.logic_out)
        esp32c3mini1.gpio[9].connect(self.reset_switch.logic_out)

        # connect low speed crystal oscillator
        self.low_speed_crystal_clock.xtal_if.xin.connect(esp32c3mini1.gpio[0].line)
        self.low_speed_crystal_clock.xtal_if.xout.connect(esp32c3mini1.gpio[1].line)
        self.low_speed_crystal_clock.xtal_if.gnd.connect(self.vdd3v3.lv)

        # TODO: set the following in the pinmux
        # jtag gpio 4,5,6,7
        esp32c3.usb.usb_if.d.n.line.connect(esp32c3.gpio[18].line)
        esp32c3.usb.usb_if.d.p.line.connect(esp32c3.gpio[19].line)
        # UART0 gpio 30/31 (default)
        esp32c3.uart[0].rx.connect(esp32c3.gpio[20])
        esp32c3.uart[0].tx.connect(esp32c3.gpio[21])

        # UART1 gpio 8/9
        esp32c3.uart[1].rx.connect(esp32c3.gpio[8])
        esp32c3.uart[1].tx.connect(esp32c3.gpio[9])
        # i2c
        esp32c3.i2c.sda.connect(
            esp32c3.gpio[3]  # default 21
        )
        esp32c3.i2c.scl.connect(
            esp32c3.gpio[2]  # default 22
        )

        # connect USB
        self.usb.connect(esp32c3.usb)

        # connect UART[0]
        self.uart.connect(esp32c3.uart[0])

        # default to SPI flash boot mode
        esp32c3.set_default_boot_mode(self)

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.low_speed_crystal_clock.crystal.frequency.constrain_subset(
            L.Range.from_center_rel(32.768 * P.kHz, 0.001)
        )
        self.low_speed_crystal_clock.crystal.frequency_tolerance.constrain_subset(
            L.Range(0 * P.ppm, 20 * P.ppm)
        )
