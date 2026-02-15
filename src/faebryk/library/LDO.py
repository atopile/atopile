# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class LDO(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    vin = F.Electrical.MakeChild()
    vout = F.Electrical.MakeChild()
    gnd = F.Electrical.MakeChild()

    output_voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    max_input_voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    output_current = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)
    dropout_voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    _is_pickable = fabll.Traits.MakeEdge(
        F.Pickable.is_pickable_by_type.MakeChild(
            endpoint=F.Pickable.is_pickable_by_type.Endpoint.LDOS,
            params={
                "output_voltage": output_voltage,
                "max_input_voltage": max_input_voltage,
                "output_current": output_current,
                "dropout_voltage": dropout_voltage,
            },
        )
    )

    _can_attatch_to_footprint = fabll.Traits.MakeEdge(
        F.Footprints.can_attach_to_footprint.MakeChild()
    )

    vin_lead = F.Lead.is_lead.MakeChild()
    vout_lead = F.Lead.is_lead.MakeChild()
    gnd_lead = F.Lead.is_lead.MakeChild()

    vin.add_dependant(fabll.Traits.MakeEdge(vin_lead, [vin]))
    vout.add_dependant(fabll.Traits.MakeEdge(vout_lead, [vout]))
    gnd.add_dependant(fabll.Traits.MakeEdge(gnd_lead, [gnd]))

    vin_pad_names = fabll.Traits.MakeEdge(
        F.Lead.can_attach_to_pad_by_name.MakeChild(regex=r"in|vin|vi|\+|1"),
        [vin_lead],
    )
    vout_pad_names = fabll.Traits.MakeEdge(
        F.Lead.can_attach_to_pad_by_name.MakeChild(regex=r"out|vout|vo|2"),
        [vout_lead],
    )
    gnd_pad_names = fabll.Traits.MakeEdge(
        F.Lead.can_attach_to_pad_by_name.MakeChild(regex=r"gnd|ground|3|-"),
        [gnd_lead],
    )

    _can_bridge = fabll.Traits.MakeEdge(F.can_bridge.MakeChild(["vin"], ["vout"]))

    designator_prefix = fabll.Traits.MakeEdge(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.U)
    )
