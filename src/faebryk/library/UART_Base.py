# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.units import P


class UART_Base(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    rx = F.ElectricLogic.MakeChild()
    tx = F.ElectricLogic.MakeChild()

    baud = F.Parameters.NumericParameter.MakeChild(unit=F.Units.BitPerSecond)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.is_interface.MakeChild()

    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    # ----------------------------------------
    #                WIP
    # ----------------------------------------

    def __preinit__(self) -> None:
        self.baud.add(F.is_bus_parameter())

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.rx.line.add(F.has_net_name("RX", level=F.has_net_name.Level.SUGGESTED))
        self.tx.line.add(F.has_net_name("TX", level=F.has_net_name.Level.SUGGESTED))
