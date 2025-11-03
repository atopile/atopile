# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.units import P


class UART_Base(fabll.Node):
    rx = F.ElectricLogic.MakeChild()
    tx = F.ElectricLogic.MakeChild()

    baud = fabll.Parameter.MakeChild_Numeric(unit=F.Units.BitPerSecond)

    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __preinit__(self) -> None:
        self.baud.add(F.is_bus_parameter())

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.rx.line.add(F.has_net_name("RX", level=F.has_net_name.Level.SUGGESTED))
        self.tx.line.add(F.has_net_name("TX", level=F.has_net_name.Level.SUGGESTED))
