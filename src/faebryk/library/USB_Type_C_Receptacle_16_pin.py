# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L


class USB_Type_C_Receptacle_16_pin(Module):
    # interfaces

    # TODO make arrays?
    cc1: F.Electrical
    cc2: F.Electrical
    sbu1: F.Electrical
    sbu2: F.Electrical
    shield: F.Electrical
    # power
    power: F.ElectricPower
    # ds: p, n
    d: F.DifferentialPair

    @L.rt_field
    def attach_to_footprint(self):
        vbus = self.power.hv
        gnd = self.power.lv

        return F.can_attach_to_footprint_via_pinmap(
            {
                "A1": gnd,
                "A4": vbus,
                "A5": self.cc1,
                "A6": self.d.p,
                "A7": self.d.n,
                "A8": self.sbu1,
                "A9": vbus,
                "A12": gnd,
                "B1": gnd,
                "B4": vbus,
                "B5": self.cc2,
                "B6": self.d.p,
                "B7": self.d.n,
                "B8": self.sbu2,
                "B9": vbus,
                "B12": gnd,
                "0": self.shield,
                "1": self.shield,
                "2": self.shield,
                "3": self.shield,
            }
        )

    designator_prefix = L.f_field(F.has_designator_prefix_defined)("J")