# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Callable

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_simple_value_representation_based_on_params(fabll.Node):
    def __init__[*P](
        self,
        params: tuple[*P],
        transformer: Callable[[*P], str],
    ) -> None:
        super().__init__()
        self.transformer = transformer
        assert all(isinstance(p, fabll.Parameter) for p in params)
        self.params = params

    # TODO make this more useful
    def get_value(self) -> str:
        return self.transformer(*self.params)
