# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Node
from faebryk.core.util import get_parent_with_trait
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.routing.util import (
    Path,
    Route,
    get_internal_nets_of_node,
    get_pads_pos_of_mifs,
)
from faebryk.library.Electrical import Electrical
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.library.has_pcb_routing_strategy import has_pcb_routing_strategy
from faebryk.library.Net import Net

logger = logging.getLogger(__name__)


class has_pcb_routing_strategy_manual(has_pcb_routing_strategy.impl()):
    def __init__(
        self,
        paths: list[tuple[Net | list[Electrical], Path]],
        relative_to: Node | None = None,
        absolute: bool = False,
    ):
        super().__init__()

        self.paths_rel = paths
        self.relative_to = relative_to
        self.absolute = absolute

    def calculate(self, transformer: PCB_Transformer):
        node = self.get_obj()
        nets = get_internal_nets_of_node(node)

        relative_to = (
            (self.relative_to or self.get_obj()) if not self.absolute else None
        )

        if relative_to:
            pos = get_parent_with_trait(relative_to, has_pcb_position)[1].get_position()
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
                    nets[net_or_mifs] if isinstance(net_or_mifs, Net) else net_or_mifs,
                    path,
                )
            )
        ]
