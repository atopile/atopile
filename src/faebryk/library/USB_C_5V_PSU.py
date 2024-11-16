# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class USB_C_5V_PSU(Module):
    # interfaces
    power_out: F.ElectricPower
    usb: F.USB_C

    # components
    configuration_resistors = L.list_field(
        2,
        lambda: F.Resistor().builder(
            lambda r: r.resistance.constrain_subset(
                L.Range.from_center_rel(5.1 * P.kohm, 0.05)
            )
        ),
    )

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __preinit__(self):
        # configure as ufp with 5V@max3A
        self.usb.cc1.connect_via(self.configuration_resistors[0], self.power_out.lv)
        self.usb.cc2.connect_via(self.configuration_resistors[1], self.power_out.lv)
