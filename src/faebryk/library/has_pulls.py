# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_pulls(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    up_ = F.Collections.Pointer.MakeChild()
    down_ = F.Collections.Pointer.MakeChild()

    def get_pulls(self) -> tuple[F.Resistor | None, F.Resistor | None]:
        up_node = self.up_.get().deref()
        down_node = self.down_.get().deref()
        up = F.Resistor.bind_instance(up_node.instance) if up_node is not None else None
        down = (
            F.Resistor.bind_instance(down_node.instance)
            if down_node is not None
            else None
        )
        return up, down

    def setup(self, up: F.Resistor | None, down: F.Resistor | None) -> Self:
        if up is not None:
            self.up_.get().point(up)
        if down is not None:
            self.down_.get().point(down)
        return self
