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
    coil_power: F.ElectricPower

    coil_max_voltage = L.p_field(units=P.V)
    coil_max_current = L.p_field(units=P.A)
    coil_resistance = L.p_field(units=P.ohm)
    contact_max_switching_voltage = L.p_field(units=P.V)
    contact_max_switching_current = L.p_field(units=P.A)
    contact_max_current = L.p_field(units=P.A)

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.K
    )
