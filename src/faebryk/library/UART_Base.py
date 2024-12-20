# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.units import P
from faebryk.libs.util import cast_assert


class UART_Base(ModuleInterface):
    rx: F.ElectricLogic
    tx: F.ElectricLogic

    baud = L.p_field(units=P.baud)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __preinit__(self) -> None:
        self.baud.add(
            F.is_dynamic_by_connections_alias(
                lambda mif: cast_assert(UART_Base, mif).baud
            )
        )
