# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import Quantity

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

    coil_rated_voltage: F.TBD[Quantity]
    coil_rated_current: F.TBD[Quantity]
    coil_resistance: F.TBD[Quantity]
    contact_max_switching_voltage: F.TBD[Quantity]
    contact_rated_switching_current: F.TBD[Quantity]
    contact_max_switchng_current: F.TBD[Quantity]

    designator_prefix = L.f_field(F.has_designator_prefix_defined)("RELAY")
