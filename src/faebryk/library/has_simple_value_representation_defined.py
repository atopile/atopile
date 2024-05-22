# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.has_simple_value_representation import (
    has_simple_value_representation,
)


class has_simple_value_representation_defined(has_simple_value_representation.impl()):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value
        assert value != ""

    def get_value(self) -> str:
        return self.value
