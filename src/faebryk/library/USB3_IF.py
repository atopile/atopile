# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L


class USB3_IF(ModuleInterface):
    usb_if: F.USB2_0_IF
    rx: F.DifferentialPair
    tx: F.DifferentialPair
    gnd_drain: F.Electrical

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )
