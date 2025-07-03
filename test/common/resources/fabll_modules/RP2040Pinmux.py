# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import TYPE_CHECKING

import faebryk.library._F as F  # noqa: F401
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from test.common.resources.fabll_modules.RP2040 import RP2040


class RP2040Pinmux(F.Pinmux):
    """
    Raspberry PI RP2040 Pinmux
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    def __init__(self, mcu: "RP2040"):
        super().__init__()
        self._mcu = mcu

    def __preinit__(self):
        # ------------------------------------
        #          parametrization
        # ------------------------------------

        # ------------------------------------
        #           connections
        # ------------------------------------
        pass

    # RP2040 Pin Multiplexing Functions
    # +-------------+----------------------------------------------------------+
    # | Function    | Description                                              |
    # +-------------+----------------------------------------------------------+
    # | SPIx        | Connect internal PL022 SPI peripherals to GPIO           |
    # | UARTx       | Connect internal PL011 UART peripherals to GPIO          |
    # | I2Cx        | Connect internal DW I2C peripherals to GPIO              |
    # | PWMx A/B    | Connect PWM slices to GPIO (8 slices, 2 outputs each)    |
    # |             | B pin can be used as input for frequency/duty cycle      |
    # | SIO (F5)    | Software control of GPIO via single-cycle IO block       |
    # |             | Always connected for input, must be selected for output  |
    # | PIOx (F6,F7)| Connect programmable IO blocks to GPIO                   |
    # |             | Flexible interface placement, always connected for input |
    # | CLOCK GPINx | General purpose clock inputs                             |
    # |             | Can be routed to internal clock domains or counters      |
    # | CLOCK GPOUTx| General purpose clock outputs                            |
    # |             | Can output internal clocks to GPIOs with optional divide |
    # | USB Control | OVCUR DET, VBUS DET, VBUS EN                             |
    # |             | USB power control signals to/from internal controller    |
    # +-------------+----------------------------------------------------------+

    # TODO SIO (F5):

    def _get_ios(self) -> list[F.Electrical]:
        return self._mcu.io

    def _get_matrix(self) -> dict[F.Electrical, list[F.Electrical | None]]:
        x = self._mcu
        return {
            x.io[0]: [
                x.spi[0].miso.line,
                x.uart[0].base_uart.tx.line,
                x.i2c[0].sda.line,
                x.pwm[0].A.line,
                x.gpio[0].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.ovcur_det.line,
            ],
            x.io[1]: [
                x.spi[0].cs.line,
                x.uart[0].base_uart.rx.line,
                x.i2c[0].scl.line,
                x.pwm[0].B.line,
                x.gpio[1].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.vbus_det.line,
            ],
            x.io[2]: [
                x.spi[0].sclk.line,
                x.uart[0].cts.line,
                x.i2c[1].sda.line,
                x.pwm[1].A.line,
                x.gpio[2].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.vbus_en.line,
            ],
            x.io[3]: [
                x.spi[0].mosi.line,
                x.uart[0].rts.line,
                x.i2c[1].scl.line,
                x.pwm[1].B.line,
                x.gpio[3].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.ovcur_det.line,
            ],
            x.io[4]: [
                x.spi[0].miso.line,
                x.uart[1].base_uart.tx.line,
                x.i2c[0].sda.line,
                x.pwm[2].A.line,
                x.gpio[4].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.vbus_det.line,
            ],
            x.io[5]: [
                x.spi[0].cs.line,
                x.uart[1].base_uart.rx.line,
                x.i2c[0].scl.line,
                x.pwm[2].B.line,
                x.gpio[5].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.vbus_en.line,
            ],
            x.io[6]: [
                x.spi[0].sclk.line,
                x.uart[1].cts.line,
                x.i2c[1].sda.line,
                x.pwm[3].A.line,
                x.gpio[6].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.ovcur_det.line,
            ],
            x.io[7]: [
                x.spi[0].mosi.line,
                x.uart[1].rts.line,
                x.i2c[1].scl.line,
                x.pwm[3].B.line,
                x.gpio[7].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.vbus_det.line,
            ],
            x.io[8]: [
                x.spi[1].miso.line,
                x.uart[0].base_uart.tx.line,
                x.i2c[0].sda.line,
                x.pwm[4].A.line,
                x.gpio[8].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.vbus_en.line,
            ],
            x.io[9]: [
                x.spi[1].cs.line,
                x.uart[0].base_uart.rx.line,
                x.i2c[0].scl.line,
                x.pwm[4].B.line,
                x.gpio[9].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.ovcur_det.line,
            ],
            x.io[10]: [
                x.spi[1].sclk.line,
                x.uart[0].cts.line,
                x.i2c[1].sda.line,
                x.pwm[5].A.line,
                x.gpio[10].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.vbus_det.line,
            ],
            x.io[11]: [
                x.spi[1].mosi.line,
                x.uart[0].rts.line,
                x.i2c[1].scl.line,
                x.pwm[5].B.line,
                x.gpio[11].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.vbus_en.line,
            ],
            x.io[12]: [
                x.spi[1].miso.line,
                x.uart[1].base_uart.tx.line,
                x.i2c[0].sda.line,
                x.pwm[6].A.line,
                x.gpio[12].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.ovcur_det.line,
            ],
            x.io[13]: [
                x.spi[1].cs.line,
                x.uart[1].base_uart.rx.line,
                x.i2c[0].scl.line,
                x.pwm[6].B.line,
                x.gpio[13].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.vbus_det.line,
            ],
            x.io[14]: [
                x.spi[1].sclk.line,
                x.uart[1].cts.line,
                x.i2c[1].sda.line,
                x.pwm[7].A.line,
                x.gpio[14].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.vbus_en.line,
            ],
            x.io[15]: [
                x.spi[1].mosi.line,
                x.uart[1].rts.line,
                x.i2c[1].scl.line,
                x.pwm[7].B.line,
                x.gpio[15].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.ovcur_det.line,
            ],
            x.io[16]: [
                x.spi[0].miso.line,
                x.uart[0].base_uart.tx.line,
                x.i2c[0].sda.line,
                x.pwm[0].A.line,
                x.gpio[16].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.vbus_det.line,
            ],
            x.io[17]: [
                x.spi[0].cs.line,
                x.uart[0].base_uart.rx.line,
                x.i2c[0].scl.line,
                x.pwm[0].B.line,
                x.gpio[17].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.vbus_en.line,
            ],
            x.io[18]: [
                x.spi[0].sclk.line,
                x.uart[0].cts.line,
                x.i2c[1].sda.line,
                x.pwm[1].A.line,
                x.gpio[18].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.ovcur_det.line,
            ],
            x.io[19]: [
                x.spi[0].mosi.line,
                x.uart[0].rts.line,
                x.i2c[1].scl.line,
                x.pwm[1].B.line,
                x.gpio[19].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.vbus_det.line,
            ],
            x.io[20]: [
                x.spi[0].miso.line,
                x.uart[1].base_uart.tx.line,
                x.i2c[0].sda.line,
                x.pwm[2].A.line,
                x.gpio[20].line,
                x.pio[0].line,
                x.pio[1].line,
                x.clock_in[0].line,
                x.usb_power_control.vbus_en.line,
            ],
            x.io[21]: [
                x.spi[0].cs.line,
                x.uart[1].base_uart.rx.line,
                x.i2c[0].scl.line,
                x.pwm[2].B.line,
                x.gpio[21].line,
                x.pio[0].line,
                x.pio[1].line,
                x.clock_out[0].line,
                x.usb_power_control.ovcur_det.line,
            ],
            x.io[22]: [
                x.spi[0].sclk.line,
                x.uart[1].cts.line,
                x.i2c[1].sda.line,
                x.pwm[3].A.line,
                x.gpio[22].line,
                x.pio[0].line,
                x.pio[1].line,
                x.clock_in[1].line,
                x.usb_power_control.vbus_det.line,
            ],
            x.io[23]: [
                x.spi[0].mosi.line,
                x.uart[1].rts.line,
                x.i2c[1].scl.line,
                x.pwm[3].B.line,
                x.gpio[23].line,
                x.pio[0].line,
                x.pio[1].line,
                x.clock_out[1].line,
                x.usb_power_control.vbus_en.line,
            ],
            x.io[24]: [
                x.spi[1].miso.line,
                x.uart[0].base_uart.tx.line,
                x.i2c[0].sda.line,
                x.pwm[4].A.line,
                x.gpio[24].line,
                x.pio[0].line,
                x.pio[1].line,
                x.clock_out[2].line,
                x.usb_power_control.ovcur_det.line,
            ],
            x.io[25]: [
                x.spi[1].cs.line,
                x.uart[0].base_uart.rx.line,
                x.i2c[0].scl.line,
                x.pwm[4].B.line,
                x.gpio[25].line,
                x.pio[0].line,
                x.pio[1].line,
                x.clock_out[3].line,
                x.usb_power_control.vbus_det.line,
            ],
            x.io[26]: [
                x.spi[1].sclk.line,
                x.uart[0].cts.line,
                x.i2c[1].sda.line,
                x.pwm[5].A.line,
                x.gpio[26].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.vbus_en.line,
            ],
            x.io[27]: [
                x.spi[1].mosi.line,
                x.uart[0].rts.line,
                x.i2c[1].scl.line,
                x.pwm[5].B.line,
                x.gpio[27].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.ovcur_det.line,
            ],
            x.io[28]: [
                x.spi[1].miso.line,
                x.uart[1].base_uart.tx.line,
                x.i2c[0].sda.line,
                x.pwm[6].A.line,
                x.gpio[28].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.vbus_det.line,
            ],
            x.io[29]: [
                x.spi[1].cs.line,
                x.uart[1].base_uart.rx.line,
                x.i2c[0].scl.line,
                x.pwm[6].B.line,
                x.gpio[29].line,
                x.pio[0].line,
                x.pio[1].line,
                None,
                x.usb_power_control.vbus_en.line,
            ],
        }
