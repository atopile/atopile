# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.units import P


class CAN(ModuleInterface):
    """
    CAN bus interface
    """

    diff_pair: F.DifferentialPair

    speed = L.p_field(units=P.bps)

    def __preinit__(self) -> None:
        self.speed.add(F.is_bus_parameter())

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.diff_pair.p.line.add(
            F.has_net_name("CAN_H", level=F.has_net_name.Level.SUGGESTED)
        )
        self.diff_pair.n.line.add(
            F.has_net_name("CAN_L", level=F.has_net_name.Level.SUGGESTED)
        )
