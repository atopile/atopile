# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class RS232(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    tx = F.ElectricLogic.MakeChild()
    rx = F.ElectricLogic.MakeChild()
    dtr = F.ElectricLogic.MakeChild()
    dcd = F.ElectricLogic.MakeChild()
    dsr = F.ElectricLogic.MakeChild()
    ri = F.ElectricLogic.MakeChild()
    rts = F.ElectricLogic.MakeChild()
    cts = F.ElectricLogic.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )

    net_names = [
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="TX",
                level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[tx]
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="RX",
                level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[rx]
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="DTR",
                level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[dtr]
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="DCD",
                level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[dcd]
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="DSR",
                level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[dsr]
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="RI",
                level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[ri]
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="RTS",
                level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[rts]
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="CTS",
                level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[cts]
        ),
    ]
