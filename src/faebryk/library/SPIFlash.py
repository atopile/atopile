# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module, ModuleInterface
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.MultiSPI import MultiSPI
from faebryk.library.TBD import TBD
from faebryk.libs.units import Quantity


class SPIFlash(Module):
    def __init__(self) -> None:
        super().__init__()

        class IFS(ModuleInterface.IFS()):
            power = ElectricPower()
            spi = MultiSPI()

        self.IFs = IFS(self)

        class PARAMS(ModuleInterface.PARAMS()):
            memory_size = TBD[Quantity]()

        self.PARAMs = PARAMS(self)

        self.add_trait(has_designator_prefix_defined("U"))
