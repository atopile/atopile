# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Callable

from faebryk.core.core import Parameter
from faebryk.library.Constant import Constant
from faebryk.library.has_simple_value_representation import (
    has_simple_value_representation,
)


class has_simple_value_representation_based_on_param(
    has_simple_value_representation.impl()
):
    def __init__(
        self, param: Parameter, transformer: Callable[[Constant], str]
    ) -> None:
        super().__init__()
        self.param = param
        self.transformer = transformer

    def get_value(self) -> str:
        param_const = self.param.get_most_narrow()
        assert isinstance(param_const, Constant)
        return self.transformer(param_const)

    def is_implemented(self):
        return isinstance(self.param.get_most_narrow(), Constant)
