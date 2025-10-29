# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_simple_value_representation_defined(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value
        assert value != ""

    def get_value(self) -> str:
        return self.value
