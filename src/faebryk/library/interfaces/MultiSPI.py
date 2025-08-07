# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.util import times


class MultiSPI(ModuleInterface):
    def __init__(self, data_lane_count: int) -> None:
        super().__init__()
        self._data_lane_count = data_lane_count

    clock: F.ElectricLogic
    chip_select: F.ElectricLogic

    @L.rt_field
    def data(self):
        return times(self._data_lane_count, F.ElectricLogic)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )
