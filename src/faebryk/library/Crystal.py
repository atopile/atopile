# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L


class Crystal(Module):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    gnd: F.Electrical
    unnamed = L.list_field(2, F.Electrical)

    # ----------------------------------------
    #               parameters
    # ----------------------------------------
    frequency: F.TBD
    frequency_tolerance: F.TBD
    frequency_temperature_tolerance: F.TBD
    frequency_ageing: F.TBD
    equivalent_series_resistance: F.TBD
    shunt_capacitance: F.TBD
    load_capacitance: F.TBD

    # ----------------------------------------
    #                traits
    # ----------------------------------------
    designator = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.XTAL
    )
    footprint: F.can_attach_to_footprint_symmetrically

    # ----------------------------------------
    #                connections
    # ----------------------------------------
