# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.trait import TraitImpl
from faebryk.libs.library import L
from faebryk.libs.util import times


class ElectricLogicGate(F.LogicGate):
    def __init__(
        self,
        input_cnt: int,
        output_cnt: int,
        *functions: TraitImpl,
    ) -> None:
        self.input_cnt = input_cnt
        self.output_cnt = output_cnt
        super().__init__(input_cnt, output_cnt, *functions)

    def __preinit__(self):
        self_logic = self

        for in_if_l, in_if_el in zip(self_logic.inputs, self.inputs):
            in_if_l.specialize(in_if_el)
        for out_if_l, out_if_el in zip(self_logic.outputs, self.outputs):
            out_if_l.specialize(out_if_el)

    @L.rt_field
    def inputs(self):
        return times(self.input_cnt, F.ElectricLogic)

    @L.rt_field
    def outputs(self):
        return times(self.output_cnt, F.ElectricLogic)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )
