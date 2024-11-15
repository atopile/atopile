# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.core.module import Module


class has_pcb_position_defined_relative(F.has_pcb_position.impl()):
    def __init__(self, position_relative: F.has_pcb_position.Point, to: Module) -> None:
        super().__init__()
        self.position_relative = position_relative
        self.to = to

    def get_position(self) -> F.has_pcb_position.Point:
        from faebryk.libs.geometry.basic import Geometry

        return Geometry.abs_pos(
            self.to.get_trait(F.has_pcb_position).get_position(), self.position_relative
        )
