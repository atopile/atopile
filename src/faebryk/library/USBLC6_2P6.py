# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.USB2_0 import USB2_0


class USBLC6_2P6(Module):
    """
    Low capacitance TVS diode array (for USB2.0)
    """

    def __init__(self) -> None:
        super().__init__()

        # interfaces
        class _IFs(Module.IFS()):
            usb = USB2_0()

        self.IFs = _IFs(self)

        x = self.IFs
        self.add_trait(
            can_attach_to_footprint_via_pinmap(
                {
                    "1": x.usb.IFs.usb_if.IFs.d.IFs.p,
                    "2": x.usb.IFs.usb_if.IFs.buspower.IFs.lv,
                    "3": x.usb.IFs.usb_if.IFs.d.IFs.n,
                    "4": x.usb.IFs.usb_if.IFs.d.IFs.n,
                    "5": x.usb.IFs.usb_if.IFs.buspower.IFs.hv,
                    "6": x.usb.IFs.usb_if.IFs.d.IFs.p,
                }
            )
        )

        self.add_trait(has_designator_prefix_defined("U"))

        self.add_trait(
            has_datasheet_defined(
                "https://datasheet.lcsc.com/lcsc/2108132230_TECH-PUBLIC-USBLC6-2P6_C2827693.pdf"
            )
        )
