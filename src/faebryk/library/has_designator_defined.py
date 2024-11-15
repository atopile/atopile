# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class has_designator_defined(F.has_designator.impl()):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value

    def get_designator(self) -> str:
        return self.value
