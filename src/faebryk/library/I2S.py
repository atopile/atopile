# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.parameter import R
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class I2S(ModuleInterface):
    sd: F.ElectricLogic  # Serial Data
    ws: F.ElectricLogic  # Word Select (Left/Right Clock)
    sck: F.ElectricLogic  # Serial Clock

    sample_rate = L.p_field(units=P.hertz, domain=R.Domains.Numbers.NATURAL())
    bit_depth = L.p_field(units=P.bit, domain=R.Domains.Numbers.NATURAL())

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.sd.line.add(F.has_net_name("SD", level=F.has_net_name.Level.SUGGESTED))
        self.ws.line.add(F.has_net_name("WS", level=F.has_net_name.Level.SUGGESTED))
        self.sck.line.add(F.has_net_name("SCK", level=F.has_net_name.Level.SUGGESTED))
