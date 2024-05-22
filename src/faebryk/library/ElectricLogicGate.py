# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import TypeVar

from faebryk.core.core import Module, TraitImpl
from faebryk.core.util import specialize_interface
from faebryk.library.Constant import Constant
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.Logic import Logic
from faebryk.library.LogicGate import LogicGate
from faebryk.libs.util import times

T = TypeVar("T", bound=Logic)


class ElectricLogicGate(LogicGate):
    def __init__(
        self, input_cnt: Constant[int], output_cnt: Constant[int], *functions: TraitImpl
    ) -> None:
        super().__init__(input_cnt, output_cnt, *functions)

        self.IFs_logic = self.IFs

        class IFS(Module.IFS()):
            inputs = times(input_cnt, ElectricLogic)
            outputs = times(output_cnt, ElectricLogic)

        self.IFs = IFS(self)

        for in_if_l, in_if_el in zip(self.IFs_logic.inputs, self.IFs.inputs):
            specialize_interface(in_if_l, in_if_el)
        for out_if_l, out_if_el in zip(self.IFs_logic.outputs, self.IFs.outputs):
            specialize_interface(out_if_l, out_if_el)

        self.add_trait(
            has_single_electric_reference_defined(
                ElectricLogic.connect_all_module_references(self)
            )
        )
