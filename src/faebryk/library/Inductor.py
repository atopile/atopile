# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import Quantity


class Inductor(Module):
    unnamed = L.list_field(2, F.Electrical)

    inductance: F.TBD[Quantity]
    self_resonant_frequency: F.TBD[Quantity]
    rated_current: F.TBD[Quantity]
    dc_resistance: F.TBD[Quantity]

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(*self.unnamed)

    attach_to_footprint: F.can_attach_to_footprint_symmetrically

    @L.rt_field
    def simple_value_representation(self):
        from faebryk.core.util import (
            as_unit,
            as_unit_with_tolerance,
        )

        return F.has_simple_value_representation_based_on_params(
            (
                self.inductance,
                self.self_resonant_frequency,
                self.rated_current,
                self.dc_resistance,
            ),
            lambda ps: " ".join(
                filter(
                    None,
                    [
                        as_unit_with_tolerance(ps[0], "H"),
                        as_unit(ps[1], "Hz"),
                        as_unit(ps[2], "A"),
                        as_unit(ps[3], "Ω"),
                    ],
                )
            ),
        )

    designator_prefix = L.f_field(F.has_designator_prefix_defined)("L")
