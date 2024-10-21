# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.exporters.pcb.layout.absolute import LayoutAbsolute
from faebryk.exporters.pcb.layout.extrude import LayoutExtrude
from faebryk.exporters.pcb.layout.typehierarchy import LayoutTypeHierarchy
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class USB2514B_ReferenceDesign(Module):
    """
    Reference implementation of the USB2514B quad port USB hub controller.

    -
    """

    class PowerSwitchedUSB2_0(Module):
        """
        Power switched USB2_0 interface.
        """

        power_distribution_switch: F.Diodes_Incorporated_AP2552W6_7
        usb_dfp_power_indicator: F.PoweredLED

        power_in: F.ElectricPower
        power_out: F.ElectricPower
        usb_ufp_d: F.USB2_0_IF.Data
        usb_dfp_d: F.USB2_0_IF.Data

        @L.rt_field
        def can_bridge(self):
            return F.can_bridge_defined(self.usb_ufp_d, self.usb_dfp_d)

        def __preinit__(self):
            # ----------------------------------------
            #              parametrization
            # ----------------------------------------
            self.usb_dfp_power_indicator.led.color.merge(F.LED.Color.YELLOW)
            self.usb_dfp_power_indicator.led.brightness.merge(
                TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value.value
            )
            self.power_distribution_switch.set_current_limit(
                F.Range.from_center_rel(520 * P.mA, 0.01)
            )

            # ----------------------------------------
            #              connections
            # ----------------------------------------
            self.power_in.connect_via(self.power_distribution_switch, self.power_out)
            self.power_out.connect(self.usb_dfp_power_indicator.power)
            self.usb_ufp_d.connect(self.usb_dfp_d)

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    hub_controller: F.USB2514B
    vbus_voltage_divider: F.ResistorVoltageDivider
    ldo_3v3: F.LDO
    suspend_indicator = L.f_field(F.LEDIndicator)(use_mosfet=False)
    power_3v3_indicator: F.PoweredLED
    switched_usb_dfp = L.list_field(4, PowerSwitchedUSB2_0)
    bias_resistor: F.Resistor
    crystal_oscillator: F.Crystal_Oscillator

    usb_ufp: F.USB2_0
    usb_dfp = L.list_field(4, F.USB2_0)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/ProductDocuments/BoardDesignFiles/EVB-USB2514BC_A3-sch.pdf"  # noqa: E501
    )

    @L.rt_field
    def has_defined_layout(self):
        Point = F.has_pcb_position.Point
        L = F.has_pcb_position.layer_type
        LVL = LayoutTypeHierarchy.Level

        layouts = [
            LVL(  # USB2514B
                mod_type=self.PowerSwitchedUSB2_0,
                layout=LayoutExtrude(base=Point((11, -9, 0, L.NONE)), vector=(0, 6, 0)),
                children_layout=LayoutTypeHierarchy(
                    layouts=[
                        LVL(  # Diodes Incorporated AP2552W6_7
                            mod_type=F.Diodes_Incorporated_AP2552W6_7,
                            layout=LayoutAbsolute(Point((0, 0, 0, L.NONE))),
                        ),
                        LVL(  # PoweredLED
                            mod_type=F.PoweredLED,
                            layout=LayoutAbsolute(Point((0, -2.75, 180, L.NONE))),
                        ),
                    ]
                ),
            ),
            LVL(  # PoweredLED
                mod_type=type(self.power_3v3_indicator),
                layout=LayoutAbsolute(Point((5.5, 6, 180, L.NONE))),
            ),
            LVL(  # ResistorVoltageDivider
                mod_type=type(self.vbus_voltage_divider),
                layout=LayoutAbsolute(Point((-10, 0, 0, L.NONE))),
            ),
            LVL(  # Resistor
                mod_type=type(self.bias_resistor),
                layout=LayoutAbsolute(Point((-4.5, 3, 270, L.NONE))),
            ),
            LVL(  # LDO
                mod_type=F.LDO,
                layout=LayoutAbsolute(Point((1.5, 7, 270, L.NONE))),
            ),
            LVL(  # Crystal Oscillator
                mod_type=F.Crystal_Oscillator,
                layout=LayoutAbsolute(Point((-7.5, 0, 270, L.NONE))),
                children_layout=LayoutTypeHierarchy(
                    layouts=[
                        LVL(
                            mod_type=F.Crystal,
                            layout=LayoutAbsolute(
                                Point((0, 0, 0, L.NONE)),
                            ),
                        ),
                        LVL(
                            mod_type=F.Capacitor,
                            layout=LayoutExtrude(
                                base=Point((2.5, 0, 270, L.NONE)),
                                vector=(0, 5, 180),
                                dynamic_rotation=True,
                                reverse_order=True,
                            ),
                        ),
                    ],
                ),
            ),
            LVL(  # USB2514B
                mod_type=F.USB2514B, layout=LayoutAbsolute(Point((0, 0, 0, L.NONE)))
            ),
        ]

        return F.has_pcb_layout_defined(LayoutTypeHierarchy(layouts))

    def __preinit__(self):
        # ----------------------------------------
        #                aliasess
        # ----------------------------------------
        vbus = self.usb_ufp.usb_if.buspower
        gnd = vbus.lv
        power_3v3 = self.ldo_3v3.power_out

        # ----------------------------------------
        #            parametrization
        # ----------------------------------------
        self.hub_controller.set_non_removable_ports(
            F.USB2514B.NonRemovablePortConfiguration.ALL_PORTS_REMOVABLE
        )
        self.hub_controller.set_configuration_source(
            F.USB2514B.ConfigurationSource.DEFAULT
        )
        for dsf_usb in self.hub_controller.configurable_downstream_usb:
            dsf_usb.configure_usb_port(
                enable_usb=True,
                enable_battery_charging=True,
            )

        # TODO: load_capacitance is a property of the crystal. remove this
        self.crystal_oscillator.crystal.load_capacitance.merge(
            F.Range(8 * P.pF, 15 * P.pF)
        )
        self.crystal_oscillator.crystal.frequency.merge(
            F.Range.from_center_rel(24 * P.MHz, 0.01)
        )
        self.crystal_oscillator.crystal.frequency_tolerance.merge(
            F.Range.upper_bound(50 * P.ppm)
        )

        # TODO: ugly
        self.crystal_oscillator.current_limiting_resistor.resistance.merge(0 * P.ohm)

        # usb transceiver bias resistor
        self.bias_resistor.resistance.merge(F.Range.from_center_rel(12 * P.kohm, 0.01))

        for led in [self.suspend_indicator.led, self.power_3v3_indicator]:
            led.led.color.merge(F.LED.Color.GREEN)
            led.led.brightness.merge(
                TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value.value
            )

        self.ldo_3v3.output_voltage.merge(F.Range.from_center_rel(3.3 * P.V, 0.05))
        self.ldo_3v3.power_in.decoupled.decouple().capacitance.merge(
            F.Range.from_center_rel(100 * P.nF, 0.1)
        )
        self.ldo_3v3.power_out.decoupled.decouple().capacitance.merge(
            F.Range.from_center_rel(100 * P.nF, 0.1)
        )

        # ----------------------------------------
        #              connections
        # ----------------------------------------
        # power
        vbus.connect(self.ldo_3v3.power_in)
        power_3v3.connect(
            self.hub_controller.power_3v3,
            self.hub_controller.power_3v3_analog,
        )
        self.ldo_3v3.enable_output()

        # crystal oscillator
        self.crystal_oscillator.xtal_if.connect(self.hub_controller.xtal_if)
        self.crystal_oscillator.gnd.connect(gnd)

        for i, dfp in enumerate(self.usb_dfp):
            # USB data
            self.hub_controller.configurable_downstream_usb[i].usb.connect_via(
                self.switched_usb_dfp[i], dfp.usb_if.d
            )
            # power
            vbus.connect(self.switched_usb_dfp[i].power_in)
            dfp.usb_if.buspower.connect(self.switched_usb_dfp[i].power_out)
            # hub controller overcurrent and power control signals
            self.switched_usb_dfp[i].power_distribution_switch.enable.connect(
                self.hub_controller.configurable_downstream_usb[i].usb_power_enable
            )
            self.switched_usb_dfp[i].power_distribution_switch.fault.connect(
                self.hub_controller.configurable_downstream_usb[i].over_current_sense
            )

        # Bias resistor
        self.hub_controller.usb_bias_resistor_input.signal.connect_via(
            self.bias_resistor, gnd
        )  # TODO: replace with pull?

        self.usb_ufp.usb_if.d.connect(self.hub_controller.usb_upstream)

        # LEDs
        self.power_3v3_indicator.power.connect(power_3v3)
        self.hub_controller.suspense_indicator.connect(self.suspend_indicator.logic_in)
