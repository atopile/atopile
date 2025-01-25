# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class pf_74AHCT2G125(Module):
    """
    The 74AHC1G/AHCT1G125 is a high-speed Si-gate CMOS device.
    The 74AHC1G/AHCT1G125 provides one non-inverting buffer/line
    driver with 3-state output. The 3-state output is controlled
    by the output enable input (OE). A HIGH at OE causes the
    output to assume a high-impedance OFF-state.
    """

    # interfaces

    power: F.ElectricPower
    a: F.ElectricLogic  # IN
    y: F.ElectricLogic  # OUT
    oe: F.ElectricLogic  # enable, active low

    @L.rt_field
    def attach_to_footprint(self):
        x = self
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": x.oe.line,
                "2": x.a.line,
                "3": x.power.lv,
                "4": x.y.line,
                "5": x.power.hv,
            }
        )

    def __preinit__(self):
        self.power.voltage.constrain_subset(L.Range(4.5 * P.V, 5.5 * P.V))

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.a, self.y)

    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://datasheet.lcsc.com/lcsc/2304140030_Nexperia-74AHCT1G125GV-125_C12494.pdf"
    )

    @L.rt_field
    def can_be_decoupled(self):
        class _(F.can_be_decoupled.impl()):
            def decouple(self, owner: Module):
                obj = self.get_obj(pf_74AHCT2G125)
                obj.power.decoupled.decouple(owner=owner)

        return _()
