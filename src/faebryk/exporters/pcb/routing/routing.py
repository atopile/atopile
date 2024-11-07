# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
TODO: Explain file
"""

import logging
from itertools import groupby

import networkx as nx

import faebryk.library._F as F
from faebryk.core.graph import GraphFunctions
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.routing.grid import (
    Coord,
    Graph,
    Grid,
    GridInvalidVertexException,
    OutCoord,
)
from faebryk.libs.geometry.basic import Geometry
from faebryk.libs.kicad.pcb import Footprint, GR_Circle, GR_Line, GR_Rect, Pad

# logging settings
logger = logging.getLogger(__name__)

PAD_VIAS = False
BURIED_VIAS = True

if not BURIED_VIAS:
    raise NotImplementedError()


def out_to_pcb(c: OutCoord) -> tuple[float, float]:
    return round(c, 3).as_tuple()[:2]


class PCB_Router:
    class RPad:
        def __init__(self, pad: Pad, fp: Footprint, router: "PCB_Router") -> None:
            self.pad = pad
            self.fp = fp
            self.router = router

            self.layers = router.transformer.get_copper_layers_pad(pad)

            if len(self.layers) not in [len(router.copper_layers), 1]:
                raise NotImplementedError(
                    "No support for pads with multiple layers but not all layers"
                )

            self.pos = [
                Coord(
                    *Geometry.abs_pos(fp.at.coord, pad.at.coord),
                    router.copper_layers[layer],
                )
                for layer in self.layers
            ]

    def __init__(self, transformer: PCB_Transformer) -> None:
        self.transformer = transformer

        self.copper_layers = {
            layer: i for i, layer in enumerate(self.transformer.get_copper_layers())
        }
        logger.info(f"{len(self.copper_layers)} layer board: {self.copper_layers}")

        self.pads = {
            pad: self.RPad(pad, fp, self)
            for fp in self.transformer.pcb.footprints
            for pad in fp.pads
            if len(transformer.get_copper_layers_pad(pad)) >= 1
        }

        pad_coords = {p for pad in self.pads.values() for p in pad.pos}

        # TODO give some space around pads for routing
        pad_rect = tuple(
            Coord(
                *(f(c[i] for c in pad_coords) for i in range(3)),
            )
            for f in (min, max)
        )
        # use all available layers
        rect = (
            pad_rect[0],
            type(pad_rect[1])(*pad_rect[1][:2], len(self.copper_layers) - 1),
        )

        pcb_edge = transformer.get_edge()
        pcb_edge_layers = [[OutCoord(*c, -1) for c in pcb_edge]] if pcb_edge else []

        self.edge = pcb_edge  # just for debug
        self.grid = Grid(rect, inclusion_poly=pcb_edge_layers)

    def draw_grid(self, graph: Graph):
        grid_points = [self.grid._project_out(gc) for gc in graph.vertices()]

        GRID_START_LAYER = 8

        for c in grid_points:
            self.transformer.insert_geo(
                GR_Circle.factory(
                    center=out_to_pcb(c),
                    end=out_to_pcb(c + OutCoord(self.grid.resolution.x / 4, 0, 0)),
                    stroke=GR_Circle.Stroke.factory(0, "default"),
                    fill_type="solid",
                    layer=f"User.{GRID_START_LAYER-int(c.z)}",
                    uuid=self.transformer.gen_uuid(),
                )
            )

    def draw_circle(self, coord: OutCoord, size=0.5, layer="User.9"):
        self.transformer.insert_geo(
            GR_Circle.factory(
                center=out_to_pcb(coord),
                end=out_to_pcb(coord + OutCoord(size, 0, 0)),
                stroke=GR_Circle.Stroke.factory(0.1, "default"),
                fill_type="none",
                layer=layer,
                uuid=self.transformer.gen_uuid(),
            )
        )

    def route_all(self):
        nets = GraphFunctions(self.transformer.graph).nodes_of_type(F.Net)

        # TODO add net picking heuristic
        for net in nets:
            netname = net.get_trait(F.has_overriden_name).get_name()
            try:
                self.route_net(net)
            except GridInvalidVertexException as e:
                coord = e.get_coord(self.grid)
                logger.error(f"Failed routing {netname}: {e}: {coord}")
                self.draw_circle(coord)
                self.draw_grid(e.graph)
                return
            except Exception as e:
                logger.error(
                    f"Could not route: {netname}: {type(e).__name__}({e.args})"
                )

        # self.grid.draw()

    def get_pad_exclusion_zones(self, pad: RPad):
        def layer(p):
            middle = p
            size = Coord(*pad.pad.size, 0)

            origin = middle - size / 2
            return origin, origin + size

        return [layer(p) for p in pad.pos]

    def route_net(self, net: F.Net):
        transformer = self.transformer

        assert net is not None
        pcb_net = transformer.get_net(net)
        net_name = net.get_trait(F.has_overriden_name).get_name()
        mifs = net.get_connected_interfaces()

        # get pads
        _pads: dict[Pad, Footprint] = {}
        for mif in mifs:
            try:
                kfp, pad, node = transformer.get_pad(mif)
            except Exception:
                continue

            _pads[pad] = kfp

        pads = {self.pads[pad] for pad in _pads}

        if len(pads) < 2:
            return

        # exclusion
        exclusion_pads = set(self.pads.values()).difference(pads)
        exclusion_rects = {
            r for pad in exclusion_pads for r in self.get_pad_exclusion_zones(pad)
        }
        layer_exclusion_rects = {
            r
            for pad in pads
            if len(pad.pos) == 1
            for r in self.get_pad_exclusion_zones(pad)
        }

        # find path
        pad_pos = {p: pad for pad in pads for p in pad.pos}
        nodes = set(pad_pos.keys())
        try:
            path = self.grid.find_path(
                list(nodes),
                exclusion_rects=exclusion_rects,
                layer_exclusion_rects=layer_exclusion_rects,
            )
        except nx.NetworkXNoPath as e:
            # TODO
            logger.warning(
                f"Can't route Net({net_name}): Could not find path: {e.args[0]}"
            )
            return

        logger.info(f"Found path {path}")

        layer_names = {v: k for k, v in self.copper_layers.items()}
        layered_path = ((k, list(v)) for k, v in groupby(path, lambda c: c[2]))

        for i, (layer, layer_path) in enumerate(layered_path):
            layer_name = layer_names[layer]
            switch_point = layer_path[0]

            # if point in nodes then through hole pad
            if i > 0 and switch_point not in nodes:
                transformer.insert_via(
                    coord=out_to_pcb(switch_point),
                    net=pcb_net.number,
                    size_drill=(0.45, 0.25),
                )

            # build track
            transformer.insert_track(
                net_id=pcb_net.number,
                points=[round(c, 2).as_tuple()[:2] for c in layer_path],
                width=0.1,
                layer=layer_name,
                arc=False,
            )

    def route_if_net(self, mif: F.Electrical):
        net = mif.get_net()
        assert net is not None
        self.route_net(net)

    def mark_exclusion(self):
        pads = self.pads
        logger.info("Marking exclusion")

        for pad in pads.values():
            zones = self.get_pad_exclusion_zones(pad)

            q_rect = tuple(self.grid.reproject(x) for zone in zones for x in zone)

            layers = pad.layers

            for layer in layers:
                self.transformer.insert(
                    GR_Rect.factory(
                        *(out_to_pcb(c) for c in q_rect),
                        stroke=GR_Rect.Stroke.factory(0.1, "default"),
                        fill_type="none",
                        layer=f"User.{self.copper_layers[layer] + 1}",
                        uuid=self.transformer.gen_uuid(),
                    )
                )

        for c1, c2 in zip(self.edge[:-1], self.edge[1:]):
            self.transformer.insert(
                GR_Line.factory(
                    *(out_to_pcb(OutCoord(*c, 0)) for c in (c1, c2)),
                    stroke=GR_Line.Stroke.factory(0.1, "default"),
                    layer="User.9",
                    uuid=self.transformer.gen_uuid(),
                )
            )

        # if self.grid.resolution >= 0.25:
        # self.draw_grid(self.grid.G)
