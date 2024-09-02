# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Callable

import faebryk.library._F as F
from faebryk.core.parameter import Parameter


class has_simple_value_representation_based_on_param(
    F.has_simple_value_representation.impl()
):
    def __init__(
        self, param: Parameter, transformer: Callable[[F.Constant], str]
    ) -> None:
        super().__init__()
        self.param = param
        self.transformer = transformer

    def get_value(self) -> str:
        param_const = self.param.get_most_narrow()
        assert isinstance(param_const, F.Constant)
        return self.transformer(param_const)

    def is_implemented(self):
        return isinstance(self.param.get_most_narrow(), F.Constant)
