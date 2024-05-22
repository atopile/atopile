# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.has_designator import has_designator


class has_designator_defined(has_designator.impl()):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value

    def get_designator(self) -> str:
        return self.value
