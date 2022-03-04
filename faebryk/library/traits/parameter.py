# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
logger = logging.getLogger("library")

import typing
from faebryk.library.core import ParameterTrait

class is_representable_by_single_value(ParameterTrait):
    def __init__(self, value: typing.Any) -> None:
        super().__init__()
        self.value = value

    def get_single_representing_value(self):
        return self.value
