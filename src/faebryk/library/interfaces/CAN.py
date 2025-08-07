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
