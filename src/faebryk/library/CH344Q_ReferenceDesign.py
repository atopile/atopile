# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class CH344Q_ReferenceDesign(Module):
    """
    Minimal implementation of the CH344Q quad UART to USB bridge
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    usb: F.USB2_0
    usb_uart_converter: F.CH344Q
    oscillator: F.Crystal_Oscillator
    ldo: F.LDO
    led_rx = L.f_field(F.LEDIndicator)(use_mosfet=False)
    led_tx = L.f_field(F.LEDIndicator)(use_mosfet=False)
    led_act = L.f_field(F.LEDIndicator)(use_mosfet=False)
    power_led: F.PoweredLED
    reset_lowpass: F.FilterElectricalRC

    @L.rt_field
    def vbus_fused(self):
        return self.usb.usb_if.buspower.fused()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------

    def __preinit__(self):
        # ------------------------------------
        #             aliases
        # ------------------------------------
        pwr_3v3 = self.usb_uart_converter.power
        # ------------------------------------
        #           connections
        # ------------------------------------
        self.usb_uart_converter.power.decoupled.decouple().capacitance.merge(
            F.Range.from_center_rel(1 * P.uF, 0.05)
        )  # TODO: per pin
        self.vbus_fused.connect_via(self.ldo, pwr_3v3)

        self.usb.usb_if.d.connect(self.usb_uart_converter.usb)

        self.usb_uart_converter.act.connect(self.led_act.logic_in)
        self.usb_uart_converter.indicator_rx.connect(self.led_rx.logic_in)
        self.usb_uart_converter.indicator_tx.connect(self.led_tx.logic_in)
        pwr_3v3.connect(
            self.power_led.power,
            self.led_rx.power_in,
            self.led_tx.power_in,
            self.led_act.power_in,
        )

        self.usb_uart_converter.osc[1].connect(self.oscillator.xtal_if.xin)
        self.usb_uart_converter.osc[0].connect(self.oscillator.xtal_if.xout)
        self.oscillator.gnd.connect(pwr_3v3.lv)

        self.reset_lowpass.out.connect(self.usb_uart_converter.reset)
        self.usb_uart_converter.reset.pulled.pull(up=True)

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.usb_uart_converter.enable_status_or_modem_signals()

        self.oscillator.crystal.frequency.merge(
            F.Range.from_center_rel(8 * P.MHz, 0.001)
        )
        self.oscillator.crystal.frequency_tolerance.merge(
            F.Range.upper_bound(40 * P.ppm)
        )
        self.oscillator.crystal.load_capacitance.merge(
            F.Range.from_center(8 * P.pF, 10 * P.pF)
        )  # TODO: should be property of crystal when picked

        self.usb.usb_if.buspower.max_current.merge(
            F.Range.from_center_rel(500 * P.mA, 0.1)
        )

        self.ldo.output_current.merge(F.Range.lower_bound(500 * P.mA))
        self.ldo.output_voltage.merge(F.Range.from_center_rel(3.3 * P.V, 0.05))

        # reset lowpass
        self.reset_lowpass.response.merge(F.Filter.Response.LOWPASS)
        self.reset_lowpass.cutoff_frequency.merge(
            F.Range.from_center_rel(100 * P.Hz, 0.1)
        )
