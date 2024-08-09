# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module, ModuleInterface
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.SWD import SWD


class SWDConnector(Module):
    def __init__(self) -> None:
        super().__init__()

        class IFS(ModuleInterface.IFS()):
            swd = SWD()
            gnd_detect = ElectricLogic()
            vcc = ElectricPower()

        self.IFs = IFS(self)

        class PARAMS(ModuleInterface.PARAMS()): ...

        self.PARAMs = PARAMS(self)

        self.add_trait(has_designator_prefix_defined("J"))

        self.add_trait(
            has_single_electric_reference_defined(
                ElectricLogic.connect_all_module_references(self)
            )
        )
