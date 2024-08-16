# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.can_attach_to_footprint_symmetrically import (
    can_attach_to_footprint_symmetrically,
)
from faebryk.library.Constant import Constant
from faebryk.library.has_defined_footprint import has_defined_footprint
from faebryk.library.has_designator_prefix_defined import (
    has_designator_prefix_defined,
)
from faebryk.library.KicadFootprint import KicadFootprint
from faebryk.library.TBD import TBD
from faebryk.libs.units import P, Quantity

logger = logging.getLogger(__name__)


class Mounting_Hole(Module):
    def __init__(self) -> None:
        super().__init__()

        class PARAMs(Module.PARAMS()):
            diameter = TBD[Quantity]()

        self.PARAMs = PARAMs(self)

        self.add_trait(can_attach_to_footprint_symmetrically())
        self.add_trait(has_designator_prefix_defined("H"))

        # Only 3.2mm supported for now
        self.PARAMs.diameter.merge(Constant(3.2 * P.mm))

        self.add_trait(
            has_defined_footprint(
                KicadFootprint("MountingHole:MountingHole_3.2mm_M3_Pad", pin_names=[])
            )
        )
