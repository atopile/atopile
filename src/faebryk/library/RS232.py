# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class RS232(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    tx = F.ElectricLogic.MakeChild()
    rx = F.ElectricLogic.MakeChild()
    dtr = F.ElectricLogic.MakeChild()
    dcd = F.ElectricLogic.MakeChild()
    dsr = F.ElectricLogic.MakeChild()
    ri = F.ElectricLogic.MakeChild()
    rts = F.ElectricLogic.MakeChild()
    cts = F.ElectricLogic.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.is_interface.MakeChild()

    _single_electric_reference = fabll._ChildField(F.has_single_electric_reference)

    # ----------------------------------------
    #                WIP
    # ----------------------------------------
