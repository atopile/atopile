# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class UART_Base(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    rx = F.ElectricLogic.MakeChild()
    tx = F.ElectricLogic.MakeChild()

    baud = F.Parameters.NumericParameter.MakeChild(unit=F.Units.BitsPerSecond)

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
                name="RX", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[rx],
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="TX", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[tx],
        ),
    ]

    bus_parameters = [
        fabll.Traits.MakeEdge(F.is_alias_bus_parameter.MakeChild(), owner=[baud]),
    ]
