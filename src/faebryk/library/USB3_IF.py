# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class USB3_IF(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    usb_if = F.USB2_0_IF.MakeChild()
    rx = F.DifferentialPair.MakeChild()
    tx = F.DifferentialPair.MakeChild()
    gnd_drain = F.Electrical.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    def on_obj_set(self):
        fabll.Traits.create_and_add_instance_to(
            node=self.rx.get(), trait=F.has_net_name_suggestion
        ).setup(name="RX", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.tx.get(), trait=F.has_net_name_suggestion
        ).setup(name="TX", level=F.has_net_name_suggestion.Level.SUGGESTED)
