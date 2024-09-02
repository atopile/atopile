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
