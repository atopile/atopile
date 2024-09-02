# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L


class USB_C(ModuleInterface):
    usb3: F.USB3
    cc1: F.Electrical
    cc2: F.Electrical
    sbu1: F.Electrical
    sbu2: F.Electrical
    rx: F.DifferentialPair
    tx: F.DifferentialPair

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )
