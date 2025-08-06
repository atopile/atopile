# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.exporters.pcb.layout.heuristic_decoupling import (
    LayoutHeuristicElectricalClosenessDecouplingCaps,
)
from faebryk.exporters.pcb.layout.heuristic_pulls import (
    LayoutHeuristicElectricalClosenessPullResistors,
)
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.smd import SMDSize
from faebryk.libs.units import P  # noqa: F401
from test.common.resources.fabll_modules.RP2040 import RP2040
from test.common.resources.fabll_modules.Winbond_Elec_W25Q128JVSIQ import (
    Winbond_Elec_W25Q128JVSIQ,
)

logger = logging.getLogger(__name__)


class RP2040_ReferenceDesign(Module):
    """Minimal required design for the Raspberry Pi RP2040 microcontroller.
    Based on the official Raspberry Pi RP2040 hardware design guidlines.
    """

    class Jumper(Module):
        logic_out: F.ElectricLogic

        resistor: F.Resistor
        switch = L.f_field(F.Switch(F.Electrical))()

        def __preinit__(self):
            self.resistor.resistance.constrain_subset(
                L.Range.from_center_rel(1 * P.kohm, 0.05)
            )
            self.logic_out.set_weak(True, self).resistance.alias_is(
                self.resistor.resistance
            )
            self.logic_out.line.connect_via(
                [self.resistor, self.switch], self.logic_out.reference.lv
            )

            # TODO this is not nice
            fp = F.KicadFootprint(pin_names=["1", "2"])
            fp.add(
                F.KicadFootprint.has_kicad_identifier(
                    "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
                )
            )
            self.switch.attach_to_footprint.attach(fp)
            # TODO make other trait for manual footprint, no pick
            self.switch.add(F.has_part_removed())

        @L.rt_field
        def single_reference(self):
            return F.has_single_electric_reference_defined(self.logic_out.reference)

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------

    # function
    rp2040: RP2040
    ldo: F.LDO
    clock_source: F.Crystal_Oscillator
    flash: Winbond_Elec_W25Q128JVSIQ

    # IO
    usb: F.USB2_0

    # UI
    boot_selector: Jumper

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://datasheets.raspberrypi.com/rp2040/hardware-design-with-rp2040.pdf"
    )

    def __preinit__(self):
        # ----------------------------------------
        #                aliasess
        # ----------------------------------------
        power_3v3 = self.add(F.ElectricPower())
        power_vbus = self.usb.usb_if.buspower

        # ----------------------------------------
        #            parametrization
        # ----------------------------------------
        # LDO
        self.ldo.output_current.constrain_ge(600 * P.mA)
        self.ldo.power_in.decoupled.decouple(owner=self).explicit(10 * P.uF)
        self.ldo.power_out.decoupled.decouple(owner=self).explicit(10 * P.uF)

        self.ldo.add(F.has_explicit_part.by_supplier("C5250992"))
        self.ldo.output_current.alias_is(1 * P.A)

        # XTAL
        xtal = self.clock_source.crystal
        xtal.load_capacitance.constrain_subset(L.Range.from_center_rel(10 * P.pF, 0.2))
        xtal.frequency.constrain_subset(L.Range.from_center_rel(12 * P.MHz, 0.05))

        self.clock_source.current_limiting_resistor.resistance.constrain_subset(
            L.Range.from_center_rel(1 * P.kohm, 0.05)
        )

        xtal.add(F.has_explicit_part.by_supplier("C20625731"))
        xtal.frequency.alias_is(12 * P.MHz)
        xtal.load_capacitance.alias_is(10 * P.pF)

        # USB
        terminated_usb_data = self.add(
            self.usb.usb_if.d.terminated(), "_terminated_usb_data"
        )
        terminated_usb_data.impedance.constrain_subset(
            L.Range.from_center_rel(27.4 * P.ohm, 0.05)
        )

        # Flash
        self.flash.memory_size.constrain_subset(16 * P.Mbit)
        self.flash.decoupled.decouple(owner=self).explicit(100 * P.nF)

        # Power rails
        self.rp2040.power_io.decoupled.decouple(owner=self, count=6).explicit(
            100 * P.nF
        )
        self.rp2040.power_adc.decoupled.decouple(owner=self).explicit(100 * P.nF)
        self.rp2040.power_core.decoupled.decouple(owner=self, count=2).explicit(
            100 * P.nF
        )
        self.rp2040.power_usb_phy.decoupled.decouple(owner=self).explicit(100 * P.nF)
        self.rp2040.core_regulator.power_in.decoupled.decouple(owner=self).explicit(
            1 * P.uF
        )
        power_3v3.decoupled.decouple(owner=self).explicit(10 * P.uF)
        self.rp2040.core_regulator.power_out.decoupled.decouple(owner=self).explicit(
            1 * P.uF
        )
        # ----------------------------------------
        #              connections
        # ----------------------------------------
        # power
        power_vbus.connect_via(self.ldo, power_3v3)
        power_3v3.connect(
            self.rp2040.power_io,
            self.rp2040.power_adc,
            self.rp2040.power_usb_phy,
            self.flash.power,
        )
        power_3v3.connect_via(self.rp2040.core_regulator, self.rp2040.power_core)

        #
        self.flash.qspi.connect(self.rp2040.qspi)
        self.flash.qspi.chip_select.connect(self.boot_selector.logic_out)

        terminated_usb_data.connect(self.rp2040.usb)

        self.rp2040.xtal_if.connect(self.clock_source.xtal_if)

        LayoutHeuristicElectricalClosenessDecouplingCaps.add_to_all_suitable_modules(  # noqa: E501
            self
        )
        caps_100nF = self.get_children(
            direct_only=False,
            types=F.Capacitor,
            f_filter=lambda c: bool(
                c.capacitance.try_get_literal()
                == L.Range.from_center_rel(100 * P.nF, 0.2)
            ),
        )
        for c in caps_100nF:
            c.explicit(size=SMDSize.I0201)

        LayoutHeuristicElectricalClosenessPullResistors.add_to_all_suitable_modules(
            self
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
                        mod_type=RP2040,
                        layout=LayoutAbsolute(
                            Point((0, 0, 0, L.NONE)),
                        ),
                    ),
                    LayoutTypeHierarchy.Level(
                        mod_type=F.LDO,
                        layout=LayoutAbsolute(Point((10, 14, 180, L.NONE))),
                    ),
                    LayoutTypeHierarchy.Level(
                        mod_type=type(self.boot_selector),
                        layout=LayoutAbsolute(
                            Point((-1.75, -11.5, 0, L.NONE)),
                        ),
                        children_layout=LayoutExtrude(
                            vector=(3.5, 0, 90),
                        ),
                    ),
                    LayoutTypeHierarchy.Level(
                        mod_type=type(self.flash),
                        layout=LayoutAbsolute(
                            Point((-1.95, -20, 0, L.NONE)),
                        ),
                    ),
                    LayoutTypeHierarchy.Level(
                        mod_type=F.Crystal_Oscillator,
                        layout=LayoutAbsolute(
                            Point((-10, 15, 0, L.NONE)),
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
