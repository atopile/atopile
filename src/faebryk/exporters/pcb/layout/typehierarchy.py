# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass

from faebryk.core.core import (
    Module,
    Node,
)
from faebryk.core.util import get_node_direct_children
from faebryk.exporters.pcb.layout.layout import Layout
from faebryk.libs.util import find_or, flatten, groupby

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=True)
class LayoutTypeHierarchy(Layout):
    @dataclass(frozen=True, eq=True)
    class Level:
        mod_type: type[Module]
        layout: Layout
        children_layout: Layout | None = None

    layouts: list[Level]

    def apply(self, *node: Node):
        """
        Tip: Make sure at least one parent of node has an absolute position defined
        """

        # Find the layout for each node and group by matched level
        levels = groupby(
            {
                n: find_or(
                    self.layouts,
                    lambda layout: isinstance(n, layout.mod_type),
                    default=None,
                )
                for n in node
            }.items(),
            lambda t: t[1],
        )

        for level, nodes_tuple in levels.items():
            nodes = [n for n, _ in nodes_tuple]

            direct_children = flatten(get_node_direct_children(n) for n in nodes)

            if level is None:
                self.apply(*direct_children)
                continue

            level.layout.apply(*nodes)

            if not level.children_layout:
                continue

            level.children_layout.apply()
