# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

logger = logging.getLogger("library")

from faebryk.library.traits.parameter import is_representable_by_single_value
from faebryk.library.core import Parameter
from faebryk.library.traits import *
from faebryk.libs.exceptions import FaebrykException
import typing


class Constant(Parameter):
    def __init__(self, value: typing.Any) -> None:
        super().__init__()
        self.value = value
        self.add_trait(is_representable_by_single_value(self.value))


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

        self.add_trait(is_representable_by_single_value(value_to_check))


class TBD(Parameter):
    def __init__(self) -> None:
        super().__init__()
