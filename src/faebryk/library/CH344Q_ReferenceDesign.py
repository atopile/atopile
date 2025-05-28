# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.smd import SMDSize
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
    led_rx = L.f_field(F.LEDIndicator)(use_mosfet=False, active_low=True)
    led_tx = L.f_field(F.LEDIndicator)(use_mosfet=False, active_low=True)
    led_act = L.f_field(F.LEDIndicator)(use_mosfet=False, active_low=True)
    power_led: F.PoweredLED
    reset_lowpass: F.FilterElectricalRC

    def __preinit__(self):
        # ------------------------------------
        #             aliases
        # ------------------------------------
        pwr_3v3 = self.usb_uart_converter.power
        # ------------------------------------
        #           connections
        # ------------------------------------
        self.usb_uart_converter.power.decoupled.decouple(owner=self).specialize(
            F.MultiCapacitor(4)
        ).set_equal_capacitance_each(L.Range.from_center_rel(100 * P.nF, 0.05))
        self.usb.usb_if.buspower.connect_via(self.ldo, pwr_3v3)

        self.usb.usb_if.d.connect(self.usb_uart_converter.usb)

        self.usb_uart_converter.act.connect(self.led_act.logic_in)
        self.usb_uart_converter.indicator_rx.connect(self.led_rx.logic_in)
        self.usb_uart_converter.indicator_tx.connect(self.led_tx.logic_in)
        pwr_3v3.connect(self.power_led.power)

        self.usb_uart_converter.osc[1].connect(self.oscillator.xtal_if.xin)
        self.usb_uart_converter.osc[0].connect(self.oscillator.xtal_if.xout)
        self.oscillator.xtal_if.gnd.connect(pwr_3v3.lv)

        self.reset_lowpass.out.line.connect(self.usb_uart_converter.reset.line)
        self.reset_lowpass.in_.line.connect(self.usb_uart_converter.reset.reference.hv)
        self.reset_lowpass.in_.reference.connect(
            self.usb_uart_converter.reset.reference
        )
        # TODO: already done by lowpass filter
        # self.usb_uart_converter.reset.pulled.pull(up=True)

        self.usb_uart_converter.test.set_weak(
            on=False, owner=self
        ).resistance.constrain_subset(L.Range.from_center_rel(4.7 * P.kohm, 0.05))

        self.ldo.enable_output()

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.usb_uart_converter.enable_status_or_modem_signals(self)

        self.oscillator.crystal.frequency.constrain_subset(
            L.Range.from_center_rel(8 * P.MHz, 0.001)
        )
        self.oscillator.crystal.frequency_tolerance.constrain_le(40 * P.ppm)
        self.oscillator.crystal.load_capacitance.constrain_subset(
            L.Range.from_center(8 * P.pF, 10 * P.pF)
        )  # TODO: should be property of crystal when picked
        self.oscillator.current_limiting_resistor.resistance.constrain_subset(0 * P.ohm)

        self.ldo.power_in.decoupled.decouple(owner=self).capacitance.constrain_subset(
            L.Range.from_center_rel(100 * P.nF, 0.1)
        )
        self.ldo.power_out.decoupled.decouple(owner=self).capacitance.constrain_subset(
            L.Range.from_center_rel(100 * P.nF, 0.1)
        )

        # self.usb.usb_if.buspower.max_current.constrain_subset(
        #    L.Range.from_center_rel(500 * P.mA, 0.1)
        # )

        self.ldo.output_current.constrain_ge(500 * P.mA)
        self.ldo.output_voltage.constrain_subset(
            L.Range.from_center_rel(3.3 * P.V, 0.05)
        )

        # reset lowpass
        # #TODO: fix
        # self.reset_lowpass.cutoff_frequency.constrain_subset(
        #    L.Range.from_center_rel(100 * P.Hz, 0.1)
        # )
        self.reset_lowpass.capacitor.capacitance.constrain_subset(
            L.Range.from_center_rel(100 * P.nF, 0.2)
        )
        self.reset_lowpass.resistor.resistance.constrain_subset(
            L.Range.from_center_rel(4.7 * P.kohm, 0.05)
        )

        for res in self.get_children(direct_only=True, types=F.Resistor):
            res.add(F.has_package_requirements(size=SMDSize.I0402))
        for cap in self.get_children(direct_only=True, types=F.Capacitor):
            cap.add(F.has_package_requirements(size=SMDSize.I0402))
