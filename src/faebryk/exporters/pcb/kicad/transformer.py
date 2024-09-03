# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import pprint
import re
import uuid
from abc import abstractmethod
from dataclasses import fields
from itertools import pairwise
from typing import Any, Callable, Iterable, List, Sequence, TypeVar

import numpy as np
from shapely import Polygon
from typing_extensions import deprecated

import faebryk.library._F as F
from faebryk.core.graphinterface import Graph
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node
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
)
from faebryk.libs.sexp.dataclass_sexp import dataclass_dfs
from faebryk.libs.util import cast_assert, find, get_key

logger = logging.getLogger(__name__)

FPad = F.Pad
FNet = F.Net
FFootprint = F.Footprint

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


def gen_uuid(mark: str = "") -> UUID:
    # format: d864cebe-263c-4d3f-bbd6-bb51c6d2a608
    value = uuid.uuid4().hex

    suffix = mark.encode().hex()
    value = value[: -len(suffix)] + suffix

    DASH_IDX = [8, 12, 16, 20]
    formatted = value
    for i, idx in enumerate(DASH_IDX):
        formatted = formatted[: idx + i] + "-" + formatted[idx + i :]

    return UUID(formatted)


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

        self.cleanup()
        self.attach()

    def attach(self):
        footprints = {
            (f.propertys["Reference"].value, f.name): f for f in self.pcb.footprints
        }
        from faebryk.core.util import get_all_nodes_with_trait

        for node, fpt in get_all_nodes_with_trait(self.graph, F.has_footprint):
            if not node.has_trait(F.has_overriden_name):
                continue
            g_fp = fpt.get_footprint()
            if not g_fp.has_trait(F.has_kicad_footprint):
                continue

            fp_ref = node.get_trait(F.has_overriden_name).get_name()
            fp_name = g_fp.get_trait(F.has_kicad_footprint).get_kicad_footprint()

            assert (
                fp_ref,
                fp_name,
            ) in footprints, (
                f"Footprint ({fp_ref=}, {fp_name=}) not found in footprints dictionary."
                f" Did you import the latest NETLIST into KiCad?"
            )
            fp = footprints[(fp_ref, fp_name)]

            g_fp.add_trait(self.has_linked_kicad_footprint_defined(fp, self))
            node.add_trait(self.has_linked_kicad_footprint_defined(fp, self))

            pin_names = g_fp.get_trait(F.has_kicad_footprint).get_pin_names()
            for fpad in g_fp.get_children(direct_only=True, types=ModuleInterface):
                pads = [
                    pad
                    for pad in fp.pads
                    if pad.name == pin_names[cast_assert(FPad, fpad)]
                ]
                fpad.add_trait(
                    PCB_Transformer.has_linked_kicad_pad_defined(fp, pads, self)
                )

        attached = {
            n: t.get_fp()
            for n, t in get_all_nodes_with_trait(
                self.graph, self.has_linked_kicad_footprint
            )
        }
        logger.debug(f"Attached: {pprint.pformat(attached)}")

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
    def get_fp(cmp) -> Footprint:
        return cmp.get_trait(PCB_Transformer.has_linked_kicad_footprint).get_fp()

    def get_net(self, net: FNet) -> Net:
        nets = {pcb_net.name: pcb_net for pcb_net in self.pcb.nets}
        return nets[net.get_trait(F.has_overriden_name).get_name()]

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
    def _get_pad(ffp: FFootprint, intf: F.Electrical):
        pin_map = ffp.get_trait(F.has_kicad_footprint).get_pin_names()
        pin_name = find(
            pin_map.items(),
            lambda pad_and_name: intf.is_connected_to(pad_and_name[0].net) is not None,
        )[1]

        fp = PCB_Transformer.get_fp(ffp)
        pad = find(fp.pads, lambda p: p.name == pin_name)

        return fp, pad

    @staticmethod
    def get_pad(intf: F.Electrical) -> tuple[Footprint, Pad, Node]:
        obj, ffp = FFootprint.get_footprint_of_parent(intf)
        fp, pad = PCB_Transformer._get_pad(ffp, intf)

        return fp, pad, obj

    @staticmethod
    def get_pad_pos_any(intf: F.Electrical) -> list[tuple[FPad, Point]]:
        try:
            fpads = FPad.find_pad_for_intf_with_parent_that_has_footprint(intf)
        except ValueError:
            # intf has no parent with footprint
            return []

        return [PCB_Transformer.get_fpad_pos(fpad) for fpad in fpads]

    @staticmethod
    def get_pad_pos(intf: F.Electrical) -> tuple[FPad, Point] | None:
        try:
            fpad = FPad.find_pad_for_intf_with_parent_that_has_footprint_unique(intf)
        except ValueError:
            return None

        return PCB_Transformer.get_fpad_pos(fpad)

    @staticmethod
    def get_fpad_pos(fpad: FPad):
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
        if len(layers) != 1:
            layer = 0
        else:
            copper_layers = {
                layer: i for i, layer in enumerate(transformer.get_copper_layers())
            }
            layer = copper_layers[layers.pop()]

        return fpad, point3d[:3] + (layer,)

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
                size=C_wh(size_drill[0], size_drill[0]),
                drill=size_drill[1],
                layers=["F.Cu", "B.Cu"],
                net=net,
                uuid=self.gen_uuid(mark=True),
            )
        )

    def insert_text(self, text: str, at: C_xyr, font: Font, front: bool = True):
        self.pcb.gr_texts.append(
            GR_Text(
                text=text,
                at=at,
                layer=C_text_layer(f"{'F' if front else 'B'}.SilkS"),
                effects=C_effects(
                    font=font,
                    justify=(
                        C_effects.E_justify.center,
                        C_effects.E_justify.center,
                        C_effects.E_justify.mirror
                        if not front
                        else C_effects.E_justify.normal,
                    ),
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

    def insert_zone(self, net: Net, layers: str | list[str], polygon: list[Point2D]):
        # check if exists
        zones = self.pcb.zones
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
                polygon=C_polygon(
                    C_polygon.C_pts([point2d_to_coord(p) for p in polygon])
                ),
                min_thickness=0.2,
                filled_areas_thickness=False,
                fill=Zone.C_fill(
                    enable=True,
                    mode=None,
                    hatch_thickness=0.25,
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
                    island_removal_mode=Zone.C_fill.E_island_removal_mode.do_not_remove,
                    island_area_min=10.0,
                ),
                locked=False,
                hatch=Zone.C_hatch(mode=Zone.C_hatch.E_mode.edge, pitch=0.5),
                priority=0,
                connect_pads=Zone.C_connect_pads(
                    mode=Zone.C_connect_pads.E_mode.thermal_reliefs, clearance=0.2
                ),
            )
        )

    # Positioning ----------------------------------------------------------------------
    def move_footprints(self):
        from faebryk.core.util import get_all_nodes_with_traits

        # position modules with defined positions
        pos_mods = get_all_nodes_with_traits(
            self.graph, (F.has_pcb_position, self.has_linked_kicad_footprint)
        )

        logger.info(f"Positioning {len(pos_mods)} footprints")

        for module, _ in pos_mods:
            fp = module.get_trait(self.has_linked_kicad_footprint).get_fp()
            coord = module.get_trait(F.has_pcb_position).get_position()
            layer_name = {
                F.has_pcb_position.layer_type.TOP_LAYER: "F.Cu",
                F.has_pcb_position.layer_type.BOTTOM_LAYER: "B.Cu",
            }

            if coord[3] == F.has_pcb_position.layer_type.NONE:
                raise Exception(f"Component {module}({fp.name}) has no layer defined")

            logger.debug(f"Placing {fp.name} at {coord} layer {layer_name[coord[3]]}")
            self.move_fp(fp, C_xyr(*coord[:3]), layer_name[coord[3]])

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
    ) -> list[Geom] | list[Line]:
        """
        Create a rectengular board outline (edge cut)
        """
        # make 4 line objects where the end of the last line is the begining of the next
        lines = [
            Line(
                start=C_xy(0, 0),
                end=C_xy(width_mm, 0),
                stroke=C_stroke(0.05, C_stroke.E_type.solid),
                layer="Edge.Cuts",
                uuid=self.gen_uuid(mark=True),
            ),
            Line(
                start=C_xy(width_mm, 0),
                end=C_xy(width_mm, height_mm),
                stroke=C_stroke(0.05, C_stroke.E_type.solid),
                layer="Edge.Cuts",
                uuid=self.gen_uuid(mark=True),
            ),
            Line(
                start=C_xy(width_mm, height_mm),
                end=C_xy(0, height_mm),
                stroke=C_stroke(0.05, C_stroke.E_type.solid),
                layer="Edge.Cuts",
                uuid=self.gen_uuid(mark=True),
            ),
            Line(
                start=C_xy(0, height_mm),
                end=C_xy(0, 0),
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
