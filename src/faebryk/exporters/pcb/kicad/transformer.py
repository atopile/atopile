# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import pprint
import re
import subprocess
from abc import abstractmethod
from dataclasses import fields
from enum import Enum, auto
from itertools import pairwise
from typing import Any, Callable, Iterable, List, Optional, Sequence, TypeVar

import numpy as np
from deprecated import deprecated
from shapely import Polygon

import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node
from faebryk.libs.exceptions import DeprecatedException, UserException, downgrade
from faebryk.libs.geometry.basic import Geometry
from faebryk.libs.kicad.fileformats import (
    UUID,
    C_arc,
    C_circle,
    C_effects,
    C_footprint,
    C_fp_text,
    C_kicad_pcb_file,
    C_line,
    C_polygon,
    C_rect,
    C_stroke,
    C_text,
    C_text_layer,
    C_wh,
    C_xy,
    C_xyr,
    C_xyz,
    E_fill,
)
from faebryk.libs.kicad.fileformats import (
    gen_uuid as _gen_uuid,
)
from faebryk.libs.kicad.fileformats_common import C_pts
from faebryk.libs.sexp.dataclass_sexp import dataclass_dfs
from faebryk.libs.util import (
    KeyErrorNotFound,
    cast_assert,
    find,
    get_key,
    hash_string,
)

logger = logging.getLogger(__name__)


PCB = C_kicad_pcb_file.C_kicad_pcb
Footprint = PCB.C_pcb_footprint
Pad = Footprint.C_pad
Net = PCB.C_net

# TODO remove
GR_Line = C_line
GR_Text = C_text
Font = C_effects.C_font
Zone = PCB.C_zone
Arc = C_arc
Rect = C_rect
Via = PCB.C_via
Line = C_line

Geom = C_line | C_arc | C_rect | C_circle

Point = Geometry.Point
Point2D = Geometry.Point2D

Justify = C_effects.C_justify.E_justify
Alignment = tuple[Justify, Justify, Justify]
Alignment_Default = (
    Justify.center_horizontal,
    Justify.center_vertical,
    Justify.normal,
)


def gen_uuid(mark: str = "") -> UUID:
    return _gen_uuid(mark)


def is_marked(uuid: UUID, mark: str):
    suffix = mark.encode().hex()
    return uuid.replace("-", "").endswith(suffix)


T = TypeVar("T", C_xy, C_xyz, C_xyr)
T2 = TypeVar("T2", C_xy, C_xyz, C_xyr)


def round_coord(coord: T, ndigits=2) -> T:
    fs = fields(coord)
    return type(coord)(
        **{f.name: round(getattr(coord, f.name), ndigits=ndigits) for f in fs}
    )


def round_line(line: tuple[Point2D, Point2D], ndigits=2):
    return per_point(line, lambda c: round_point(c, ndigits))


P = TypeVar("P", Point, Point2D)


def round_point(point: P, ndigits=2) -> P:
    return tuple(round(c, ndigits) for c in point)  # type: ignore


def coord_to_point(coord: T) -> Point:
    return tuple(getattr(coord, f.name) for f in fields(coord))


def coord_to_point2d(coord: T) -> Point2D:
    return coord.x, coord.y


def point2d_to_coord(point: Point2D) -> C_xy:
    return C_xy(x=point[0], y=point[1])


def abs_pos(origin: T, vector: T2):
    return Geometry.abs_pos(coord_to_point(origin), coord_to_point(vector))


def abs_pos2d(origin: T, vector: T2) -> Point2D:
    return Geometry.as2d(
        Geometry.abs_pos(coord_to_point2d(origin), coord_to_point2d(vector))
    )


def per_point[R](
    line: tuple[Point2D, Point2D], func: Callable[[Point2D], R]
) -> tuple[R, R]:
    return func(line[0]), func(line[1])


def get_all_geo_containers(obj: PCB | Footprint) -> list[Sequence[Geom]]:
    if isinstance(obj, C_kicad_pcb_file.C_kicad_pcb):
        return [obj.gr_lines, obj.gr_arcs, obj.gr_circles, obj.gr_rects]
    elif isinstance(obj, Footprint):
        return [obj.fp_lines, obj.fp_arcs, obj.fp_circles, obj.fp_rects]

    raise TypeError()


def get_all_geos(obj: PCB | Footprint) -> list[Geom]:
    candidates = get_all_geo_containers(obj)

    return [geo for geos in candidates for geo in geos]


