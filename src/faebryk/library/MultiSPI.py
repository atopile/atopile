# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.Electrical import Electrical
from faebryk.libs.util import times


class MultiSPI(ModuleInterface):
    def __init__(self, data_lane_count: int) -> None:
        super().__init__()

        class IFS(ModuleInterface.IFS()):
            data = times(data_lane_count, Electrical)
            sclk = Electrical()
            ss_n = Electrical()
            gnd = Electrical()

        self.IFs = IFS(self)
