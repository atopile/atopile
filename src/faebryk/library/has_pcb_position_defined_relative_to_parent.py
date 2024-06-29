# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.library.has_pcb_position import has_pcb_position

logger = logging.getLogger(__name__)


class has_pcb_position_defined_relative_to_parent(has_pcb_position.impl()):
    def __init__(self, position_relative: has_pcb_position.Point):
        super().__init__()
        self.position_relative = position_relative

    def get_position(self) -> has_pcb_position.Point:
        from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

        for parent, _ in reversed(self.get_obj().get_hierarchy()[:-1]):
            if parent.has_trait(has_pcb_position):
                pos = parent.get_trait(has_pcb_position).get_position()
                logger.debug(
                    f"Found parent position for: {self.get_obj().get_full_name()}:"
                    f"{pos} [{parent.get_full_name()}]"
                )
                return PCB_Transformer.Geometry.abs_pos(
                    pos,
                    self.position_relative,
                )
        raise Exception(
            f"Component of type {type(self.get_obj())} with relative to parent position"
            " has no (valid) parent"
        )
