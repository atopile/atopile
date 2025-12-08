# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class USB2_0_IF(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    d = F.DifferentialPair.MakeChild()
    buspower = F.ElectricPower.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    def on_obj_set(self):
        fabll.Traits.create_and_add_instance_to(
            node=self.d.get(), trait=F.has_net_name_suggestion
        ).setup(name="DATA", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.buspower.get(), trait=F.has_net_name_suggestion
        ).setup(name="VBUS", level=F.has_net_name_suggestion.Level.SUGGESTED)
