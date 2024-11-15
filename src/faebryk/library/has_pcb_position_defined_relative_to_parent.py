# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F

logger = logging.getLogger(__name__)


class has_pcb_position_defined_relative_to_parent(F.has_pcb_position.impl()):
    def __init__(self, position_relative: F.has_pcb_position.Point):
        super().__init__()
        self.position_relative = position_relative

    def get_position(self) -> F.has_pcb_position.Point:
        from faebryk.libs.geometry.basic import Geometry

        for parent, _ in reversed(self.obj.get_hierarchy()[:-1]):
            if parent.has_trait(F.has_pcb_position):
                pos = parent.get_trait(F.has_pcb_position).get_position()
                logger.debug(
                    f"Found parent position for: {self.obj.get_full_name()}:"
                    f"{pos} [{parent.get_full_name()}]"
                )
                return Geometry.abs_pos(
                    pos,
                    self.position_relative,
                )
        raise Exception(
            f"Component of type {type(self.obj)} with relative to parent position"
            " has no (valid) parent"
        )
