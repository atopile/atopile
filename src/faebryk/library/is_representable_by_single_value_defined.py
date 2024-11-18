# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import typing

import faebryk.library._F as F


class is_representable_by_single_value_defined(
    F.is_representable_by_single_value.impl()
):
    def __init__(self, value: typing.Any) -> None:
        super().__init__()
        self.value = value

    def get_single_representing_value(self):
        return self.value
