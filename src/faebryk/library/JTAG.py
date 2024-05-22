# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)


class JTAG(ModuleInterface):
    def __init__(self) -> None:
        super().__init__()

        class IFS(ModuleInterface.IFS()):
            dbgrq = ElectricLogic()
            tdo = ElectricLogic()
            tdi = ElectricLogic()
            tms = ElectricLogic()
            tck = ElectricLogic()
            n_trst = ElectricLogic()
            n_reset = ElectricLogic()
            vtref = Electrical()

        self.IFs = IFS(self)

        ref = ElectricLogic.connect_all_module_references(self)
        self.add_trait(has_single_electric_reference_defined(ref))
