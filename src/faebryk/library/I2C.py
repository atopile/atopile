# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.Resistor import Resistor


class I2C(ModuleInterface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class NODES(ModuleInterface.NODES()):
            scl = ElectricLogic()
            sda = ElectricLogic()

        self.NODEs = NODES(self)

        ref = ElectricLogic.connect_all_module_references(self)
        self.add_trait(has_single_electric_reference_defined(ref))

    def terminate(self, resistors: tuple[Resistor, Resistor]):
        # TODO: https://www.ti.com/lit/an/slva689/slva689.pdf

        self.NODEs.sda.pull_up(resistors[0])
        self.NODEs.scl.pull_up(resistors[1])
