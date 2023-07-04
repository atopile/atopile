# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import typing

from faebryk.core.core import Parameter
from faebryk.library.is_representable_by_single_value_defined import (
    is_representable_by_single_value_defined,
)
from faebryk.libs.exceptions import FaebrykException


class Range(Parameter):
    def __init__(self, value_min: typing.Any, value_max: typing.Any) -> None:
        super().__init__()
        self.min = value_min
        self.max = value_max

    def pick(self, value_to_check: typing.Any):
        if not self.min <= value_to_check <= self.max:
            raise FaebrykException(
                f"Value not in range: {value_to_check} not in [{self.min},{self.max}]"
            )
        self.add_trait(is_representable_by_single_value_defined(value_to_check))
