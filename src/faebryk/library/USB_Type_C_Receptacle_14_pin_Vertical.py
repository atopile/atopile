# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.picker.picker import DescriptiveProperties


class USB_Type_C_Receptacle_14_pin_Vertical(Module):
    """
    14 pin vertical female USB Type-C connector
    918-418K2022Y40000
    """

    # interfaces

    # TODO make arrays?
    cc1: F.Electrical
    cc2: F.Electrical
    shield: F.Electrical
    # power
    vbus: F.ElectricPower
    # diffpairs: p, n
    usb: F.USB2_0

    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "Jing Extension of the Electronic Co.",  # noqa: E501
            DescriptiveProperties.partno: "918-418K2022Y40000",
        }
    )

    @L.rt_field
    def attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.vbus.lv,
                "2": self.vbus.hv,
                "3": self.usb.usb_if.d.n.signal,
                "4": self.usb.usb_if.d.p.signal,
                "5": self.cc2,
                "6": self.vbus.hv,
                "7": self.vbus.lv,
                "8": self.vbus.lv,
                "9": self.vbus.hv,
                "10": self.usb.usb_if.d.n.signal,
                "11": self.usb.usb_if.d.p.signal,
                "12": self.cc1,
                "13": self.vbus.hv,
                "14": self.vbus.lv,
                "0": self.shield,
            }
        )

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.J
    )
