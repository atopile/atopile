# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.units import P


class USB2_0_IF(ModuleInterface):
    class Data(F.DifferentialPair):
        @L.rt_field
        def single_electric_reference(self):
            return F.has_single_electric_reference_defined(
                F.ElectricLogic.connect_all_module_references(self)
            )

        def __preinit__(self):
            self.p.reference.voltage.merge(F.Range(0 * P.V, 3.6 * P.V))
            self.n.reference.voltage.merge(F.Range(0 * P.V, 3.6 * P.V))

    d: Data
    buspower: F.ElectricPower
