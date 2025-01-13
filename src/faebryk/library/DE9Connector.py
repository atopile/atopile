# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class DE9Connector(Module):
    """
    DE-9 connector
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    contact = L.list_field(9, F.Electrical)
    shield: F.Electrical

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.X
    )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.shield: ["MH1"],
                self.shield: ["MH2"],
                self.contact[0]: ["1"],
                self.contact[1]: ["2"],
                self.contact[2]: ["3"],
                self.contact[3]: ["4"],
                self.contact[4]: ["5"],
                self.contact[5]: ["6"],
                self.contact[6]: ["7"],
                self.contact[7]: ["8"],
                self.contact[8]: ["9"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    @L.rt_field
    def can_attach_to_footprint(self):
        pinmap = {f"{i+1}": ei for i, ei in enumerate(self.contact)}
        pinmap.update({"10": self.shield})
        return F.can_attach_to_footprint_via_pinmap(pinmap)

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        pass
