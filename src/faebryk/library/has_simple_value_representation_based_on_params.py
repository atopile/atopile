# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Callable, Sequence

from faebryk.core.core import Parameter
from faebryk.library.has_simple_value_representation import (
    has_simple_value_representation,
)


class has_simple_value_representation_based_on_params(
    has_simple_value_representation.impl()
):
    def __init__(
        self,
        params: Sequence[Parameter],
        transformer: Callable[[Sequence[Parameter]], str],
    ) -> None:
        super().__init__()
        self.transformer = transformer
        self.params = params

    def get_value(self) -> str:
        params_const = tuple(param.get_most_narrow() for param in self.params)
        return self.transformer(params_const)
