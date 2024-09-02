# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass

from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node
from faebryk.exporters.pcb.layout.layout import Layout
from faebryk.libs.util import NotNone, find_or, groupby

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=True)
class LayoutTypeHierarchy(Layout):
    @dataclass(frozen=True, eq=True)
    class Level:
        mod_type: type[Module] | tuple[type[Module], ...]
        layout: Layout
        children_layout: Layout | None = None

    layouts: list[Level]

    def apply(self, *node: Node):
        """
        Tip: Make sure at least one parent of node has an absolute position defined
        """

        # Find the layout for each node (isinstance mod_type) and group by matched level
        levels = groupby(
            {
                n: find_or(
                    self.layouts,
                    lambda layout: isinstance(n, NotNone(layout).mod_type),
                    default=None,
                )
                for n in node
            }.items(),
            lambda t: t[1],
        )

        logger.debug(f"Applying to {node}")

        for level, nodes_tuple in levels.items():
            nodes = [n for n, _ in nodes_tuple]

            direct_children = {
                c
                for n in nodes
                for c in n.get_children(
                    direct_only=True, types=(Module, ModuleInterface)
                )
            }
            logger.debug(
                f"Level: {level.mod_type if level else None},"
                f" Children: {direct_children}"
            )

            # No type match, search for children instead
            if level is None:
                self.apply(*direct_children)
                continue

            level.layout.apply(*nodes)

            if not level.children_layout:
                continue

            level.children_layout.apply(*direct_children)

    def __hash__(self):
        return sum(map(hash, self.layouts))
