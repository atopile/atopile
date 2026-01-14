# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import StrEnum

import faebryk.core.node as fabll
import faebryk.library._F as F


class NetTie(fabll.Node):
    """
    A net tie component that can bridge different interfaces.

    Net ties are used to connect different nets together on the PCB,
    typically for connecting ground planes or power islands.

    Example usage in ato:
        # Basic 2-pin net tie connecting grounds
        basic_nettie = new NetTie

        # Connect high-voltage side instead of ground
        hv_nettie = new NetTie<connect_gnd=False>

        # 3-pin SMD net tie with 2mm pads
        wide_nettie = new NetTie<width=2.0, pin_count=3>

        # THT net tie
        tht_nettie = new NetTie<width=0.3, pad_type="THT">
    """

    class PadType(StrEnum):
        SMD = "SMD"
        THT = "THT"

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    # Part is removed - net ties don't go through part picking
    _has_part_removed = fabll.Traits.MakeEdge(F.has_part_removed.MakeChild())

    # Can attach to footprint
    _can_attach_to_footprint = fabll.Traits.MakeEdge(
        F.Footprints.can_attach_to_footprint.MakeChild()
    )

    # Designator prefix JP for jumper
    _designator_prefix = fabll.Traits.MakeEdge(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.JP)
    )

    power = F.Electrical.MakeChild()

    can_bridge = fabll.Traits.MakeEdge(
        F.can_bridge.MakeChild(in_=[power], out_=[power])
    )

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
        from "NetTie.py" import NetTie

        # Basic 2-pin net tie (SMD, 0.5mm pad, connects gnd)
        basic_nettie = new NetTie

        # Net tie connecting high-voltage side
        hv_nettie = new NetTie<connect_gnd=False>

        # 3-pin SMD net tie with 2mm pads
        wide_nettie = new NetTie<width=2.0, pin_count=3>

        # THT net tie with 0.3mm pads
        tht_nettie = new NetTie<width=0.3, pad_type="THT">

        # Bridge connect for 2-pin netties
        power_a = new ElectricPower
        power_b = new ElectricPower
        power_a ~> basic_nettie ~> power_b
        """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )
