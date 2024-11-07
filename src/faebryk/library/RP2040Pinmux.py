# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import TYPE_CHECKING

import faebryk.library._F as F  # noqa: F401
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from faebryk.library.RP2040 import RP2040


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
                x.spi[0].miso.signal,
                x.uart[0].base_uart.tx.signal,
                x.i2c[0].sda.signal,
                x.pwm[0].A.signal,
                x.gpio[0].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.ovcur_det.signal,
            ],
            x.io[1]: [
                x.spi[0].cs.signal,
                x.uart[0].base_uart.rx.signal,
                x.i2c[0].scl.signal,
                x.pwm[0].B.signal,
                x.gpio[1].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.vbus_det.signal,
            ],
            x.io[2]: [
                x.spi[0].sclk.signal,
                x.uart[0].cts.signal,
                x.i2c[1].sda.signal,
                x.pwm[1].A.signal,
                x.gpio[2].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.vbus_en.signal,
            ],
            x.io[3]: [
                x.spi[0].mosi.signal,
                x.uart[0].rts.signal,
                x.i2c[1].scl.signal,
                x.pwm[1].B.signal,
                x.gpio[3].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.ovcur_det.signal,
            ],
            x.io[4]: [
                x.spi[0].miso.signal,
                x.uart[1].base_uart.tx.signal,
                x.i2c[0].sda.signal,
                x.pwm[2].A.signal,
                x.gpio[4].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.vbus_det.signal,
            ],
            x.io[5]: [
                x.spi[0].cs.signal,
                x.uart[1].base_uart.rx.signal,
                x.i2c[0].scl.signal,
                x.pwm[2].B.signal,
                x.gpio[5].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.vbus_en.signal,
            ],
            x.io[6]: [
                x.spi[0].sclk.signal,
                x.uart[1].cts.signal,
                x.i2c[1].sda.signal,
                x.pwm[3].A.signal,
                x.gpio[6].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.ovcur_det.signal,
            ],
            x.io[7]: [
                x.spi[0].mosi.signal,
                x.uart[1].rts.signal,
                x.i2c[1].scl.signal,
                x.pwm[3].B.signal,
                x.gpio[7].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.vbus_det.signal,
            ],
            x.io[8]: [
                x.spi[1].miso.signal,
                x.uart[0].base_uart.tx.signal,
                x.i2c[0].sda.signal,
                x.pwm[4].A.signal,
                x.gpio[8].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.vbus_en.signal,
            ],
            x.io[9]: [
                x.spi[1].cs.signal,
                x.uart[0].base_uart.rx.signal,
                x.i2c[0].scl.signal,
                x.pwm[4].B.signal,
                x.gpio[9].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.ovcur_det.signal,
            ],
            x.io[10]: [
                x.spi[1].sclk.signal,
                x.uart[0].cts.signal,
                x.i2c[1].sda.signal,
                x.pwm[5].A.signal,
                x.gpio[10].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.vbus_det.signal,
            ],
            x.io[11]: [
                x.spi[1].mosi.signal,
                x.uart[0].rts.signal,
                x.i2c[1].scl.signal,
                x.pwm[5].B.signal,
                x.gpio[11].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.vbus_en.signal,
            ],
            x.io[12]: [
                x.spi[1].miso.signal,
                x.uart[1].base_uart.tx.signal,
                x.i2c[0].sda.signal,
                x.pwm[6].A.signal,
                x.gpio[12].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.ovcur_det.signal,
            ],
            x.io[13]: [
                x.spi[1].cs.signal,
                x.uart[1].base_uart.rx.signal,
                x.i2c[0].scl.signal,
                x.pwm[6].B.signal,
                x.gpio[13].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.vbus_det.signal,
            ],
            x.io[14]: [
                x.spi[1].sclk.signal,
                x.uart[1].cts.signal,
                x.i2c[1].sda.signal,
                x.pwm[7].A.signal,
                x.gpio[14].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.vbus_en.signal,
            ],
            x.io[15]: [
                x.spi[1].mosi.signal,
                x.uart[1].rts.signal,
                x.i2c[1].scl.signal,
                x.pwm[7].B.signal,
                x.gpio[15].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.ovcur_det.signal,
            ],
            x.io[16]: [
                x.spi[0].miso.signal,
                x.uart[0].base_uart.tx.signal,
                x.i2c[0].sda.signal,
                x.pwm[0].A.signal,
                x.gpio[16].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.vbus_det.signal,
            ],
            x.io[17]: [
                x.spi[0].cs.signal,
                x.uart[0].base_uart.rx.signal,
                x.i2c[0].scl.signal,
                x.pwm[0].B.signal,
                x.gpio[17].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.vbus_en.signal,
            ],
            x.io[18]: [
                x.spi[0].sclk.signal,
                x.uart[0].cts.signal,
                x.i2c[1].sda.signal,
                x.pwm[1].A.signal,
                x.gpio[18].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.ovcur_det.signal,
            ],
            x.io[19]: [
                x.spi[0].mosi.signal,
                x.uart[0].rts.signal,
                x.i2c[1].scl.signal,
                x.pwm[1].B.signal,
                x.gpio[19].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.vbus_det.signal,
            ],
            x.io[20]: [
                x.spi[0].miso.signal,
                x.uart[1].base_uart.tx.signal,
                x.i2c[0].sda.signal,
                x.pwm[2].A.signal,
                x.gpio[20].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                x.clock_in[0].signal,
                x.usb_power_control.vbus_en.signal,
            ],
            x.io[21]: [
                x.spi[0].cs.signal,
                x.uart[1].base_uart.rx.signal,
                x.i2c[0].scl.signal,
                x.pwm[2].B.signal,
                x.gpio[21].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                x.clock_out[0].signal,
                x.usb_power_control.ovcur_det.signal,
            ],
            x.io[22]: [
                x.spi[0].sclk.signal,
                x.uart[1].cts.signal,
                x.i2c[1].sda.signal,
                x.pwm[3].A.signal,
                x.gpio[22].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                x.clock_in[1].signal,
                x.usb_power_control.vbus_det.signal,
            ],
            x.io[23]: [
                x.spi[0].mosi.signal,
                x.uart[1].rts.signal,
                x.i2c[1].scl.signal,
                x.pwm[3].B.signal,
                x.gpio[23].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                x.clock_out[1].signal,
                x.usb_power_control.vbus_en.signal,
            ],
            x.io[24]: [
                x.spi[1].miso.signal,
                x.uart[0].base_uart.tx.signal,
                x.i2c[0].sda.signal,
                x.pwm[4].A.signal,
                x.gpio[24].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                x.clock_out[2].signal,
                x.usb_power_control.ovcur_det.signal,
            ],
            x.io[25]: [
                x.spi[1].cs.signal,
                x.uart[0].base_uart.rx.signal,
                x.i2c[0].scl.signal,
                x.pwm[4].B.signal,
                x.gpio[25].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                x.clock_out[3].signal,
                x.usb_power_control.vbus_det.signal,
            ],
            x.io[26]: [
                x.spi[1].sclk.signal,
                x.uart[0].cts.signal,
                x.i2c[1].sda.signal,
                x.pwm[5].A.signal,
                x.gpio[26].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.vbus_en.signal,
            ],
            x.io[27]: [
                x.spi[1].mosi.signal,
                x.uart[0].rts.signal,
                x.i2c[1].scl.signal,
                x.pwm[5].B.signal,
                x.gpio[27].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.ovcur_det.signal,
            ],
            x.io[28]: [
                x.spi[1].miso.signal,
                x.uart[1].base_uart.tx.signal,
                x.i2c[0].sda.signal,
                x.pwm[6].A.signal,
                x.gpio[28].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.vbus_det.signal,
            ],
            x.io[29]: [
                x.spi[1].cs.signal,
                x.uart[1].base_uart.rx.signal,
                x.i2c[0].scl.signal,
                x.pwm[6].B.signal,
                x.gpio[29].signal,
                x.pio[0].signal,
                x.pio[1].signal,
                None,
                x.usb_power_control.vbus_en.signal,
            ],
        }
