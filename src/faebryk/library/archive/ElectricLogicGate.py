# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.libs.library import L
from faebryk.libs.util import times


class ElectricLogicGate(F.LogicGate):
    @L.rt_field
    def inputs(self):
        return times(self._input_cnt, F.ElectricLogic)

    @L.rt_field
    def outputs(self):
        return times(self._output_cnt, F.ElectricLogic)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )
