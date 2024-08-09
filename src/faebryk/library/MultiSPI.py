# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.libs.util import times


class MultiSPI(ModuleInterface):
    def __init__(self, data_lane_count: int) -> None:
        super().__init__()

        class IFS(ModuleInterface.IFS()):
            clk = ElectricLogic()
            data = times(data_lane_count, ElectricLogic)
            cs = ElectricLogic()

        self.IFs = IFS(self)

        class PARAMS(ModuleInterface.PARAMS()): ...

        self.PARAMs = PARAMS(self)
