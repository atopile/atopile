# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class has_designator(fabll.Node):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value

    def get_designator(self) -> str:
        return self.value
