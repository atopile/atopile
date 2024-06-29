# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.core.core import Module
from faebryk.library.has_pcb_position import has_pcb_position


class has_pcb_position_defined_relative(has_pcb_position.impl()):
    def __init__(self, position_relative: has_pcb_position.Point, to: Module) -> None:
        super().__init__()
        self.position_relative = position_relative
        self.to = to

    def get_position(self) -> has_pcb_position.Point:
        from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

        return PCB_Transformer.Geometry.abs_pos(
            self.to.get_trait(has_pcb_position).get_position(), self.position_relative
        )
