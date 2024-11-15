# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class has_simple_value_representation_defined(F.has_simple_value_representation.impl()):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value
        assert value != ""

    def get_value(self) -> str:
        return self.value
