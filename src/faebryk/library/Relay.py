# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


# TODO: make generic (use Switch module, different switch models, bistable, etc.)
class Relay(Module):
    switch_a_nc: F.Electrical
    switch_a_common: F.Electrical
    switch_a_no: F.Electrical
    switch_b_no: F.Electrical
    switch_b_common: F.Electrical
    switch_b_nc: F.Electrical
    coil_p: F.Electrical
    coil_n: F.Electrical

    coil_rated_voltage = L.p_field(unit=P.V)
    coil_rated_current = L.p_field(unit=P.A)
    coil_resistance = L.p_field(unit=P.ohm)
    contact_max_switching_voltage = L.p_field(unit=P.V)
    contact_rated_switching_current = L.p_field(unit=P.A)
    contact_max_switchng_current = L.p_field(unit=P.A)

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.K
    )
