# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import TYPE_CHECKING, Sequence

import faebryk.library._F as F
from faebryk.core.node import Node
from faebryk.exporters.pcb.routing.util import (
    Path,
    Route,
    get_internal_nets_of_node,
    get_pads_pos_of_mifs,
)

if TYPE_CHECKING:
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

logger = logging.getLogger(__name__)


class has_pcb_routing_strategy_manual(F.has_pcb_routing_strategy.impl()):
    def __init__(
        self,
        paths: Sequence[tuple[F.Net | Sequence[F.Electrical], Path]],
        relative_to: Node | None = None,
        absolute: bool = False,
    ):
        super().__init__()

        self.paths_rel = paths
        self.relative_to = relative_to
        self.absolute = absolute

    def calculate(self, transformer: "PCB_Transformer"):
        node = self.obj
        nets = get_internal_nets_of_node(node)

        relative_to = (self.relative_to or self.obj) if not self.absolute else None

        if relative_to:
            pos = relative_to.get_parent_with_trait(F.has_pcb_position)[
                1
            ].get_position()
            for _, path in self.paths_rel:
                path.abs_pos(pos)

        def get_route_for_mifs_in_net(mifs, path):
            pads = get_pads_pos_of_mifs(mifs)
            # Nothing we have can do with the groups because we don't know
            #  which parts of the path are specifically for those pads
            # pad_groups = group_pads_that_are_connected_already(pads)

            return Route(pads=pads, path=path)

        return [
            route
            for net_or_mifs, path in self.paths_rel
            if (
                route := get_route_for_mifs_in_net(
                    nets[net_or_mifs]
                    if isinstance(net_or_mifs, F.Net)
                    else net_or_mifs,
                    path,
                )
            )
        ]
