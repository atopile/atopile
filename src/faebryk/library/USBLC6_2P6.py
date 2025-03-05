# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L


class USBLC6_2P6(Module):
    """
    Low capacitance TVS diode array (for USB2.0)
    """

    # interfaces
    usb: F.USB2_0

    @L.rt_field
    def attach_to_footprint(self):
        x = self
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": x.usb.usb_if.d.p.line,
                "2": x.usb.usb_if.buspower.lv,
                "3": x.usb.usb_if.d.n.line,
                "4": x.usb.usb_if.d.n.line,
                "5": x.usb.usb_if.buspower.hv,
                "6": x.usb.usb_if.d.p.line,
            }
        )

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://datasheet.lcsc.com/lcsc/2108132230_TECH-PUBLIC-USBLC6-2P6_C2827693.pdf"
    )