class PCB_Transformer:
    class has_linked_kicad_footprint(Module.TraitT):
        """
        Module has footprint (which has kicad footprint) and that footprint
        is found in the current PCB file.
        """

        @abstractmethod
        def get_transformer(self) -> "PCB_Transformer": ...

        @abstractmethod
        def get_fp(self) -> Footprint: ...

    class has_linked_kicad_footprint_defined(has_linked_kicad_footprint.impl()):
        def __init__(self, fp: Footprint, transformer: "PCB_Transformer") -> None:
            super().__init__()
            self.fp = fp
            self.transformer = transformer

        def get_fp(self):
            return self.fp

        def get_transformer(self):
            return self.transformer

    class has_linked_kicad_pad(ModuleInterface.TraitT):
        @abstractmethod
        def get_pad(self) -> tuple[Footprint, list[Pad]]: ...

        @abstractmethod
        def get_transformer(self) -> "PCB_Transformer": ...

    class has_linked_kicad_pad_defined(has_linked_kicad_pad.impl()):
        def __init__(
            self, fp: Footprint, pad: list[Pad], transformer: "PCB_Transformer"
        ) -> None:
            super().__init__()
            self.fp = fp
            self.pad = pad
            self.transformer = transformer

        def get_pad(self):
            return self.fp, self.pad

        def get_transformer(self):
            return self.transformer

    def __init__(
        self, pcb: PCB, graph: Graph, app: Module, cleanup: bool = True
    ) -> None:
        self.pcb = pcb
        self.graph = graph
        self.app = app

        self.dimensions = None

        FONT_SCALE = 8
        FONT = Font(
            size=C_wh(1 / FONT_SCALE, 1 / FONT_SCALE),
            thickness=0.15 / FONT_SCALE,
        )
        self.font = FONT

        if cleanup:
            self.cleanup()
        self.attach()

    def attach(self, check_unattached: bool = False):
        for node, fp in PCB_Transformer.map_footprints(self.graph, self.pcb).items():
            self.bind_footprint(fp, node)

        if check_unattached:
            self.check_unattached()

    def check_unattached(self):
        unattached_nodes = {
            node
            for node, trait in GraphFunctions(self.graph).nodes_with_trait(
                F.has_footprint
            )
            if not trait.get_footprint().has_trait(F.has_kicad_footprint)
            and not node.has_trait(PCB_Transformer.has_linked_kicad_footprint)
        }
        if unattached_nodes:
            logger.error(f"Unattached: {pprint.pformat(unattached_nodes)}")
            raise UserException(
                f"Failed to attach {len(unattached_nodes)} node(s) to footprints"
            )

        # TODO: check other properties:
        # fp_ref = node.get_trait(F.has_overriden_name).get_name()
        # fp_name = g_fp.get_trait(F.has_kicad_footprint).get_kicad_footprint()
        # fp.propertys["atopile_address"] = node.get_full_name()

    @staticmethod
    def map_footprints(graph: Graph, pcb: PCB) -> dict[Node, Footprint]:
        """
        Attach as many nodes <> footprints as possible, and
        return the set of nodes that were missing footprints.
        """
        # Now, try to map between the footprints and the layout
        footprint_map: dict[Node, Footprint] = {}
        fps_by_atopile_addr = {
            f.propertys["atopile_address"].value: f
            for f in pcb.footprints
            if "atopile_address" in f.propertys
        }
        fps_by_path = {f.path: f for f in pcb.footprints if f.path is not None}

        # Also try nodes without footprints, because they might get them later
        nodes = GraphFunctions(graph).nodes_of_type(Module)
        for node in nodes:
            atopile_addr = node.get_full_name()
            hashed_addr = hash_string(atopile_addr)
            if fp := fps_by_atopile_addr.get(atopile_addr):
                footprint_map[node] = fp
            # TODO: @v0.4 remove this, it's a fallback for v0.2 designs
            elif fp := fps_by_path.get(f"/{hashed_addr}/{hashed_addr}"):
                with downgrade(DeprecatedException):
                    raise DeprecatedException(
                        f"{fp.name} is linked using v0.2 mechanism, "
                        "please save the design to update."
                    )
                footprint_map[node] = fp

        return footprint_map

    def bind_footprint(self, fp: Footprint, node: Node):
        node.add(self.has_linked_kicad_footprint_defined(fp, self))
        if not node.has_trait(F.has_footprint):
            return

        g_fp = node.get_trait(F.has_footprint).get_footprint()
        g_fp.add(self.has_linked_kicad_footprint_defined(fp, self))
        pin_names = g_fp.get_trait(F.has_kicad_footprint).get_pin_names()
        for fpad in g_fp.get_children(direct_only=True, types=ModuleInterface):
            pads = [
                pad
                for pad in fp.pads
                if pad.name == pin_names[cast_assert(F.Pad, fpad)]
            ]
            fpad.add(self.has_linked_kicad_pad_defined(fp, pads, self))

    def cleanup(self):
        # delete faebryk objects in pcb

        # find all objects with path_len 2 (direct children of a list in pcb)
        candidates = [o for o in dataclass_dfs(self.pcb) if len(o[1]) == 2]
        for obj, path, _ in candidates:
            if not self.is_marked(obj):
                continue

            # delete object by removing it from the container they are in
            holder = path[-1]
            if isinstance(holder, list):
                holder.remove(obj)
            elif isinstance(holder, dict):
                del holder[get_key(obj, holder)]

    @staticmethod
    def flipped[T](input_list: list[tuple[T, int]]) -> list[tuple[T, int]]:
        return [(x, (y + 180) % 360) for x, y in reversed(input_list)]

    @staticmethod
    def gen_uuid(mark: bool = False):
        return gen_uuid(mark="FBRK" if mark else "")

    @staticmethod
    def is_marked(obj) -> bool:
        if not hasattr(obj, "uuid"):
            return False
        return is_marked(obj.uuid, "FBRK")

    # Getter ---------------------------------------------------------------------------
    @staticmethod
    def get_fp(cmp: Node) -> Footprint:
        return cmp.get_trait(PCB_Transformer.has_linked_kicad_footprint).get_fp()

    def get_all_footprints(self) -> List[tuple[Module, Footprint]]:
        return [
            (cast_assert(Module, cmp), t.get_fp())
            for cmp, t in GraphFunctions(self.graph).nodes_with_trait(
                PCB_Transformer.has_linked_kicad_footprint
            )
        ]

    def get_net(self, net: F.Net) -> Net:
        nets = {pcb_net.name: pcb_net for pcb_net in self.pcb.nets}
        return nets[net.get_trait(F.has_overriden_name).get_name()]

    @staticmethod
    def get_footprint_silkscreen_bbox(fp: Footprint) -> None | tuple[Point2D, Point2D]:
        return PCB_Transformer.get_bounding_box(fp, {"F.SilkS", "B.SilkS"})

    @staticmethod
    def get_bounding_box(
        fp: Footprint,
        layers: str | set[str],
    ) -> None | tuple[Point2D, Point2D]:
        if isinstance(layers, str):
            layers = {layers}
        else:
            layers = set(layers)

        # TODO: make it properly generic
        if layers != {"F.SilkS", "B.SilkS"}:
            raise NotImplementedError(f"Unsupported layers: {layers}")

        content = [geo for geo in get_all_geos(fp) if geo.layer in layers]

        if not content:
            logger.warning(
                f"fp:{fp.name}|{fp.propertys['Reference'].value} has no silk outline"
            )
            return None

        return PCB_Transformer.get_bbox_from_geos(content)

    @staticmethod
    def get_pad_bbox(pad: Pad) -> tuple[Point2D, Point2D]:
        # TODO does this work for all shapes?
        rect_size = (pad.size.w, pad.size.h or pad.size.w)
        if pad.at.r in (90, 270):
            rect_size = (rect_size[1], rect_size[0])

        rect = (
            (pad.at.x - rect_size[0] / 2, pad.at.y - rect_size[1] / 2),
            (pad.at.x + rect_size[0] / 2, pad.at.y + rect_size[1] / 2),
        )

        return rect

    @staticmethod
    def get_geo_bbox(geo: Geom) -> tuple[Point2D, Point2D]:
        vecs = []
        if isinstance(geo, C_line):
            vecs = [geo.start, geo.end]
        elif isinstance(geo, C_arc):
            vecs = [geo.start, geo.mid, geo.end]
        elif isinstance(geo, C_rect):
            vecs = [geo.start, geo.end]
        elif isinstance(geo, C_circle):
            radius = geo.end - geo.center
            normal_radius = geo.end.rotate(geo.center, -90) - geo.center
            vecs = [
                geo.center - normal_radius - radius,
                geo.center - normal_radius + radius,
                geo.center + normal_radius - radius,
                geo.center + normal_radius + radius,
            ]
        else:
            raise NotImplementedError(f"Unsupported type {type(geo)}: {geo}")

        return Geometry.bbox([coord_to_point2d(vec) for vec in vecs])

    @staticmethod
    def get_footprint_pads_bbox(
        fp: Footprint, fp_coords: bool = True
    ) -> None | tuple[Point2D, Point2D]:
        pads = fp.pads
        rects = [PCB_Transformer.get_pad_bbox(pad) for pad in pads]

        if not fp_coords:
            raise NotImplementedError("fp_coords must be true")
        #    rects = [
        #        (abs_pos(fp.at, rect[0]), abs_pos(fp.at, rect[1])) for rect in rects
        #    ]

        return Geometry.bbox([point for rect in rects for point in rect])

    @staticmethod
    def get_bbox_from_geos(geos: list[Geom]) -> tuple[Point2D, Point2D] | None:
        extremes = list[C_xy]()

        for geo in geos:
            if isinstance(geo, C_line):
                extremes.extend([geo.start, geo.end])
            elif isinstance(geo, C_arc):
                # TODO: calculate extremes.extend([geo.start, geo.mid, geo.end])
                ...
            elif isinstance(geo, C_rect):
                extremes.extend([geo.start, geo.end])
            elif isinstance(geo, C_circle):
                # TODO: calculate extremes.extend([geo.center, geo.end])
                ...

        return Geometry.bbox([Point2D((point.x, point.y)) for point in extremes])

    def get_edge(self) -> list[Point2D]:
        def geo_to_lines(
            geo: Geom, fp: Footprint | None = None
        ) -> list[tuple[Point2D, Point2D]]:
            lines: list[tuple[Point2D, Point2D]] = []

            if isinstance(geo, GR_Line):
                lines = [(coord_to_point2d(geo.start), coord_to_point2d(geo.end))]
            elif isinstance(geo, Arc):
                arc = map(coord_to_point2d, (geo.start, geo.mid, geo.end))
                lines = Geometry.approximate_arc(*arc, resolution=10)
            elif isinstance(geo, Rect):
                rect = (coord_to_point2d(geo.start), coord_to_point2d(geo.end))

                c0 = (rect[0][0], rect[1][1])
                c1 = (rect[1][0], rect[0][1])

                l0 = (rect[0], c0)
                l1 = (rect[0], c1)
                l2 = (rect[1], c0)
                l3 = (rect[1], c1)

                lines = [l0, l1, l2, l3]
            else:
                raise NotImplementedError(f"Unsupported type {type(geo)}: {geo}")

            if fp:
                fpat = coord_to_point(fp.at)
                lines = [
                    per_point(
                        line,
                        lambda c: Geometry.as2d(Geometry.abs_pos(fpat, c)),
                    )
                    for line in lines
                ]

            return lines

        lines: list[tuple[Point2D, Point2D]] = [
            round_line(line)
            for sub_lines in [
                geo_to_lines(pcb_geo)
                for pcb_geo in get_all_geos(self.pcb)
                if pcb_geo.layer == "Edge.Cuts"
            ]
            + [
                geo_to_lines(fp_geo, fp)
                for fp in self.pcb.footprints
                for fp_geo in get_all_geos(fp)
                if fp_geo.layer == "Edge.Cuts"
            ]
            for line in sub_lines
        ]

        if not lines:
            return []

        from shapely import (
            LineString,
            get_geometry,
            get_num_geometries,
            polygonize_full,
        )

        polys, cut_edges, dangles, invalid_rings = polygonize_full(
            [LineString(line) for line in lines]
        )

        if get_num_geometries(cut_edges) != 0:
            raise Exception(f"EdgeCut: Cut edges: {cut_edges}")

        if get_num_geometries(dangles) != 0:
            raise Exception(f"EdgeCut: Dangling lines: {dangles}")

        if get_num_geometries(invalid_rings) != 0:
            raise Exception(f"EdgeCut: Invald rings: {invalid_rings}")

        if (n := get_num_geometries(polys)) != 1:
            if n == 0:
                logger.warning(f"EdgeCut: No closed polygons found in {lines}")
                assert False  # TODO remove
                return []
            raise Exception(f"EdgeCut: Ambiguous polygons {polys}")

        poly = get_geometry(polys, 0)
        assert isinstance(poly, Polygon)
        return list(poly.exterior.coords)

    @staticmethod
    def _get_pad(ffp: F.Footprint, intf: F.Electrical):
        pin_map = ffp.get_trait(F.has_kicad_footprint).get_pin_names()
        pin_name = find(
            pin_map.items(),
            lambda pad_and_name: intf.is_connected_to(pad_and_name[0].net),
        )[1]

        fp = PCB_Transformer.get_fp(ffp)
        pad = find(fp.pads, lambda p: p.name == pin_name)

        return fp, pad

    @staticmethod
    def get_pad(intf: F.Electrical) -> tuple[Footprint, Pad, Node]:
        obj, ffp = F.Footprint.get_footprint_of_parent(intf)
        fp, pad = PCB_Transformer._get_pad(ffp, intf)

        return fp, pad, obj

    @staticmethod
    def get_pad_pos_any(intf: F.Electrical):
        try:
            fpads = F.Pad.find_pad_for_intf_with_parent_that_has_footprint(intf)
        except KeyErrorNotFound:
            # intf has no parent with footprint
            return []

        return [PCB_Transformer.get_fpad_pos(fpad) for fpad in fpads]

    @staticmethod
    def get_pad_pos(intf: F.Electrical):
        try:
            fpad = F.Pad.find_pad_for_intf_with_parent_that_has_footprint_unique(intf)
        except ValueError:
            return None

        return PCB_Transformer.get_fpad_pos(fpad)

    @staticmethod
    def get_fpad_pos(fpad: F.Pad):
        fp, pad = fpad.get_trait(PCB_Transformer.has_linked_kicad_pad).get_pad()
        if len(pad) > 1:
            raise NotImplementedError(
                f"Multiple same pads is not implemented: {fpad} {pad}"
            )
        pad = pad[0]

        point3d = abs_pos(fp.at, pad.at)

        transformer = fpad.get_trait(
            PCB_Transformer.has_linked_kicad_pad
        ).get_transformer()

        layers = transformer.get_copper_layers_pad(pad)
        copper_layers = {
            layer: i for i, layer in enumerate(transformer.get_copper_layers())
        }
        layers = {copper_layers[layer] for layer in layers}

        return fpad, point3d[:3] + (layers,)

    def get_copper_layers(self):
        COPPER = re.compile(r"^.*\.Cu$")

        return {
            layer.name
            for layer in self.pcb.layers
            if COPPER.match(layer.name) is not None
        }

    def get_copper_layers_pad(self, pad: Pad):
        COPPER = re.compile(r"^.*\.Cu$")

        all_layers = [layer.name for layer in self.pcb.layers]

        def dewildcard(layer: str):
            if "*" not in layer:
                return {layer}
            pattern = re.compile(layer.replace(".", r"\.").replace("*", r".*"))
            return {
                global_layer
                for global_layer in all_layers
                if pattern.match(global_layer) is not None
            }

        layers = pad.layers
        dewildcarded_layers = {
            sub_layer for layer in layers for sub_layer in dewildcard(layer)
        }
        matching_layers = {
            layer for layer in dewildcarded_layers if COPPER.match(layer) is not None
        }

        return matching_layers

    def get_layer_id(self, layer: str) -> int:
        copper_layers = {layer: i for i, layer in enumerate(self.get_copper_layers())}
        return copper_layers[layer]

    def get_layer_name(self, layer_id: int) -> str:
        copper_layers = {i: layer for i, layer in enumerate(self.get_copper_layers())}
        return copper_layers[layer_id]

    # Insert ---------------------------------------------------------------------------
    @staticmethod
    def mark[R](node: R) -> R:
        if hasattr(node, "uuid"):
            node.uuid = PCB_Transformer.gen_uuid(mark=True)  # type: ignore

        return node

    @deprecated("Use the proper inserter, or insert into corresponding field")
    def insert(self, obj: Any):
        self._insert(obj)

    def _get_pcb_list_field[R](self, node: R, prefix: str = "") -> list[R]:
        root = self.pcb
        key = prefix + type(node).__name__.removeprefix("C_") + "s"

        assert hasattr(root, key)

        target = getattr(root, key)
        assert isinstance(target, list)
        assert all(isinstance(x, type(node)) for x in target)
        return target

    def _insert(self, obj: Any, prefix: str = ""):
        obj = PCB_Transformer.mark(obj)
        self._get_pcb_list_field(obj, prefix=prefix).append(obj)

    def _delete(self, obj: Any, prefix: str = ""):
        self._get_pcb_list_field(obj, prefix=prefix).remove(obj)

    def insert_via(
        self, coord: tuple[float, float], net: int, size_drill: tuple[float, float]
    ):
        self.pcb.vias.append(
            Via(
                at=C_xy(*coord),
                size=size_drill[0],
                drill=size_drill[1],
                layers=["F.Cu", "B.Cu"],
                net=net,
                uuid=self.gen_uuid(mark=True),
            )
        )

    def insert_text(
        self,
        text: str,
        at: C_xyr,
        font: Font,
        layer: str = "F.SilkS",
        alignment: Alignment | None = None,
        knockout: bool = False,
    ):
        if not alignment:
            if layer.startswith("F."):
                alignment = Alignment_Default
            else:
                alignment = (
                    Justify.center_horizontal,
                    Justify.center_vertical,
                    Justify.mirror,
                )

        self.pcb.gr_texts.append(
            GR_Text(
                text=text,
                at=at,
                layer=C_text_layer(layer, C_text_layer.E_knockout.knockout)
                if knockout
                else C_text_layer(layer),
                effects=C_effects(
                    font=font,
                    justifys=[C_effects.C_justify(justifys=list(alignment))],
                ),
                uuid=self.gen_uuid(mark=True),
            )
        )

    def insert_track(
        self,
        net_id: int,
        points: list[Point2D],
        width: float,
        layer: str,
        arc: bool,
    ):
        points_ = [point2d_to_coord(p) for p in points]
        if arc:
            start_and_ends = points_[::2]
            for s, e, m in zip(start_and_ends[:-1], start_and_ends[1:], points_[1::2]):
                self.pcb.arcs.append(
                    PCB.C_arc_segment(
                        start=s,
                        mid=m,
                        end=e,
                        width=width,
                        layer=layer,
                        net=net_id,
                        uuid=self.gen_uuid(mark=True),
                    )
                )
        else:
            for s, e in zip(points_[:-1], points_[1:]):
                self.pcb.segments.append(
                    PCB.C_segment(
                        start=s,
                        end=e,
                        width=width,
                        layer=layer,
                        net=net_id,
                        uuid=self.gen_uuid(mark=True),
                    )
                )

    def insert_line(self, start: C_xy, end: C_xy, width: float, layer: str):
        self.insert_geo(
            Line(
                start=start,
                end=end,
                stroke=C_stroke(width, C_stroke.E_type.solid),
                layer=layer,
                uuid=self.gen_uuid(mark=True),
            )
        )

    def insert_geo(self, geo: Geom):
        self._insert(geo, prefix="gr_")

    def delete_geo(self, geo: Geom):
        self._delete(geo, prefix="gr_")

    def get_net_obj_bbox(self, net: Net, layer: str, tolerance=0.0):
        vias = self.pcb.vias
        pads = [(pad, fp) for fp in self.pcb.footprints for pad in fp.pads]

        net_vias = [via for via in vias if via.net == net.number]
        net_pads = [
            (pad, fp)
            for pad, fp in pads
            if pad.net == net.number and layer in pad.layers
        ]
        coords: list[Point2D] = [coord_to_point2d(via.at) for via in net_vias] + [
            abs_pos2d(fp.at, pad.at) for pad, fp in net_pads
        ]

        # TODO ugly, better get pcb boundaries
        if not coords:
            coords = [(-1e3, -1e3), (1e3, 1e3)]

        bbox = Geometry.bbox(coords, tolerance=tolerance)

        return Geometry.rect_to_polygon(bbox)

    def insert_zone(
        self,
        net: Net,
        layers: str | list[str],
        polygon: list[Point2D],
        keepout: bool = False,
    ):
        # check if exists
        zones = self.pcb.zones
        # TODO: zones is always emtpy list?
        # TODO check bbox

        if isinstance(layers, str):
            layers = [layers]

        for layer in layers:
            if any([zone.layer == layer for zone in zones]):
                logger.warning(f"Zone already exists in {layer=}")
                return

        self.pcb.zones.append(
            Zone(
                net=net.number,
                net_name=net.name,
                layer=layers[0] if len(layers) == 1 else None,
                layers=layers if len(layers) > 1 else None,
                uuid=self.gen_uuid(mark=True),
                name=f"layer_fill_{net.name}",
                polygon=C_polygon(C_pts([point2d_to_coord(p) for p in polygon])),
                min_thickness=0.2,
                filled_areas_thickness=False,
                fill=Zone.C_fill(
                    enable=True,
                    mode=None,
                    hatch_thickness=0.0,
                    hatch_gap=0.5,
                    hatch_orientation=0,
                    hatch_smoothing_level=0,
                    hatch_smoothing_value=0,
                    hatch_border_algorithm=Zone.C_fill.E_hatch_border_algorithm.hatch_thickness,
                    hatch_min_hole_area=0.3,
                    thermal_gap=0.2,
                    thermal_bridge_width=0.2,
                    smoothing=None,
                    radius=1,
                    # island_removal_mode=Zone.C_fill.E_island_removal_mode.do_not_remove, # noqa E501
                    island_area_min=10.0,
                ),
                locked=False,
                hatch=Zone.C_hatch(mode=Zone.C_hatch.E_mode.edge, pitch=0.5),
                priority=0,
                keepout=Zone.C_keepout(
                    tracks=Zone.C_keepout.E_keepout_bool.allowed,
                    vias=Zone.C_keepout.E_keepout_bool.allowed,
                    pads=Zone.C_keepout.E_keepout_bool.allowed,
                    copperpour=Zone.C_keepout.E_keepout_bool.not_allowed,
                    footprints=Zone.C_keepout.E_keepout_bool.allowed,
                )
                if keepout
                else None,
                connect_pads=Zone.C_connect_pads(
                    mode=Zone.C_connect_pads.E_mode.thermal_reliefs, clearance=0.2
                ),
            )
        )

    # Groups ---------------------------------------------------------------------------
    def _add_group(
        self, members: list[UUID], name: Optional[str] = None, locked: bool = False
    ) -> UUID:
        group = C_kicad_pcb_file.C_kicad_pcb.C_group(
            name=name, members=members, uuid=self.gen_uuid(mark=True), locked=locked
        )
        self.pcb.groups.append(group)
        logger.debug(f"Added group {name} with members: {len(members)}")
        return group.uuid

    # JLCPCB ---------------------------------------------------------------------------
    class JLCPBC_QR_Size(Enum):
        SMALL_5x5mm = C_xy(5, 5)
        MEDIUM_8x8mm = C_xy(5, 5)
        LARGE_10x10mm = C_xy(5, 5)

    def insert_jlcpcb_qr(
        self,
        size: JLCPBC_QR_Size,
        center_at: C_xy,
        layer="F.SilkS",
        number: bool = True,
    ):
        assert layer.endswith("SilkS"), "JLCPCB QR code must be on silk screen layer"
        if number:
            self.insert_text(
                "######",
                at=C_xyr(center_at.x, center_at.y + size.value.y / 2 + 1, 0),
                font=Font(size=C_wh(0.75, 0.75), thickness=0.15),
                layer="F.Fab" if layer.startswith("F.") else "B.Fab",
            )
        self.insert_geo(
            C_rect(
                start=C_xy(
                    center_at.x - size.value.x / 2, center_at.y - size.value.y / 2
                ),
                end=C_xy(
                    center_at.x + size.value.x / 2, center_at.y + size.value.y / 2
                ),
                stroke=C_stroke(width=0.15, type=C_stroke.E_type.solid),
                fill=E_fill.solid,
                layer=layer,
                uuid=self.gen_uuid(mark=True),
            )
        )

    def insert_jlcpcb_serial(
        self,
        center_at: C_xyr,
        layer="F.SilkS",
    ):
        assert layer.endswith(
            "SilkS"
        ), "JLCPCB serial number must be on silk screen layer"
        self.insert_text(
            "JLCJLCJLCJLC",
            at=center_at,
            font=Font(
                size=C_wh(1, 1),
                thickness=0.15,
            ),
            layer=layer,
        )

    # Positioning ----------------------------------------------------------------------
    def move_footprints(self):
        # position modules with defined positions
        pos_mods = GraphFunctions(self.graph).nodes_with_traits(
            (F.has_pcb_position, self.has_linked_kicad_footprint)
        )

        logger.info(f"Positioning {len(pos_mods)} footprints")

        for module, _ in pos_mods:
            fp = module.get_trait(self.has_linked_kicad_footprint).get_fp()
            coord = module.get_trait(F.has_pcb_position).get_position()
            layer_names = {
                F.has_pcb_position.layer_type.TOP_LAYER: "F.Cu",
                F.has_pcb_position.layer_type.BOTTOM_LAYER: "B.Cu",
            }

            match coord[3]:
                case F.has_pcb_position.layer_type.NONE:
                    logger.warning(
                        f"Assigning default layer for component `{module}({fp.name})`",
                        extra={"markdown": True},
                    )
                    layer = layer_names[F.has_pcb_position.layer_type.TOP_LAYER]
                case _:
                    layer = layer_names[coord[3]]

            logger.debug(f"Placing {fp.name} at {coord} layer {layer}")
            self.move_fp(fp, C_xyr(*coord[:3]), layer)

    def move_fp(self, fp: Footprint, coord: C_xyr, layer: str):
        if any([x.text == "FBRK:notouch" for x in fp.fp_texts]):
            logger.warning(f"Skipped no touch component: {fp.name}")
            return

        # Rotate
        rot_angle = (coord.r - fp.at.r) % 360

        if rot_angle:
            # Rotation vector in kicad footprint objs not relative to footprint rotation
            #  or is it?
            for obj in fp.pads:
                obj.at.r = (obj.at.r + rot_angle) % 360
            # For some reason text rotates in the opposite direction
            #  or maybe not?
            for obj in fp.fp_texts + list(fp.propertys.values()):
                obj.at.r = (obj.at.r + rot_angle) % 360

        fp.at = coord

        # Flip
        flip = fp.layer != layer

        if flip:

            def _flip(x: str):
                return x.replace("F.", "<F>.").replace("B.", "F.").replace("<F>.", "B.")

            fp.layer = _flip(fp.layer)

            # TODO: sometimes pads are being rotated by kicad ?!??
            for obj in fp.pads:
                obj.layers = [_flip(x) for x in obj.layers]

            for obj in get_all_geos(fp) + fp.fp_texts + list(fp.propertys.values()):
                if isinstance(obj, C_footprint.C_property):
                    obj = obj.layer
                if isinstance(obj, C_fp_text):
                    obj = obj.layer
                obj.layer = _flip(obj.layer)

        # Label
        if not any([x.text == "FBRK:autoplaced" for x in fp.fp_texts]):
            fp.fp_texts.append(
                C_fp_text(
                    type=C_fp_text.E_type.user,
                    text="FBRK:autoplaced",
                    at=C_xyr(0, 0, rot_angle),
                    effects=C_effects(self.font),
                    uuid=self.gen_uuid(mark=True),
                    layer=C_text_layer("User.5"),
                )
            )

    # Edge -----------------------------------------------------------------------------
    # TODO: make generic
    def connect_line_pair_via_radius(
        self,
        line1: C_line,
        line2: C_line,
        radius: float,
    ) -> tuple[Line, Arc, Line]:
        # Assert if the endpoints of the lines are not connected
        assert line1.end == line2.start, "The endpoints of the lines are not connected."

        # Assert if the radius is less than or equal to zero
        assert radius > 0, "The radius must be greater than zero."

        l1s = line1.start.x, line1.start.y
        l1e = line1.end.x, line1.end.y
        l2s = line2.start.x, line2.start.y
        l2e = line2.end.x, line2.end.y

        v1 = np.array(l1s) - np.array(l1e)
        v2 = np.array(l2e) - np.array(l2s)
        v1 = v1 / np.linalg.norm(v1)
        v2 = v2 / np.linalg.norm(v2)

        v_middle = v1 * radius + v2 * radius
        v_middle_norm = v_middle / np.linalg.norm(v_middle)
        v_center = v_middle - v_middle_norm * radius

        # calculate the arc center
        arc_center = np.array(l1e) + v_center

        # calculate the arc start and end points
        arc_end = np.array(l2s) + v2 * radius
        arc_start = np.array(l1e) + v1 * radius

        # convert to tuples
        arc_start = point2d_to_coord(tuple(arc_start))
        arc_center = point2d_to_coord(tuple(arc_center))
        arc_end = point2d_to_coord(tuple(arc_end))

        logger.debug(f"{v_middle=}")
        logger.debug(f"{v_middle_norm=}")
        logger.debug(f"{v_center=}")

        logger.debug(f"line intersection: {l1e} == {l2s}")
        logger.debug(f"line1: {l1s} -> {l1e}")
        logger.debug(f"line2: {l2s} -> {l2e}")
        logger.debug(f"v1: {v1}")
        logger.debug(f"v2: {v2}")
        logger.debug(f"v_middle: {v_middle}")
        logger.debug(f"radius: {radius}")
        logger.debug(f"arc_start: {arc_start}")
        logger.debug(f"arc_center: {arc_center}")
        logger.debug(f"arc_end: {arc_end}")

        # Create the arc
        arc = Arc(
            start=arc_start,
            mid=arc_center,
            end=arc_end,
            stroke=C_stroke(0.05, C_stroke.E_type.solid),
            layer="Edge.Cuts",
            uuid=self.gen_uuid(mark=True),
        )

        # Create new lines
        new_line1 = Line(
            start=line1.start,
            end=arc_start,
            stroke=C_stroke(0.05, C_stroke.E_type.solid),
            layer="Edge.Cuts",
            uuid=self.gen_uuid(mark=True),
        )
        new_line2 = Line(
            start=arc_end,
            end=line2.end,
            stroke=C_stroke(0.05, C_stroke.E_type.solid),
            layer="Edge.Cuts",
            uuid=self.gen_uuid(mark=True),
        )

        return new_line1, arc, new_line2

    def round_corners(
        self, geometry: Sequence[Geom], corner_radius_mm: float
    ) -> list[Geom]:
        """
        Round the corners of a geometry by replacing line pairs with arcs.
        """

        def _transform(geo1: Geom, geo2: Geom) -> Iterable[Geom]:
            if not isinstance(geo1, Line) or not isinstance(geo2, Line):
                return (geo1,)

            new_line1, arc, new_line2 = self.connect_line_pair_via_radius(
                geo1,
                geo2,
                corner_radius_mm,
            )
            return new_line1, new_line2, arc

        return [
            t_geo
            for pair in pairwise(list(geometry) + [geometry[0]])
            for t_geo in _transform(*pair)
        ]

    def create_rectangular_edgecut(
        self,
        width_mm: float,
        height_mm: float,
        rounded_corners: bool = False,
        corner_radius_mm: float = 0.0,
        origin: tuple[float, float] = (0, 0),
    ) -> list[Geom] | list[Line]:
        """
        Create a rectengular board outline (edge cut)
        """
        # make 4 line objects where the end of the last line is the begining of the next
        lines = [
            Line(
                start=C_xy(origin[0], origin[1]),
                end=C_xy(origin[0] + width_mm, origin[1]),
                stroke=C_stroke(0.05, C_stroke.E_type.solid),
                layer="Edge.Cuts",
                uuid=self.gen_uuid(mark=True),
            ),
            Line(
                start=C_xy(origin[0] + width_mm, origin[1]),
                end=C_xy(origin[0] + width_mm, origin[1] + height_mm),
                stroke=C_stroke(0.05, C_stroke.E_type.solid),
                layer="Edge.Cuts",
                uuid=self.gen_uuid(mark=True),
            ),
            Line(
                start=C_xy(origin[0] + width_mm, origin[1] + height_mm),
                end=C_xy(origin[0], origin[1] + height_mm),
                stroke=C_stroke(0.05, C_stroke.E_type.solid),
                layer="Edge.Cuts",
                uuid=self.gen_uuid(mark=True),
            ),
            Line(
                start=C_xy(origin[0], origin[1] + height_mm),
                end=C_xy(origin[0], origin[1]),
                stroke=C_stroke(0.05, C_stroke.E_type.solid),
                layer="Edge.Cuts",
                uuid=self.gen_uuid(mark=True),
            ),
        ]
        if rounded_corners:
            rounded_geometry = self.round_corners(lines, corner_radius_mm)
            return rounded_geometry
        else:
            return lines

    # plot the board outline with matplotlib
    # TODO: remove
    def plot_board_outline(self, geometry: List[Any]):
        import matplotlib.patches as patches
        import matplotlib.pyplot as plt
        from matplotlib.path import Path

        def plot_arc(start, mid, end):
            verts = [start, mid, end]
            codes = [Path.MOVETO, Path.CURVE3, Path.CURVE3]  # , Path.CLOSEPOLY]

            path = Path(verts, codes)
            shape = patches.PathPatch(path, facecolor="none", lw=0.75)
            plt.gca().add_patch(shape)

        fig, ax = plt.subplots()
        for geo in geometry:
            if isinstance(geo, Line):
                # plot a line
                plt.plot([geo.start.x, geo.end.x], [geo.start.y, geo.end.y])
            elif isinstance(geo, Arc):
                plot_arc(geo.start, geo.mid, geo.end)
                plt.plot([geo.start.x, geo.end.x], [geo.start.y, geo.end.y])
        plt.show()

    def set_pcb_outline_complex(
        self,
        geometry: List[Geom],
        remove_existing_outline: bool = True,
        corner_radius_mm: float = 0.0,
    ):
        """
        Create a board outline (edge cut) consisting out of
        different geometries
        """

        # TODO: remove
        # self.plot_board_outline(geometry)

        # remove existing lines on Egde.cuts layer
        if remove_existing_outline:
            for geo in get_all_geos(self.pcb):
                if not isinstance(geo, (Line, Arc)):
                    continue
                if geo.layer != "Edge.Cuts":
                    continue
                self.delete_geo(geo)

        # round corners between lines
        if corner_radius_mm > 0:
            geometry = self.round_corners(geometry, corner_radius_mm)

        # create Edge.Cuts geometries
        for geo in geometry:
            assert geo.layer == "Edge.Cuts", f"Geometry {geo} is not on Edge.Cuts layer"

            self.insert_geo(geo)

        # find bounding box

    # Silkscreen -----------------------------------------------------------------------
    class Side(Enum):
        TOP = auto()
        BOTTOM = auto()
        LEFT = auto()
        RIGHT = auto()

    def set_designator_position(
        self,
        offset: float,
        displacement: C_xy = C_xy(0, 0),
        rotation: Optional[float] = None,
        offset_side: Side = Side.BOTTOM,
        layer: Optional[C_text_layer] = None,
        font: Optional[Font] = None,
        knockout: Optional[C_text_layer.E_knockout] = None,
        justify: Alignment | None = None,
    ):
        for mod, fp in self.get_all_footprints():
            reference = fp.propertys["Reference"]
            reference.layer = (
                layer
                if layer
                else C_text_layer(
                    layer="F.SilkS" if fp.layer.startswith("F") else "B.SilkS"
                )
            )
            if knockout:
                reference.layer.knockout = knockout
            if font:
                reference.effects.font = font
            if justify:
                reference.effects.justifys = [
                    C_effects.C_justify(justifys=list(justify))
                ]

            rot = rotation if rotation else reference.at.r

            footprint_bbox = self.get_bounding_box(fp, {"F.SilkS", "B.SilkS"})
            if not footprint_bbox:
                continue
            max_coord = C_xy(*footprint_bbox[1])
            min_coord = C_xy(*footprint_bbox[0])

            if offset_side == self.Side.BOTTOM:
                reference.at = C_xyr(
                    displacement.x, max_coord.y + offset - displacement.y, rot
                )
            elif offset_side == self.Side.TOP:
                reference.at = C_xyr(
                    displacement.x, min_coord.y - offset - displacement.y, rot
                )
            elif offset_side == self.Side.LEFT:
                reference.at = C_xyr(
                    min_coord.x - offset - displacement.x, displacement.y, rot
                )
            elif offset_side == self.Side.RIGHT:
                reference.at = C_xyr(
                    max_coord.x + offset + displacement.x, displacement.y, rot
                )

    def add_git_version(
        self,
        center_at: C_xyr,
        layer: str = "F.SilkS",
        font: Font = Font(size=C_wh(1, 1), thickness=0.2),
        knockout: bool = True,
        alignment: Alignment = Alignment_Default,
    ):
        # check if gitcli is available
        try:
            subprocess.check_output(["git", "--version"])
        except subprocess.CalledProcessError:
            logger.warning("git is not installed")
            git_human_version = "git is not installed"

        try:
            git_human_version = (
                subprocess.check_output(["git", "describe", "--always"])
                .strip()
                .decode("utf-8")
            )
        except subprocess.CalledProcessError:
            logger.warning("Cannot get git project version")
            git_human_version = "Cannot get git project version"

        self.insert_text(
            text=git_human_version,
            at=center_at,
            layer=layer,
            font=font,
            alignment=alignment,
            knockout=knockout,
        )
