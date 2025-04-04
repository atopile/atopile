# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L


class JTAG(ModuleInterface):
    dbgrq: F.ElectricLogic
    tdo: F.ElectricLogic
    tdi: F.ElectricLogic
    tms: F.ElectricLogic
    tck: F.ElectricLogic
    n_trst: F.ElectricLogic
    n_reset: F.ElectricLogic
    vtref: F.ElectricPower

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )
