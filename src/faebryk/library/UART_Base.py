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

    baud = F.Parameters.NumericParameter.MakeChild(unit=F.Units.BitPerSecond)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )

    # self.rx.line.add(F.has_net_name("RX", level=F.has_net_name.Level.SUGGESTED))
    # self.tx.line.add(F.has_net_name("TX", level=F.has_net_name.Level.SUGGESTED))
