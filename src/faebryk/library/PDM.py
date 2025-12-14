# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class PDM(fabll.Node):
    """
    Pulse Density Modulation is a way of representing a sampled signal as a stream of
    single bits where the relative density of the pulses correspond to the analog
    signal's amplitude
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    data = F.ElectricLogic.MakeChild()
    clock = F.ElectricLogic.MakeChild()
    select = F.ElectricLogic.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    _single_electric_reference = fabll._ChildField(F.has_single_electric_reference)

    def on_obj_set(self):
        fabll.Traits.create_and_add_instance_to(
            node=self.data.get(), trait=F.has_net_name_suggestion
        ).setup(name="DATA", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.clock.get(), trait=F.has_net_name_suggestion
        ).setup(name="CLOCK", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.select.get(), trait=F.has_net_name_suggestion
        ).setup(name="SELECT", level=F.has_net_name_suggestion.Level.SUGGESTED)
