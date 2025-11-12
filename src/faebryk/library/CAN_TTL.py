# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class CAN_TTL(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    rx = F.ElectricLogic.MakeChild()
    tx = F.ElectricLogic.MakeChild()

    baudrate = F.Parameters.NumericParameter.MakeChild(unit=F.Units.BitPerSecond)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.is_interface.MakeChild()

    # ----------------------------------------
    #                 WIP
    # ----------------------------------------

    _single_electric_reference = fabll.ChildField(F.has_single_electric_reference)
