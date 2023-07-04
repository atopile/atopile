# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.Electrical import Electrical
from faebryk.library.Power import Power


class ElectricPower(Power):
    def __init__(self) -> None:
        super().__init__()

        class NODES(Power.NODES()):
            hv = Electrical()
            lv = Electrical()

        self.NODEs = NODES(self)

    def _connect(self, other: ModuleInterface) -> ModuleInterface:
        if isinstance(other, type(self)):
            self.NODEs.hv.connect(other.NODEs.hv)
            self.NODEs.lv.connect(other.NODEs.lv)
        return super()._connect(other)
