# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.DifferentialPair import (
    DifferentialPair,
)
from faebryk.library.Electrical import Electrical
from faebryk.library.has_designator_prefix_defined import (
    has_designator_prefix_defined,
)
from faebryk.libs.util import times


class USB_Type_C_Receptacle_24_pin(Module):
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
            gnd = times(4, Electrical)
            vbus = times(4, Electrical)
            # diffpairs: p, n
            rx1 = DifferentialPair()
            rx2 = DifferentialPair()
            tx1 = DifferentialPair()
            tx2 = DifferentialPair()
            d1 = DifferentialPair()
            d2 = DifferentialPair()

        self.IFs = _IFs(self)

        self.add_trait(
            can_attach_to_footprint_via_pinmap(
                {
                    "A1": self.IFs.gnd[0],
                    "A2": self.IFs.tx1.IFs.p,
                    "A3": self.IFs.tx1.IFs.n,
                    "A4": self.IFs.vbus[0],
                    "A5": self.IFs.cc1,
                    "A6": self.IFs.d1.IFs.p,
                    "A7": self.IFs.d1.IFs.n,
                    "A8": self.IFs.sbu1,
                    "A9": self.IFs.vbus[1],
                    "A10": self.IFs.rx2.IFs.n,
                    "A11": self.IFs.rx2.IFs.p,
                    "A12": self.IFs.gnd[1],
                    "B1": self.IFs.gnd[2],
                    "B2": self.IFs.tx2.IFs.p,
                    "B3": self.IFs.tx2.IFs.n,
                    "B4": self.IFs.vbus[2],
                    "B5": self.IFs.cc2,
                    "B6": self.IFs.d2.IFs.p,
                    "B7": self.IFs.d2.IFs.n,
                    "B8": self.IFs.sbu2,
                    "B9": self.IFs.vbus[3],
                    "B10": self.IFs.rx1.IFs.n,
                    "B11": self.IFs.rx1.IFs.p,
                    "B12": self.IFs.gnd[3],
                    "0": self.IFs.shield,
                }
            )
        )

        self.add_trait(has_designator_prefix_defined("P"))
