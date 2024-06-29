# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass

from faebryk.core.core import (
    Module,
    Node,
)
from faebryk.core.util import get_all_nodes
from faebryk.exporters.pcb.kicad.layout.layout import Layout
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.library.has_pcb_position_defined_relative_to_parent import (
    has_pcb_position_defined_relative_to_parent,
)
from faebryk.libs.util import find

logger = logging.getLogger(__name__)


@dataclass
class SimpleLayout(Layout):
    @dataclass
    class SubLayout:
        mod_type: type[Module]
        position: has_pcb_position.Point
        sub_layout: "SimpleLayout | None" = None

    layouts: list[SubLayout]

    def apply(self, node: Node):
        """
        Tip: Make sure at least one parent of node has an absolute position defined
        """
        nodes = get_all_nodes(node)

        # Find node depth that exists in layout
        if not any([isinstance(node, layout.mod_type) for layout in self.layouts]):
            for child in nodes:
                self.apply(child)
            return

        # Find layout for the node
        sub_layout = find(
            self.layouts, lambda layout: isinstance(node, layout.mod_type)
        )

        # Set position of node to be relative to parent
        node.add_trait(has_pcb_position_defined_relative_to_parent(sub_layout.position))

        # Recurse
        if not sub_layout.sub_layout:
            return
        for child in nodes:
            sub_layout.sub_layout.apply(child)
