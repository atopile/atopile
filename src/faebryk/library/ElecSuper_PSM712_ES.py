# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class ElecSuper_PSM712_ES(Module):
    """
    RS485 bus ESD and surge protection

    17A 350W Bidirectional SOT-23
    ESD and Surge Protection (TVS/ESD) ROHS
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    rs485: F.RS485HalfDuplex

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )
    explicit_part = L.f_field(F.has_explicit_part.by_mfr)("ElecSuper", "PSM712-ES")

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.rs485.diff_pair.n.line: ["1"],
                self.rs485.diff_pair.p.line: ["2"],
                self.rs485.diff_pair.n.reference.lv: ["3"],
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
