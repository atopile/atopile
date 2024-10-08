# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.units import P


class UART_Base(ModuleInterface):
    rx: F.ElectricLogic
    tx: F.ElectricLogic

    baud = L.p_field(unit=P.baud)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def _on_connect(self, other: "UART_Base"):
        super()._on_connect(other)

        self.baud.alias_is(other.baud)
