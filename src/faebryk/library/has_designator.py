# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.module import Module


class has_designator(Module.TraitT.decless()):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value

    def get_designator(self) -> str:
        return self.value
