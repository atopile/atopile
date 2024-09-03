# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from typing import TYPE_CHECKING

import faebryk.library._F as F
from faebryk.core.node import Node
from faebryk.core.trait import TraitImpl

if TYPE_CHECKING:
    from faebryk.library.Pad import Pad


class has_linked_pad_defined(F.has_linked_pad.impl()):
    def __init__(self, pad: "Pad") -> None:
        super().__init__()
        self.pads = {pad}

    def get_pads(self) -> set["Pad"]:
        return self.pads

    def handle_duplicate(self, other: TraitImpl, node: Node) -> bool:
        if not isinstance(other, has_linked_pad_defined):
            return super().handle_duplicate(other, node)

        other.pads.update(self.pads)
        return False
