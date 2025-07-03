# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto
from typing import TYPE_CHECKING, Sequence

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.geometry.basic import Geometry
from faebryk.libs.util import KeyErrorAmbiguous, KeyErrorNotFound, find

if TYPE_CHECKING:
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

logger = logging.getLogger(__name__)


class has_pcb_routing_strategy_greedy_direct_line(F.has_pcb_routing_strategy.impl()):
    class Topology(Enum):
        STAR = auto()
        DIRECT = auto()
        # CHAIN = auto()

    def __init__(
        self,
        topology: Topology = Topology.DIRECT,
        extra_mifs: Sequence[ModuleInterface] | None = None,
        extra_pads: Sequence[F.Pad] | None = None,
    ) -> None:
        super().__init__()
        self.topology = topology
        self.extra_mifs = extra_mifs or []
        self.extra_pads = extra_pads or []

    def calculate(self, transformer: "PCB_Transformer"):
        from faebryk.exporters.pcb.routing.util import (
            DEFAULT_TRACE_WIDTH,
            Path,
            Route,
            get_internal_nets_of_node,
            get_pads_pos_of_mifs,
            group_pads_that_are_connected_already,
        )

        node = self.obj
        nets = get_internal_nets_of_node(node)

        logger.debug(f"Routing {node} {'-' * 40}")
        # TODO avoid crossing pads
        # might make this very complex though

        def get_route_for_mifs_in_net(mifs) -> Route | None:
            pads = get_pads_pos_of_mifs(mifs + self.extra_mifs, self.extra_pads)

            unique_layers = {layer for pos in pads.values() for layer in pos[3]}
            try:
                layer = find(
                    unique_layers,
                    lambda layer: all(layer in pos[3] for pos in pads.values()),
                )
            except KeyErrorAmbiguous as e:
                layer = e.duplicates[0]
            except KeyErrorNotFound as e:
                raise NotImplementedError(
                    "Only support pads that share at least one layer"
                ) from e

            grouped_pads = group_pads_that_are_connected_already(pads)

            if len(grouped_pads) < 2:
                return None

            logger.debug(f"Routing pads: {pads}")

            def _get_pad_pos(pad: F.Pad):
                """
                overwrite layer set with the layer we chose to route on
                """
                x, y, r, _ = pads[pad]
                return x, y, r, layer

            def get_route_for_net_star():
                # filter pads that are already connected
                fpads = {
                    (pad := next(iter(pad_group))): _get_pad_pos(pad)
                    for pad_group in grouped_pads
                }

                center = Geometry.average([pos for _, pos in fpads.items()])

                path = Path()
                for _, pos in fpads.items():
                    path.add(Path.Line(DEFAULT_TRACE_WIDTH, layer, pos, center))

                return Route(pads=fpads.keys(), path=path)

            def get_route_for_direct():
                sets = [{_get_pad_pos(pad) for pad in group} for group in grouped_pads]

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
