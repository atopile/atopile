# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class TVS(F.Diode):
    reverse_breakdown_voltage = L.p_field(units=P.V)

    pickable = L.f_field(F.is_pickable_by_type)(F.is_pickable_by_type.Type.TVS)
