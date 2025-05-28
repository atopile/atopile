# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class Shenzhen_Kinghelm_Elec_KH_BNC75_3511(Module):
    """
    Inner hole BNC connector board-end elbow 3GHz -55℃~+155℃ 75Ω 9.5mm
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    line: F.ElectricSignal
    shield: F.Electrical

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    explicit_part = L.f_field(F.has_explicit_part.by_supplier)("C2837588")
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.J
    )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.line.line: ["OUT"],
                self.shield: ["2", "3", "4"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        pass
