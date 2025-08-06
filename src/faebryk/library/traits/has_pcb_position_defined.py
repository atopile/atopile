# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class has_pcb_position_defined(F.has_pcb_position.impl()):
    def __init__(self, position: F.has_pcb_position.Point) -> None:
        super().__init__()
        self.position = position

    def get_position(self) -> F.has_pcb_position.Point:
        return self.position
