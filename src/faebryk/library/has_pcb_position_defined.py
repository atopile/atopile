# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.has_pcb_position import has_pcb_position


class has_pcb_position_defined(has_pcb_position.impl()):
    def __init__(self, position: has_pcb_position.Point) -> None:
        super().__init__()
        self.position = position

    def get_position(self) -> has_pcb_position.Point:
        return self.position
