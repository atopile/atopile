# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class PDM(ModuleInterface):
    """
    Pulse Density Modulation is a way of representing a sampled signal as a stream of
    single bits where the relative density of the pulses correspond to the analog
    signal's amplitude
    """

    data: F.ElectricLogic
    clock: F.ElectricLogic
    select: F.ElectricLogic

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.data.line.add(F.has_net_name("DATA", level=F.has_net_name.Level.SUGGESTED))
        self.clock.line.add(
            F.has_net_name("CLOCK", level=F.has_net_name.Level.SUGGESTED)
        )
        self.select.line.add(
            F.has_net_name("SELECT", level=F.has_net_name.Level.SUGGESTED)
        )
