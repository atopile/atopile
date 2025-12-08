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

    def on_obj_set(self):
        fabll.Traits.create_and_add_instance_to(
            node=self.tx.get(), trait=F.has_net_name_suggestion
        ).setup(name="TX", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.rx.get(), trait=F.has_net_name_suggestion
        ).setup(name="RX", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.dtr.get(), trait=F.has_net_name_suggestion
        ).setup(name="DTR", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.dcd.get(), trait=F.has_net_name_suggestion
        ).setup(name="DCD", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.dsr.get(), trait=F.has_net_name_suggestion
        ).setup(name="DSR", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.ri.get(), trait=F.has_net_name_suggestion
        ).setup(name="RI", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.rts.get(), trait=F.has_net_name_suggestion
        ).setup(name="RTS", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.cts.get(), trait=F.has_net_name_suggestion
        ).setup(name="CTS", level=F.has_net_name_suggestion.Level.SUGGESTED)
