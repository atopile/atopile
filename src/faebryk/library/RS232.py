# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module, ModuleInterface
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)


class RS232(ModuleInterface):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()):
            tx = ElectricLogic()
            rx = ElectricLogic()

        self.NODEs = _NODEs(self)

        ref = ElectricLogic.connect_all_module_references(self)
        self.add_trait(has_single_electric_reference_defined(ref))
