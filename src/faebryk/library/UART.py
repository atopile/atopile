# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface


class UART(ModuleInterface):
    base_uart: F.UART_Base
    rts: F.ElectricLogic
    cts: F.ElectricLogic
    dtr: F.ElectricLogic
    dsr: F.ElectricLogic
    dcd: F.ElectricLogic
    ri: F.ElectricLogic

    # TODO: this creates too many connections in some projects
    # @L.rt_field
    # def single_electric_reference(self):
    #    return F.has_single_electric_reference_defined(
    #       F.ElectricLogic.connect_all_module_references(self)
    #   )

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.rts.line.add(F.has_net_name("RTS", level=F.has_net_name.Level.SUGGESTED))
        self.cts.line.add(F.has_net_name("CTS", level=F.has_net_name.Level.SUGGESTED))
        self.dtr.line.add(F.has_net_name("DTR", level=F.has_net_name.Level.SUGGESTED))
        self.dsr.line.add(F.has_net_name("DSR", level=F.has_net_name.Level.SUGGESTED))
        self.dcd.line.add(F.has_net_name("DCD", level=F.has_net_name.Level.SUGGESTED))
        self.ri.line.add(F.has_net_name("RI", level=F.has_net_name.Level.SUGGESTED))
