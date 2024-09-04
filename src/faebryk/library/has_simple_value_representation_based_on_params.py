# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Callable

import faebryk.library._F as F
from faebryk.core.parameter import Parameter


class has_simple_value_representation_based_on_params(
    F.has_simple_value_representation.impl()
):
    def __init__[*P](
        self,
        params: tuple[*P],
        transformer: Callable[[*P], str],
    ) -> None:
        super().__init__()
        self.transformer = transformer
        assert all(isinstance(p, Parameter) for p in params)
        self.params = params

    def get_value(self) -> str:
        params_const = tuple(param.get_most_narrow() for param in self.params)
        return self.transformer(*params_const)
