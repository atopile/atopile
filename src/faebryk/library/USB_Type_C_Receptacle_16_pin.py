# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.core.core import Module
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.DifferentialPair import DifferentialPair
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined


class USB_Type_C_Receptacle_16_pin(Module):
    def __init__(self) -> None:
        super().__init__()

        # interfaces
        class _IFs(Module.IFS()):
            # TODO make arrays?
            cc1 = Electrical()
            cc2 = Electrical()
            sbu1 = Electrical()
            sbu2 = Electrical()
            shield = Electrical()
            # power
            power = ElectricPower()
            # ds: p, n
            d = DifferentialPair()

        self.IFs = _IFs(self)

        vbus = self.IFs.power.IFs.hv
        gnd = self.IFs.power.IFs.lv

        self.add_trait(
            can_attach_to_footprint_via_pinmap(
                {
                    "A1": gnd,
                    "A4": vbus,
                    "A5": self.IFs.cc1,
                    "A6": self.IFs.d.IFs.p,
                    "A7": self.IFs.d.IFs.n,
                    "A8": self.IFs.sbu1,
                    "A9": vbus,
                    "A12": gnd,
                    "B1": gnd,
                    "B4": vbus,
                    "B5": self.IFs.cc2,
                    "B6": self.IFs.d.IFs.p,
                    "B7": self.IFs.d.IFs.n,
                    "B8": self.IFs.sbu2,
                    "B9": vbus,
                    "B12": gnd,
                    "0": self.IFs.shield,
                    "1": self.IFs.shield,
                    "2": self.IFs.shield,
                    "3": self.IFs.shield,
                }
            )
        )

        self.add_trait(has_designator_prefix_defined("J"))
