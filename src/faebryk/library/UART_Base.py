# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.TBD import TBD


class UART_Base(ModuleInterface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class IFS(ModuleInterface.IFS()):
            rx = ElectricLogic()
            tx = ElectricLogic()

        self.IFs = IFS(self)

        class PARAMS(ModuleInterface.PARAMS()):
            baud = TBD()

        self.PARAMs = PARAMS(self)

        ref = ElectricLogic.connect_all_module_references(self)
        self.add_trait(has_single_electric_reference_defined(ref))

    def _on_connect(self, other: "UART_Base"):
        super()._on_connect(other)

        self.PARAMs.baud.merge(other.PARAMs.baud)
