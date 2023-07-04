# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.differential_pair import DifferentialPair
from faebryk.library.ElectricPower import ElectricPower


class USB2_0(ModuleInterface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class _NODEs(ModuleInterface.NODES()):
            d = DifferentialPair()
            buspower = ElectricPower()

        self.NODEs = _NODEs(self)
