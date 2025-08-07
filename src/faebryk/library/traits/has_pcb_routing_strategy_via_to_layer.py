# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.routing.util import (
    DEFAULT_TRACE_WIDTH,
    DEFAULT_VIA_SIZE_DRILL,
    Path,
    Route,
    get_internal_nets_of_node,
    get_pads_pos_of_mifs,
    get_routes_of_pad,
    group_pads_that_are_connected_already,
)
from faebryk.libs.geometry.basic import Geometry

logger = logging.getLogger(__name__)


class has_pcb_routing_strategy_via_to_layer(F.has_pcb_routing_strategy.impl()):
    def __init__(self, layer: str, vec: Geometry.Point2D):
        super().__init__()
        self.vec = vec
        self.layer = layer

    def calculate(self, transformer: PCB_Transformer):
        layer = transformer.get_layer_id(self.layer)

        node = self.obj
        nets = get_internal_nets_of_node(node)

        logger.debug(f"Routing {node} {'-' * 40}")

        def get_route_for_net(net: F.Net, mifs) -> Route | None:
            pads = get_pads_pos_of_mifs(mifs)
            pad_groups = group_pads_that_are_connected_already(pads)

            # Get pad representatives in groups
            # Filter groups that already are connected to VIAs
            pads_filtered = {
                pad: pads[pad]
                for group in pad_groups
                if (pad := next(iter(group)))
                and not any(
                    isinstance(path_elem, Path.Via)
                    for r in get_routes_of_pad(pad)
                    for path_elem in r.path.path
                )
            }

            logger.debug(f"Routing net {net} with pads: {pads_filtered}")

            path = Path()

            for _, pos in pads_filtered.items():
                # No need to add via if on same layer already
                pad_layer = pos[3]
                if pad_layer == layer:
                    continue
                via_pos: Geometry.Point = Geometry.add_points(pos, self.vec)
                path.add(Path.Via(via_pos, size_drill=DEFAULT_VIA_SIZE_DRILL))
                path.add(Path.Line(DEFAULT_TRACE_WIDTH, pad_layer, pos, via_pos))

            path.add(
                Path.Zone(
                    layer,
                    transformer.get_net_obj_bbox(
                        transformer.get_net(net),
                        layer=self.layer,
                        tolerance=Geometry.distance_euclid((0, 0, 0, 0), self.vec),
                    ),
                )
            )

            return Route(pads, path)

        return [
            route
            for net, mifs in nets.items()
            if net and (route := get_route_for_net(net, mifs))
        ]
