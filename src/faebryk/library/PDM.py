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

    # ----------------------------------------
    #                WIP
    # ----------------------------------------
    _single_electric_reference = fabll._ChildField(F.has_single_electric_reference)

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.data.line.add(F.has_net_name("DATA", level=F.has_net_name.Level.SUGGESTED))
        self.clock.line.add(
            F.has_net_name("CLOCK", level=F.has_net_name.Level.SUGGESTED)
        )
        self.select.line.add(
            F.has_net_name("SELECT", level=F.has_net_name.Level.SUGGESTED)
        )
