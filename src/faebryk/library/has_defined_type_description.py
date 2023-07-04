# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.has_type_description import has_type_description


class has_defined_type_description(has_type_description.impl()):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value

    def get_type_description(self) -> str:
        return self.value
