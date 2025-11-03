# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class RS232(fabll.Node):
    tx = F.ElectricLogic.MakeChild()
    rx = F.ElectricLogic.MakeChild()
    dtr = F.ElectricLogic.MakeChild()
    dcd = F.ElectricLogic.MakeChild()
    dsr = F.ElectricLogic.MakeChild()
    ri = F.ElectricLogic.MakeChild()
    rts = F.ElectricLogic.MakeChild()
    cts = F.ElectricLogic.MakeChild()

    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )
