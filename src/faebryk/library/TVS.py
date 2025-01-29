# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class TVS(F.Diode):
    reverse_breakdown_voltage = L.p_field(units=P.V)

    @L.rt_field
    def pickable(self):
        return F.is_pickable_by_type(
            F.is_pickable_by_type.Type.TVS,
            F.Diode().get_trait(F.is_pickable_by_type).get_parameters()  # TODO: better
            | {
                "reverse_breakdown_voltage": self.reverse_breakdown_voltage,
            },
        )
