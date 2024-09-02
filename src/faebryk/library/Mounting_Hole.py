# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P, Quantity

logger = logging.getLogger(__name__)


class Mounting_Hole(Module):
    diameter: F.TBD[Quantity]

    attach_to_footprint: F.can_attach_to_footprint_symmetrically
    designator_prefix = L.f_field(F.has_designator_prefix_defined)("H")

    def __preinit__(self):
        # Only 3.2mm supported for now
        self.diameter.merge(F.Constant(3.2 * P.mm))

    # footprint = L.f_field(F.has_footprint_defined)(
    #    F.KicadFootprint("MountingHole:MountingHole_3.2mm_M3_Pad", pin_names=[])
    # )

    # TODO make back to f_field, rt_field because of imports
    @L.rt_field
    def footprint(self):
        return F.has_footprint_defined(
            F.KicadFootprint("MountingHole:MountingHole_3.2mm_M3_Pad", pin_names=[])
        )
