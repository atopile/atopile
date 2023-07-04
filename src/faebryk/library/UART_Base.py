# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.Electrical import Electrical


class UART_Base(ModuleInterface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class NODES(ModuleInterface.NODES()):
            rx = Electrical()
            tx = Electrical()
            gnd = Electrical()

        self.NODEs = UART_Base.NODES(self)
