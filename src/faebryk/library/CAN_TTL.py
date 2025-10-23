# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.units import P


class CAN_TTL(fabll.ModuleInterface):
    rx: F.ElectricLogic
    tx: F.ElectricLogic

    speed = fabll.p_field(units=P.bps)

    @fabll.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __preinit__(self) -> None:
        self.speed.add(F.is_bus_parameter())
