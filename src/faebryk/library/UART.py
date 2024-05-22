# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.Electrical import Electrical
from faebryk.library.UART_Base import UART_Base


class UART(ModuleInterface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class IFS(super().IFS()):
            base_uart = UART_Base()
            rts = Electrical()
            cts = Electrical()
            dtr = Electrical()
            dsr = Electrical()

        self.IFs = IFS(self)
