# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class FerriteBead(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    unnamed = [F.Electrical.MakeChild() for _ in range(2)]

    impedance_at_frequency = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ohm)
    current_rating = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)
    dc_resistance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ohm)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    _is_pickable = fabll.Traits.MakeEdge(
        F.Pickable.is_pickable_by_type.MakeChild(
            endpoint=F.Pickable.is_pickable_by_type.Endpoint.FERRITE_BEADS,
            params={
                "impedance_at_frequency": impedance_at_frequency,
                "current_rating": current_rating,
                "dc_resistance": dc_resistance,
            },
        )
    )

    _can_attatch_to_footprint = fabll.Traits.MakeEdge(
        F.Footprints.can_attach_to_footprint.MakeChild()
    )

    for e in unnamed:
        lead = fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [e])
        lead.add_dependant(
            fabll.Traits.MakeEdge(F.Lead.can_attach_to_any_pad.MakeChild(), [lead])
        )
        e.add_dependant(lead)

    _can_bridge = fabll.Traits.MakeEdge(
        F.can_bridge.MakeChild(["unnamed[0]"], ["unnamed[1]"])
    )

    designator_prefix = fabll.Traits.MakeEdge(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.FB)
    )
