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

    def on_obj_set(self):
        fabll.Traits.create_and_add_instance_to(
            node=self.rx.get(), trait=F.has_net_name
        ).setup(name="RX", level=F.has_net_name.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.tx.get(), trait=F.has_net_name
        ).setup(name="TX", level=F.has_net_name.Level.SUGGESTED)
