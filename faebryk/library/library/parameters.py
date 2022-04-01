# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

logger = logging.getLogger("library")

from faebryk.library.traits.parameter import is_representable_by_single_value
from faebryk.library.core import Parameter
from faebryk.library.traits import *
import typing


class Constant(Parameter):
    def __init__(self, value: typing.Any) -> None:
        super().__init__()
        self.value = value
        self.add_trait(is_representable_by_single_value(self.value))


class TBD(Parameter):
    def __init__(self) -> None:
        super().__init__()
