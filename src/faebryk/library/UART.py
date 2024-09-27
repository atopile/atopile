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
