# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class RaspberryPiPicoBase_ReferenceDesign(Module):
    """
    A reference design based on the Raspberry Pi pico microcontroller dev board.
    """

    class BootSelector(Module):
        logic_out: F.ElectricLogic

        resistor: F.Resistor
        switch = L.f_field(F.Switch(F.Electrical))()

        def __preinit__(self):
            self.resistor.resistance.merge(F.Range.from_center_rel(1 * P.kohm, 0.05))
            self.logic_out.set_weak(True).resistance.merge(self.resistor.resistance)
            self.logic_out.signal.connect_via(
                [self.resistor, self.switch], self.logic_out.reference.lv
            )

        @L.rt_field
        def single_reference(self):
            return F.has_single_electric_reference_defined(self.logic_out.reference)

    class PICO_DebugHeader(Module):
        swd: F.SWD

        lcsc_id = L.f_field(F.has_descriptive_properties_defined)({"LCSC": "C160389"})
        designator_prefix = L.f_field(F.has_designator_prefix_defined)(
            F.has_designator_prefix.Prefix.J
        )

        @L.rt_field
        def can_attach_to_footprint(self):
            return F.can_attach_to_footprint_via_pinmap(
                pinmap={
                    "1": self.swd.dio.signal,
                    "2": self.swd.dio.reference.lv,
                    "3": self.swd.clk.signal,
                }
            )

        datasheet = L.f_field(F.has_datasheet_defined)(
            "https://datasheets.raspberrypi.com/debug/debug-connector-specification.pdf"
        )

        def __preinit__(self):
            pass

    class PICO_ADC_VoltageReference(Module):
        rc_filter: F.FilterElectricalRC
        power_in: F.ElectricPower
        reference_out: F.ElectricPower

        @L.rt_field
        def can_bridge(self):
            return F.can_bridge_defined(self.power_in, self.reference_out)

        # @L.rt_field
        # def single_reference(self):
        #    return F.ElectricLogic.connect_all_module_references(self, gnd_only=True)

        def __preinit__(self):
            self.rc_filter.response.merge(F.Filter.Response.LOWPASS)
            self.rc_filter.cutoff_frequency.merge(
                F.Range.from_center_rel(360 * P.Hz, 0.1)
            )
            # self.reference_out.voltage.merge(F.Range(2 * P.V, 3 * P.V))

            self.power_in.connect(self.rc_filter.in_.reference)
            self.power_in.hv.connect(self.rc_filter.in_.signal)
            self.reference_out.hv.connect(self.rc_filter.out.signal)
            self.reference_out.lv.connect(self.rc_filter.out.reference.lv)

            # Specialize
            special = self.rc_filter.specialize(F.FilterElectricalRC())
            # Construct
            special.get_trait(F.has_construction_dependency).construct()

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------

    # function
    rp2040: F.RP2040
    ldo: F.LDO
    clock_source: F.Crystal_Oscillator
    flash: F.Winbond_W25Q16JVUXIQ

    # IO
    usb: F.USB2_0
    status_led = L.f_field(F.LEDIndicator)(use_mosfet=False)

    # debug header
    debug_header: PICO_DebugHeader

    # UI
    boot_selector: BootSelector
    reset_button = L.f_field(F.Switch(F.Electrical))()

    # ADC voltage reference
    adc_voltage_reference: PICO_ADC_VoltageReference

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://datasheets.raspberrypi.com/pico/pico-datasheet.pdf"
    )

    def __preinit__(self):
        # ----------------------------------------
        #                aliasess
        # ----------------------------------------
        power_3v3 = self.ldo.power_out
        power_vbus = self.usb.usb_if.buspower

        # ----------------------------------------
        #            parametrization
        # ----------------------------------------
        # LDO
        self.ldo.output_current.merge(F.Range.from_center_rel(600 * P.mA, 0.05))
        self.ldo.power_in.decoupled.decouple().capacitance.merge(
            F.Range.from_center_rel(10 * P.uF, 0.05)
        )
        self.ldo.power_out.decoupled.decouple().capacitance.merge(
            F.Range.from_center_rel(10 * P.uF, 0.05)
        )

        # XTAL
        self.clock_source.crystal.load_capacitance.merge(
            F.Range.from_center_rel(10 * P.pF, 0.05)
        )

        self.clock_source.current_limiting_resistor.resistance.merge(
            F.Range.from_center_rel(1 * P.kohm, 0.05)
        )
        self.clock_source.crystal.add(
            F.has_descriptive_properties_defined(
                {
                    DescriptiveProperties.manufacturer.value: "Abracon LLC",
                    DescriptiveProperties.partno: "ABM8-272-T3",
                }
            )
        )

        # Status LED
        self.status_led.led.led.color.merge(F.LED.Color.GREEN)
        self.status_led.led.led.brightness.merge(
            TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value.value
        )

        # USB
        terminated_usb = self.rp2040.usb.terminated()
        self.add(terminated_usb)
        terminated_usb.impedance.merge(F.Range.from_center_rel(27.4 * P.ohm, 0.05))

        # Flash
        self.flash.decoupled.decouple().capacitance.merge(
            F.Range.from_center_rel(100 * P.nF, 0.05)
        )

        # Power rails
        self.rp2040.power_io.decoupled.decouple().specialize(
            F.MultiCapacitor(6)
        ).set_equal_capacitance_each(F.Range.from_center_rel(100 * P.nF, 0.05))
        self.rp2040.core_regulator.power_in.decoupled.decouple().capacitance.merge(
            F.Range.from_center_rel(1 * P.uF, 0.05)
        )
        self.rp2040.power_adc.decoupled.decouple().capacitance.merge(
            F.Range.from_center_rel(100 * P.nF, 0.05)
        )
        self.rp2040.power_usb_phy.decoupled.decouple().capacitance.merge(
            F.Range.from_center_rel(100 * P.nF, 0.05)
        )
        power_3v3.get_trait(F.is_decoupled).get_capacitor().capacitance.merge(
            F.Range.from_center_rel(10 * P.uF, 0.05)
        )
        self.rp2040.power_core.decoupled.decouple().specialize(
            F.MultiCapacitor(2)
        ).set_equal_capacitance_each(F.Range.from_center_rel(100 * P.nF, 0.05))
        self.rp2040.core_regulator.power_out.decoupled.decouple().capacitance.merge(
            F.Range.from_center_rel(1 * P.uF, 0.05)
        )

        for c in self.get_children_modules(types=F.Capacitor):
            if F.Constant(100 * P.nF).is_subset_of(c.capacitance):
                c.add(F.has_footprint_requirement_defined([("0201", 2)]))
            else:
                c.add(
                    F.has_footprint_requirement_defined(
                        [("0402", 2), ("0603", 2), ("0805", 2)]
                    )
                )

        for r in self.get_children_modules(types=F.Resistor):
            if F.Constant(27.4 * P.ohm).is_subset_of(r.resistance):
                r.add(F.has_footprint_requirement_defined([("0201", 2)]))
            else:
                r.add(F.has_footprint_requirement_defined([("0402", 2)]))

        self.reset_button.add(F.has_descriptive_properties_defined({"LCSC": "C139797"}))
        self.boot_selector.switch.add(
            F.has_descriptive_properties_defined({"LCSC": "C139797"})
        )

        # ----------------------------------------
        #              connections
        # ----------------------------------------
        # power
        power_vbus.connect(self.ldo.power_in)
        power_3v3.connect(
            self.rp2040.power_io,
            self.adc_voltage_reference.power_in,
            self.rp2040.power_usb_phy,
            self.flash.power,
        )
        power_3v3.connect_via(self.rp2040.core_regulator, self.rp2040.power_core)

        self.ldo.enable_output()

        # rp2040
        self.flash.qspi.connect(self.rp2040.qspi)
        self.flash.qspi.chip_select.connect(self.boot_selector.logic_out)

        terminated_usb.connect(self.usb.usb_if.d)

        self.rp2040.xtal_if.connect(self.clock_source.xtal_if)

        self.rp2040.power_adc.connect(self.adc_voltage_reference.reference_out)

        self.rp2040.swd.connect(self.debug_header.swd)

        self.rp2040.run.signal.connect_via(
            self.reset_button, self.rp2040.run.reference.lv
        )

        self.status_led.logic_in.connect(self.rp2040.gpio[25])
        self.rp2040.pinmux.enable(self.rp2040.gpio[25])

    @L.rt_field
    def pcb_layout(self):
        from faebryk.exporters.pcb.layout.absolute import LayoutAbsolute
        from faebryk.exporters.pcb.layout.extrude import LayoutExtrude
        from faebryk.exporters.pcb.layout.typehierarchy import LayoutTypeHierarchy

        Point = F.has_pcb_position.Point
        L = F.has_pcb_position.layer_type
        LVL = LayoutTypeHierarchy.Level

        layout = F.has_pcb_layout_defined(
            layout=LayoutTypeHierarchy(
                layouts=[
                    LVL(
                        mod_type=F.RP2040,
                        layout=LayoutAbsolute(
                            Point((0, 0, 0, L.NONE)),
                        ),
                    ),
                    LVL(
                        mod_type=F.LDO,
                        layout=LayoutAbsolute(Point((0, -20, 270, L.NONE))),
                    ),
                    LVL(
                        mod_type=F.LEDIndicator,
                        layout=LayoutAbsolute(Point((4.5, -15, 90, L.NONE))),
                    ),
                    LVL(
                        mod_type=type(self.reset_button),
                        layout=LayoutAbsolute(Point((1, -15, 90, L.NONE))),
                    ),
                    LVL(
                        mod_type=self.BootSelector,
                        layout=LayoutAbsolute(
                            Point((-4, -15, 90, L.NONE)),
                        ),
                        children_layout=LayoutTypeHierarchy(
                            layouts=[
                                LVL(
                                    mod_type=F.Switch(F.Electrical),
                                    layout=LayoutAbsolute(
                                        Point((0, 0, 0, L.NONE)),
                                    ),
                                ),
                                LVL(
                                    mod_type=F.Resistor,
                                    layout=LayoutExtrude(
                                        base=Point((-7, -1.5, 0, L.NONE)),
                                        vector=(0, 2.25, 180),
                                        reverse_order=True,
                                        dynamic_rotation=True,
                                    ),
                                ),
                            ],
                        ),
                    ),
                    LVL(
                        mod_type=type(self.flash),
                        layout=LayoutAbsolute(
                            Point((-3.5, -8, 0, L.NONE)),
                        ),
                    ),
                    LVL(
                        mod_type=F.Resistor,
                        layout=LayoutExtrude(
                            base=Point((4, -9.75, 0, L.NONE)), vector=(0, 1.25, 180)
                        ),
                    ),
                    LVL(
                        mod_type=self.PICO_DebugHeader,
                        layout=LayoutAbsolute(
                            Point((4.5, 8, 90, L.NONE)),
                        ),
                    ),
                    LVL(
                        mod_type=F.Crystal_Oscillator,
                        layout=LayoutAbsolute(
                            Point((-2, 9.5, 0, L.NONE)),
                        ),
                        children_layout=LayoutTypeHierarchy(
                            layouts=[
                                LVL(
                                    mod_type=F.Crystal,
                                    layout=LayoutAbsolute(
                                        Point((0, 0, 0, L.NONE)),
                                    ),
                                ),
                                LVL(
                                    mod_type=F.Resistor,
                                    layout=LayoutAbsolute(
                                        Point((1.75, -2.5, 0, L.NONE)),
                                    ),
                                ),
                                LVL(
                                    mod_type=F.Capacitor,
                                    layout=LayoutExtrude(
                                        base=Point((3, 0, 90, L.NONE)),
                                        vector=(0, -6, 180),
                                        dynamic_rotation=True,
                                        reverse_order=True,
                                    ),
                                ),
                            ],
                        ),
                    ),
                    LVL(
                        mod_type=self.PICO_ADC_VoltageReference,
                        layout=LayoutAbsolute(
                            Point((0.75, -6, 0, L.NONE)),
                        ),
                        children_layout=LayoutTypeHierarchy(
                            layouts=[
                                LVL(
                                    mod_type=F.FilterElectricalRC,
                                    layout=LayoutAbsolute(
                                        Point((0, 0, 0, L.NONE)),
                                    ),
                                    children_layout=LayoutTypeHierarchy(
                                        layouts=[
                                            LVL(
                                                mod_type=F.Capacitor,
                                                layout=LayoutAbsolute(
                                                    Point((0, 0, 0, L.NONE)),
                                                ),
                                            ),
                                            LVL(
                                                mod_type=F.Resistor,
                                                layout=LayoutAbsolute(
                                                    Point((1.25, 0, 270, L.NONE)),
                                                ),
                                            ),
                                        ],
                                    ),
                                ),
                            ],
                        ),
                    ),
                ]
            )
        )

        return layout
