# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class RP2040_Reference_Design(Module):
    """Minimal required design for the Raspberry Pi RP2040 microcontroller.
    Based on the official Raspberry Pi RP2040 hardware design guidlines"""

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------

    usb: F.USB2_0

    rp2040: F.RP2040
    flash: F.SPIFlash
    led: F.PoweredLED
    usb_current_limit_resistor = L.list_field(2, F.Resistor)
    reset_button: F.Button
    boot_button: F.Button
    boot_resistor: F.Resistor
    ldo: F.LDO
    crystal_oscillator: F.Crystal_Oscillator
    oscillator_resistor: F.Resistor

    # TODO: add voltage divider with switch
    # TODO: add optional LM4040 voltage reference or voltage divider

    def __preinit__(self):
        # TODO
        return
        # ----------------------------------------
        #                aliasess
        # ----------------------------------------
        power_3v3 = self.ldo.power_out
        power_5v = self.ldo.power_in
        power_vbus = self.usb.usb_if.buspower
        gnd = power_vbus.lv
        # ----------------------------------------
        #            parametrization
        # ----------------------------------------
        self.ldo.output_voltage.merge(3.3 * P.V)
        self.ldo.output_current.merge(600 * P.mA)
        self.crystal_oscillator.crystal.frequency.merge(12 * P.MHz)
        self.crystal_oscillator.crystal.load_impedance.merge(10 * P.pF)

        # for cap in self.crystal_oscillator.capacitors:
        #     cap.capacitance.merge(15 * P.pF) # TODO: remove?

        self.oscillator_resistor.resistance.merge(F.Constant(1 * P.kohm))

        self.flash.memory_size.merge(F.Constant(16 * P.Mbit))

        self.led.led.color.merge(F.LED.Color.GREEN)
        self.led.led.brightness.merge(
            TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value.value
        )
        # TODO: remove: #poweredled voltage merge issue
        self.led.power.voltage.merge(power_3v3.voltage)

        self.usb_current_limit_resistor[0].resistance.merge(F.Constant(27 * P.ohm))
        self.usb_current_limit_resistor[1].resistance.merge(F.Constant(27 * P.ohm))

        # ----------------------------------------
        #              connections
        # ----------------------------------------
        # connect power rails
        power_vbus.connect(power_5v)

        # connect rp2040 power rails
        for pwrrail in [
            self.rp2040.io_vdd,
            self.rp2040.adc_vdd,
            self.rp2040.vreg_in,
            self.rp2040.usb.usb_if.buspower,
        ]:
            pwrrail.connect(power_3v3)

        self.rp2040.vreg_out.connect(self.rp2040.core_vdd)

        # connect flash
        self.flash.spi.connect(self.rp2040.qspi)
        self.flash.power.connect(power_3v3)

        # connect led
        self.rp2040.gpio[25].connect_via(self.led, gnd)

        # crystal oscillator
        self.rp2040.xin.connect_via(
            [self.crystal_oscillator, self.oscillator_resistor],
            self.rp2040.xout,
        )
        gnd.connect(self.crystal_oscillator.power.lv)

        # buttons
        self.rp2040.qspi.cs.signal.connect_via(
            [self.boot_resistor, self.boot_button], gnd
        )
        self.boot_resistor.resistance.merge(F.Constant(1 * P.kohm))
        self.rp2040.run.signal.connect_via(self.reset_button, gnd)

        # connect usb
        self.usb.usb_if.d.p.connect_via(
            self.usb_current_limit_resistor[0],
            self.rp2040.usb.usb_if.d.p,
        )
        self.usb.usb_if.d.n.connect_via(
            self.usb_current_limit_resistor[1],
            self.rp2040.usb.usb_if.d.n,
        )

    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://datasheets.raspberrypi.com/rp2040/hardware-design-with-rp2040.pdf"
    )

    @L.rt_field
    def pcb_layout(self):
        from faebryk.exporters.pcb.layout.absolute import LayoutAbsolute
        from faebryk.exporters.pcb.layout.extrude import LayoutExtrude
        from faebryk.exporters.pcb.layout.typehierarchy import LayoutTypeHierarchy

        Point = F.has_pcb_position.Point
        L = F.has_pcb_position.layer_type

        return F.has_pcb_layout_defined(
            layout=LayoutTypeHierarchy(
                layouts=[
                    LayoutTypeHierarchy.Level(
                        mod_type=F.RP2040,
                        layout=LayoutAbsolute(
                            Point((0, 0, 0, L.NONE)),
                        ),
                    ),
                    LayoutTypeHierarchy.Level(
                        mod_type=F.LDO,
                        layout=LayoutAbsolute(Point((0, 14, 0, L.NONE))),
                    ),
                    LayoutTypeHierarchy.Level(
                        mod_type=F.Button,
                        layout=LayoutExtrude(
                            base=Point((-1.75, -11.5, 0, L.NONE)),
                            vector=(3.5, 0, 90),
                        ),
                    ),
                    LayoutTypeHierarchy.Level(
                        mod_type=F.SPIFlash,
                        layout=LayoutAbsolute(
                            Point((-1.95, -6.5, 0, L.NONE)),
                        ),
                    ),
                    LayoutTypeHierarchy.Level(
                        mod_type=F.PoweredLED,
                        layout=LayoutAbsolute(
                            Point((6.5, -1.5, 270, L.NONE)),
                        ),
                        children_layout=LayoutTypeHierarchy(
                            layouts=[
                                LayoutTypeHierarchy.Level(
                                    mod_type=F.LED,
                                    layout=LayoutAbsolute(
                                        Point((0, 0, 0, L.NONE)),
                                    ),
                                ),
                                LayoutTypeHierarchy.Level(
                                    mod_type=F.Resistor,
                                    layout=LayoutAbsolute(
                                        Point((-2.75, 0, 180, L.NONE))
                                    ),
                                ),
                            ]
                        ),
                    ),
                    LayoutTypeHierarchy.Level(
                        mod_type=F.Crystal_Oscillator,
                        layout=LayoutAbsolute(
                            Point((0, 7, 0, L.NONE)),
                        ),
                        children_layout=LayoutTypeHierarchy(
                            layouts=[
                                LayoutTypeHierarchy.Level(
                                    mod_type=F.Crystal,
                                    layout=LayoutAbsolute(
                                        Point((0, 0, 0, L.NONE)),
                                    ),
                                ),
                                LayoutTypeHierarchy.Level(
                                    mod_type=F.Capacitor,
                                    layout=LayoutExtrude(
                                        base=Point((-3, 0, 90, L.NONE)),
                                        vector=(0, 6, 180),
                                        dynamic_rotation=True,
                                    ),
                                ),
                            ]
                        ),
                    ),
                    LayoutTypeHierarchy.Level(
                        mod_type=F.Resistor,
                        layout=LayoutExtrude(
                            base=Point((0.75, -6, 0, L.NONE)),
                            vector=(1.25, 0, 270),
                        ),
                    ),
                ]
            )
        )
