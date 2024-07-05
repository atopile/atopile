# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto

from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.routing.util import (
    DEFAULT_TRACE_WIDTH,
    Path,
    Route,
    get_internal_nets_of_node,
    get_pads_pos_of_mifs,
    group_pads_that_are_connected_already,
)
from faebryk.library.has_pcb_routing_strategy import has_pcb_routing_strategy
from faebryk.libs.geometry.basic import Geometry

logger = logging.getLogger(__name__)


class has_pcb_routing_strategy_greedy_direct_line(has_pcb_routing_strategy.impl()):
    class Topology(Enum):
        STAR = auto()
        DIRECT = auto()
        # CHAIN = auto()

    def __init__(self, topology: Topology = Topology.DIRECT, priority: float = 0.0):
        super().__init__()
        self.topology = topology

    def calculate(self, transformer: PCB_Transformer):
        node = self.get_obj()
        nets = get_internal_nets_of_node(node)

        logger.debug(f"Routing {node} {'-'*40}")
        # TODO avoid crossing pads
        # might make this very complex though

        def get_route_for_mifs_in_net(mifs) -> Route | None:
            pads = get_pads_pos_of_mifs(mifs)

            layers = {pos[3] for pos in pads.values()}
            if len(layers) > 1:
                raise NotImplementedError()
            layer = next(iter(layers))

            if len(pads) < 2:
                return None

            logger.debug(f"Routing pads: {pads}")

            def get_route_for_net_star():
                # filter pads that are already connected
                fpads = {
                    (pad := next(iter(pad_group))): pads[pad]
                    for pad_group in group_pads_that_are_connected_already(pads)
                }

                center = Geometry.average([pos for _, pos in fpads.items()])

                path = Path()
                for _, pos in fpads.items():
                    path.add(Path.Line(DEFAULT_TRACE_WIDTH, layer, pos, center))

                return Route(pads=fpads.keys(), path=path)

            def get_route_for_direct():
                _sets = group_pads_that_are_connected_already(pads)
                sets = [{pads[pad] for pad in group} for group in _sets]

                path = Path()

                while len(sets) > 1:
                    # find closest pads
                    closest = min(
                        (
                            (set1, set2, Geometry.distance_euclid(p1, p2), [p1, p2])
                            for set1 in sets
                            for set2 in sets
                            for p1 in set1
                            for p2 in set2
                            if set1 != set2
                        ),
                        key=lambda t: t[2],
                    )

                    # merge closest pads
                    sets.remove(closest[0])
                    sets.remove(closest[1])
                    sets.append(closest[0].union(closest[1]))

                    path.add(
                        Path.Track(
                            width=DEFAULT_TRACE_WIDTH, layer=layer, points=closest[3]
                        )
                    )

                return Route(pads=pads.keys(), path=path)

            if self.topology == self.Topology.STAR:
                return get_route_for_net_star()
            elif self.topology == self.Topology.DIRECT:
                return get_route_for_direct()
            else:
                raise NotImplementedError

        return [
            route
            for net, mifs in nets.items()
            if net and (route := get_route_for_mifs_in_net(mifs))
        ]
