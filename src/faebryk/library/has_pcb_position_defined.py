# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_pcb_position_defined(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    def __init__(self, position: F.has_pcb_position.Point) -> None:
        super().__init__()
        self.position = position

    def get_position(self) -> F.has_pcb_position.Point:
        return self.position
