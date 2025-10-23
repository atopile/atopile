# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class RS232(fabll.ModuleInterface):
    tx: F.ElectricLogic
    rx: F.ElectricLogic
    dtr: F.ElectricLogic
    dcd: F.ElectricLogic
    dsr: F.ElectricLogic
    ri: F.ElectricLogic
    rts: F.ElectricLogic
    cts: F.ElectricLogic

    @fabll.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )
