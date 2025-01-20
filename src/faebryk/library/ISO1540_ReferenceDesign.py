# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class ISO1540_ReferenceDesign(Module):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    isolator: F.ISO1540

    # ----------------------------------------
    #                 traits
    # ----------------------------------------

    def __preinit__(self):
        self.isolator.non_iso.power.decoupled.decouple(
            owner=self
        ).capacitance.constrain_subset(L.Range.from_center_rel(10 * P.uF, 0.01))
        self.isolator.iso.power.decoupled.decouple(
            owner=self
        ).capacitance.constrain_subset(L.Range.from_center_rel(10 * P.uF, 0.01))
