# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.units import P


class CAN_TTL(fabll.Node):

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    rx = F.ElectricLogic.MakeChild()
    tx = F.ElectricLogic.MakeChild()

    baudrate = fabll.Parameter.MakeChild_Numeric(unit=F.Units.BitPerSecond)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.is_interface.MakeChild()

    # ----------------------------------------
    #                 WIP
    # ----------------------------------------

    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __preinit__(self) -> None:
        self.baudrate.add(F.is_bus_parameter())
