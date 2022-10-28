# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

logger = logging.getLogger("library")

import typing

from faebryk.library.traits.parameter import is_representable_by_single_value


class is_representable_by_single_value_defined(is_representable_by_single_value.impl()):
    def __init__(self, value: typing.Any) -> None:
        super().__init__()
        self.value = value

    def get_single_representing_value(self):
        return self.value
