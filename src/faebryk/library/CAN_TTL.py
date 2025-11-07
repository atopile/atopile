# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from ast import Or
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

    _single_electric_reference = fabll.ChildField(F.has_single_electric_reference)
