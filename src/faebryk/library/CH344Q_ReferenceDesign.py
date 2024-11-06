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

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    @L.rt_field
    def pcb_layout(self):
        from faebryk.exporters.pcb.layout.absolute import LayoutAbsolute
        from faebryk.exporters.pcb.layout.extrude import LayoutExtrude
        from faebryk.exporters.pcb.layout.typehierarchy import LayoutTypeHierarchy

        Point = F.has_pcb_position.Point
        L = F.has_pcb_position.layer_type
        LVL = LayoutTypeHierarchy.Level

        return F.has_pcb_layout_defined(
            layout=LayoutTypeHierarchy(
                layouts=[
                    LVL(
                        mod_type=F.CH344Q,
                        layout=LayoutAbsolute(Point((0, 0, 0, L.NONE))),
                    ),
                    LVL(
                        mod_type=F.Crystal_Oscillator,
                        layout=LayoutAbsolute(Point((-1, 10.75, 180, L.NONE))),
                    ),
                    LVL(
                        mod_type=F.LDO,
                        layout=LayoutAbsolute(Point((7.5, -9.25, 270, L.NONE))),
                    ),
                    LVL(
                        mod_type=F.LEDIndicator,
                        layout=LayoutExtrude(
                            base=Point((8, 9.5, 0, L.NONE)),
                            vector=(-1.75, 0, 90),
                            reverse_order=True,
                        ),
                    ),
                    LVL(
                        mod_type=F.PoweredLED,
                        layout=LayoutAbsolute(Point((-6.5, 9.5, 270, L.NONE))),
                    ),
                    LVL(
                        mod_type=F.FilterElectricalRC,
                        layout=LayoutAbsolute(Point((0, -8, 0, L.NONE))),
                    ),
                ]
            )
        )

    def __preinit__(self):
        # ------------------------------------
        #             aliases
        # ------------------------------------
        pwr_3v3 = self.usb_uart_converter.power
        # ------------------------------------
        #           connections
        # ------------------------------------
        self.usb_uart_converter.power.decoupled.decouple().specialize(
            F.MultiCapacitor(4)
        ).set_equal_capacitance_each(F.Range.from_center_rel(100 * P.nF, 0.05))
        self.usb.usb_if.buspower.connect_via(self.ldo, pwr_3v3)

        self.usb.usb_if.d.connect(self.usb_uart_converter.usb)

        self.usb_uart_converter.act.connect(self.led_act.logic_in)
        self.usb_uart_converter.indicator_rx.connect(self.led_rx.logic_in)
        self.usb_uart_converter.indicator_tx.connect(self.led_tx.logic_in)
        pwr_3v3.connect(self.power_led.power)

        self.usb_uart_converter.osc[1].connect(self.oscillator.xtal_if.xin)
        self.usb_uart_converter.osc[0].connect(self.oscillator.xtal_if.xout)
        self.oscillator.xtal_if.gnd.connect(pwr_3v3.lv)

        self.reset_lowpass.out.connect(self.usb_uart_converter.reset)
        self.reset_lowpass.in_.signal.connect(
            self.usb_uart_converter.reset.reference.hv
        )
        self.reset_lowpass.in_.reference.connect(
            self.usb_uart_converter.reset.reference
        )
        # TODO: already done by lowpass filter
        # self.usb_uart_converter.reset.pulled.pull(up=True)

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
        self.oscillator.current_limiting_resistor.resistance.merge(
            F.Constant(0 * P.ohm)
        )

        self.ldo.power_in.decoupled.decouple().capacitance.merge(
            F.Range.from_center_rel(100 * P.nF, 0.1)
        )
        self.ldo.power_out.decoupled.decouple().capacitance.merge(
            F.Range.from_center_rel(100 * P.nF, 0.1)
        )

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

        # Specialize
        special = self.reset_lowpass.specialize(F.FilterElectricalRC())
        # Construct
        special.get_trait(F.has_construction_dependency).construct()
