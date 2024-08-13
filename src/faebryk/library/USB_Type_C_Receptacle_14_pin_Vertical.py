# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_prefix_defined import (
    has_designator_prefix_defined,
)
from faebryk.library.USB2_0 import USB2_0


class USB_Type_C_Receptacle_14_pin_Vertical(Module):
    """
    14 pin vertical female USB Type-C connector
    918-418K2022Y40000
    """

    def __init__(self) -> None:
        super().__init__()

        # interfaces
        class _IFs(Module.IFS()):
            # TODO make arrays?
            cc1 = Electrical()
            cc2 = Electrical()
            shield = Electrical()
            # power
            vbus = ElectricPower()
            # diffpairs: p, n
            usb = USB2_0()

        self.IFs = _IFs(self)

        self.add_trait(
            can_attach_to_footprint_via_pinmap(
                {
                    "1": self.IFs.vbus.IFs.lv,
                    "2": self.IFs.vbus.IFs.hv,
                    "3": self.IFs.usb.IFs.usb_if.IFs.d.IFs.n,
                    "4": self.IFs.usb.IFs.usb_if.IFs.d.IFs.p,
                    "5": self.IFs.cc2,
                    "6": self.IFs.vbus.IFs.hv,
                    "7": self.IFs.vbus.IFs.lv,
                    "8": self.IFs.vbus.IFs.lv,
                    "9": self.IFs.vbus.IFs.hv,
                    "10": self.IFs.usb.IFs.usb_if.IFs.d.IFs.n,
                    "11": self.IFs.usb.IFs.usb_if.IFs.d.IFs.p,
                    "12": self.IFs.cc1,
                    "13": self.IFs.vbus.IFs.hv,
                    "14": self.IFs.vbus.IFs.lv,
                    "0": self.IFs.shield,
                }
            )
        )

        self.add_trait(has_designator_prefix_defined("J"))
