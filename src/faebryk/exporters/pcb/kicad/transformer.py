# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import itertools
import logging
import math
import pprint
import random
import re
from operator import add
from typing import Any, TypeVar

import numpy as np
from faebryk.core.core import (
    Footprint as Core_Footprint,
)
from faebryk.core.core import (
    Module,
    ModuleInterface,
    ModuleTrait,
    Node,
)
from faebryk.core.graph import Graph
from faebryk.library.has_footprint import has_footprint
from faebryk.library.has_kicad_footprint import has_kicad_footprint
from faebryk.library.has_overriden_name import has_overriden_name
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.library.Net import Net as FNet
from faebryk.libs.kicad.pcb import (
    PCB,
    Arc,
    At,
    Footprint,
    FP_Text,
    Geom,
    GR_Line,
    GR_Text,
    Net,
    Pad,
    Rect,
    Segment,
    Segment_Arc,
    Via,
)
from faebryk.libs.kicad.pcb import (
    Node as PCB_Node,
)

logger = logging.getLogger(__name__)


class PCB_Transformer:
    class has_linked_kicad_footprint(ModuleTrait):
        """
        Module has footprint (which has kicad footprint) and that footprint
        is found in the current PCB file.
        """

        def get_fp(self) -> Footprint:
            raise NotImplementedError()

    class has_linked_kicad_footprint_defined(has_linked_kicad_footprint.impl()):
        def __init__(self, fp: Footprint) -> None:
            super().__init__()
            self.fp = fp

        def get_fp(self):
            return self.fp

    def __init__(
        self, pcb: PCB, graph: Graph, app: Module, cleanup: bool = True
    ) -> None:
        self.pcb = pcb
        self.graph = graph
        self.app = app

        self.dimensions = None

        FONT_SCALE = 8
        FONT = (1 / FONT_SCALE, 1 / FONT_SCALE, 0.15 / FONT_SCALE)
        self.font = FONT

        # After finalized, vias get changed to 0.45
        self.via_size_drill = (0.46, 0.2)

        self.tstamp_i = itertools.count()
        self.cleanup()

        self.attach()

    def attach(self):
        footprints = {(f.reference.text, f.name): f for f in self.pcb.footprints}

        for node in {gif.node for gif in self.graph.G.nodes}:
            assert isinstance(node, Node)
            if not node.has_trait(has_overriden_name):
                continue
            if not node.has_trait(has_footprint):
                continue
            g_fp = node.get_trait(has_footprint).get_footprint()
            if not g_fp.has_trait(has_kicad_footprint):
                continue

            fp_ref = node.get_trait(has_overriden_name).get_name()
            fp_name = g_fp.get_trait(has_kicad_footprint).get_kicad_footprint()

            assert (
                fp_ref,
                fp_name,
            ) in footprints, (
                f"Footprint ({fp_ref=}, {fp_name=}) not found in footprints dictionary."
                f" Did you import the latest NETLIST into KiCad?"
            )
            fp = footprints[(fp_ref, fp_name)]

            node.add_trait(self.has_linked_kicad_footprint_defined(fp))

        attached = {
            gif.node: gif.node.get_trait(self.has_linked_kicad_footprint).get_fp()
            for gif in self.graph.G.nodes
            if gif.node.has_trait(self.has_linked_kicad_footprint)
        }
        logger.debug(f"Attached: {pprint.pformat(attached)}")

    def set_dimensions_rectangle(
        self,
        width_mm: float,
        height_mm: float,
        origin_x_mm: float = 0.0,
        origin_y_mm: float = 0.0,
    ):
        """
        Create a rectengular board outline (edge cut)
        """

        for geo in self.pcb.geoms:
            if not isinstance(geo, GR_Line):
                continue
            line = geo
            if line.layer_name != "Edge.Cuts":
                continue
            line.delete()

        points = [
            (origin_x_mm, origin_y_mm),
            (origin_x_mm, origin_y_mm + height_mm),
            (origin_x_mm + width_mm, origin_y_mm + height_mm),
            (origin_x_mm + width_mm, origin_y_mm),
            (origin_x_mm, origin_y_mm),
        ]

        for start, end in zip(points[:-1], points[1:]):
            self.pcb.append(
                GR_Line.factory(
                    start,
                    end,
                    stroke=GR_Line.Stroke.factory(0.05, "default"),
                    layer="Edge.Cuts",
                    tstamp=str(int(random.random() * 100000)),
                )
            )

        self.dimensions = (width_mm, height_mm)

    def set_dimensions_complex(
        self,
        points: list,
        origin_x_mm: float = 0.0,
        origin_y_mm: float = 0.0,
        remove_existing_outline: bool = True,
    ):
        """
        Create a board outline (edge cut) consisting out of
        points connected via straight lines
        """

        # remove existing lines on Egde.cuts layer
        if remove_existing_outline:
            for geo in self.pcb.geoms:
                if not isinstance(geo, GR_Line):
                    continue
                line = geo
                if line.layer_name != "Edge.Cuts":
                    continue
                line.delete()

        # offset the points with origin
        points_offset = []
        for point in points:
            points_offset.append((point[0] + origin_x_mm, point[1] + origin_y_mm))

        # Append the first point to the end to create a closed shape
        points_offset.append(points_offset[0])

        # create Edge.Cuts lines
        for start, end in zip(points_offset, points_offset[1:]):
            self.pcb.append(
                GR_Line.factory(
                    start,
                    end,
                    stroke=GR_Line.Stroke.factory(0.05, "default"),
                    layer="Edge.Cuts",
                    tstamp=str(int(random.random() * 100000)),
                )
            )

        width_mm = max(p[0] for p in points)
        height_mm = max(p[1] for p in points)

        self.dimensions = (width_mm, height_mm)

    def move_fp(self, fp: Footprint, coord: Footprint.Coord, layer: str):
        if any([x.text == "FBRK:notouch" for x in fp.user_text]):
            logger.warning(f"Skipped no touch component: {fp.name}")
            return

        # Rotate
        rot_angle = (coord[2] - fp.at.coord[2]) % 360

        if rot_angle:
            for at_prop in fp.get_prop("at", recursive=True):
                coords = at_prop.node[1:]
                # if rot is 0 in coord, its compressed to a 2-tuple by kicad
                if len(coords) == 2:
                    coords.append(0)
                coords[2] = (coords[2] + rot_angle) % 360
                at_prop.node[1:] = coords

        fp.at.coord = coord

        # Flip
        # TODO a bit ugly with the hardcoded front layer
        flip = layer != "F.Cu" and fp.layer != layer

        if flip:
            for layer_prop in fp.get_prop(["layer", "layers"], recursive=True):

                def _flip(x):
                    return (
                        x.replace("F.", "<F>.")
                        .replace("B.", "F.")
                        .replace("<F>.", "B.")
                    )

                layer_prop.node[1:] = [_flip(x) for x in layer_prop.node[1:]]

        # Label
        if any([x.text == "FBRK:autoplaced" for x in fp.user_text]):
            return
        fp.append(
            FP_Text.factory(
                text="FBRK:autoplaced",
                at=At.factory((0, 0, 0)),
                font=self.font,
                tstamp=str(next(self.tstamp_i)),
                layer="User.5",
            )
        )

    def cleanup(self):
        # delete auto-placed vias
        # determined by their size_drill values
        for via in self.pcb.vias:
            if via.size_drill == self.via_size_drill:
                via.delete()

        for text in self.pcb.text:
            if text.text.endswith("_FBRK_AUTO"):
                text.delete()

        # TODO maybe faebryk layer?
        CLEAN_LAYERS = re.compile(r"^User.[2-9]$")
        for geo in self.pcb.geoms:
            if CLEAN_LAYERS.match(geo.layer_name) is None:
                continue
            geo.delete()
        self.pcb.garbage_collect()

    @staticmethod
    def get_fp(cmp) -> Footprint:
        return cmp.get_trait(PCB_Transformer.has_linked_kicad_footprint).get_fp()

    def get_net(self, net: FNet) -> Net:
        nets = {pcb_net.name: pcb_net for pcb_net in self.pcb.nets}
        return nets[net.get_trait(has_overriden_name).get_name()]

    def get_edge(self) -> list[GR_Line.Coord]:
        def geo_to_lines(
            geo: Geom, parent: PCB_Node
        ) -> list[tuple[GR_Line.Coord, GR_Line.Coord]]:
            lines = []
            assert geo.sym is not None

            if isinstance(geo, GR_Line):
                lines = [(geo.start, geo.end)]
            elif isinstance(geo, Arc):
                arc = (geo.start, geo.mid, geo.end)
                lines = self.Geometry.approximate_arc(*arc, resolution=10)
            elif isinstance(geo, Rect):
                rect = (geo.start, geo.end)

                c0 = (rect[0][0], rect[1][1])
                c1 = (rect[1][0], rect[0][1])

                l0 = (rect[0], c0)
                l1 = (rect[0], c1)
                l2 = (rect[1], c0)
                l3 = (rect[1], c1)

                lines = [l0, l1, l2, l3]
            else:
                raise NotImplementedError(f"Unsupported type {type(geo)}: {geo}")

            if geo.sym.startswith("fp"):
                assert isinstance(parent, Footprint)
                lines = [
                    tuple(self.Geometry.abs_pos(parent.at.coord, x) for x in line)
                    for line in lines
                ]

            return lines

        def quantize_line(line: tuple[GR_Line.Coord, GR_Line.Coord]):
            DIGITS = 2
            return tuple(tuple(round(c, DIGITS) for c in p) for p in line)

        lines: list[tuple[GR_Line.Coord, GR_Line.Coord]] = [
            quantize_line(line)
            for sub_lines in [
                geo_to_lines(pcb_geo, self.pcb)
                for pcb_geo in self.pcb.geoms
                if pcb_geo.layer_name == "Edge.Cuts"
            ]
            + [
                geo_to_lines(fp_geo, fp)
                for fp in self.pcb.footprints
                for fp_geo in fp.geoms
                if fp_geo.layer_name == "Edge.Cuts"
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

        return get_geometry(polys, 0).exterior.coords

    T = TypeVar("T")

    @staticmethod
    def flipped(input_list: list[tuple[T, int]]) -> list[tuple[T, int]]:
        return [(x, (y + 180) % 360) for x, y in reversed(input_list)]

    def gen_tstamp(self):
        return str(next(self.tstamp_i))

    def insert(self, node: PCB_Node):
        self.pcb.append(node)

    # TODO
    def insert_plane(self, layer: str, net: Any):
        raise NotImplementedError()

    def insert_via(self, coord: tuple[float, float], net: str):
        self.insert(
            Via.factory(
                at=At.factory(coord),
                size_drill=self.via_size_drill,
                layers=("F.Cu", "B.Cu"),
                net=net,
                tstamp=self.gen_tstamp(),
            )
        )

    def insert_text(self, text: str, at: "At", font: FP_Text.Font, permanent: bool):
        # TODO find a better way for this
        if not permanent:
            text = text + "_FBRK_AUTO"
        self.insert(
            GR_Text.factory(
                text=text,
                at=at,
                layer="F.SilkS",
                font=font,
                tstamp=self.gen_tstamp(),
            )
        )

    def insert_track(
        self,
        net_id: int,
        points: list[Segment.Coord],
        width: float,
        layer: str,
        arc: bool,
    ):
        # TODO marker

        parts = []
        if arc:
            start_and_ends = points[::2]
            for s, e, m in zip(start_and_ends[:-1], start_and_ends[1:], points[1::2]):
                parts.append(
                    Segment_Arc.factory(
                        s,
                        m,
                        e,
                        width=width,
                        layer=layer,
                        net_id=net_id,
                        tstamp=self.gen_tstamp(),
                    )
                )
        else:
            for s, e in zip(points[:-1], points[1:]):
                parts.append(
                    Segment.factory(
                        s,
                        e,
                        width=width,
                        layer=layer,
                        net_id=net_id,
                        tstamp=self.gen_tstamp(),
                    )
                )

        for part in parts:
            self.insert(part)

    def insert_geo(self, geo: Geom):
        self.insert(geo)

    @staticmethod
    def get_corresponding_fp(
        intf: ModuleInterface,
    ) -> tuple[Core_Footprint, Module]:
        obj = intf

        while not obj.has_trait(has_footprint):
            parent = obj.get_parent()
            if parent is None:
                raise Exception
            obj = parent[0]

        assert isinstance(obj, Module)
        return obj.get_trait(has_footprint).get_footprint(), obj

    @staticmethod
    def get_pad(intf: ModuleInterface) -> tuple[Footprint, Pad]:
        cfp, obj = PCB_Transformer.get_corresponding_fp(intf)
        pin_map = cfp.get_trait(has_kicad_footprint).get_pin_names()
        cfg_if = [
            (pin, name) for pin, name in pin_map.items() if intf.is_connected_to(pin)
        ]
        assert len(cfg_if) == 1

        pin_name = cfg_if[0][1]

        fp = PCB_Transformer.get_fp(obj)
        pad = fp.get_pad(pin_name)

        return fp, pad

    def get_copper_layers(self):
        COPPER = re.compile(r"^.*\.Cu$")

        return {name for name in self.pcb.layer_names if COPPER.match(name) is not None}

    def get_copper_layers_pad(self, pad: Pad):
        COPPER = re.compile(r"^.*\.Cu$")

        all_layers = self.pcb.layer_names

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

    def insert_via_next_to(self, intf: ModuleInterface, clearance: tuple[float, float]):
        fp, pad = self.get_pad(intf)

        rel_target = tuple(map(add, pad.at.coord, clearance))
        coord = self.Geometry.abs_pos(fp.at.coord, rel_target)

        self.insert_via(coord[:2], pad.net)

        # print("Inserting via for", ".".join([y for x,y in intf.get_hierarchy()]),
        # "at:", coord, "in net:", net)
        ...

    def insert_via_triangle(
        self, intfs: list[ModuleInterface], depth: float, clearance: float
    ):
        # get pcb pads
        fp_pads = list(map(self.get_pad, intfs))
        pads = [x[1] for x in fp_pads]
        fp = fp_pads[0][0]

        # from first & last pad
        rect = [pads[-1].at.coord[i] - pads[0].at.coord[i] for i in range(2)]
        assert 0 in rect
        width = [p for p in rect if p != 0][0]
        start = pads[0].at.coord

        # construct triangle
        shape = self.Geometry.triangle(
            self.Geometry.abs_pos(fp.at.coord, start),
            width=width,
            depth=depth,
            count=len(pads),
        )

        # clearance
        shape = self.Geometry.translate(
            tuple([clearance if x != 0 else 0 for x in rect]), shape
        )

        # place vias
        for pad, point in zip(pads, shape):
            self.insert_via(point, pad.net)

    def insert_via_line(
        self,
        intfs: list[ModuleInterface],
        length: float,
        clearance: float,
        angle_deg: float,
    ):
        raise NotImplementedError()
        # get pcb pads
        fp_pads = list(map(self.get_pad, intfs))
        pads = [x[1] for x in fp_pads]
        fp = fp_pads[0][0]

        # from first & last pad
        start = pads[0].at.coord
        abs_start = self.Geometry.abs_pos(fp.at.coord, start)

        shape = self.Geometry.line(
            start=abs_start,
            length=length,
            count=len(pads),
        )

        shape = self.Geometry.rotate(
            axis=abs_start[:2],
            structure=shape,
            angle_deg=angle_deg,
        )

        # clearance
        shape = self.Geometry.translate((clearance, 0), shape)

        # place vias
        for pad, point in zip(pads, shape):
            self.insert_via(point, pad.net)

    def insert_via_line2(
        self,
        intfs: list[ModuleInterface],
        length: tuple[float, float],
        clearance: tuple[float, float],
    ):
        # get pcb pads
        fp_pads = list(map(self.get_pad, intfs))
        pads = [x[1] for x in fp_pads]
        fp = fp_pads[0][0]

        # from first & last pad
        start = tuple(map(add, pads[0].at.coord, clearance))
        abs_start = self.Geometry.abs_pos(fp.at.coord, start)

        shape = self.Geometry.line2(
            start=abs_start,
            end=self.Geometry.abs_pos(abs_start, length),
            count=len(pads),
        )

        # place vias
        for pad, point in zip(pads, shape):
            self.insert_via(point, pad.net)

    # Positioning ------------------------------------------------------------
    def move_footprints(self):
        # position modules with defined positions
        pos_mods: set[Module] = {
            gif.node
            for gif in self.graph.G.nodes
            if gif.node.has_trait(has_pcb_position)
            and gif.node.has_trait(self.has_linked_kicad_footprint)
        }
        logger.info(f"Positioning {len(pos_mods)} footprints")

        for module in pos_mods:
            fp = module.get_trait(self.has_linked_kicad_footprint).get_fp()
            coord = module.get_trait(has_pcb_position).get_position()
            layer_name = {
                has_pcb_position.layer_type.TOP_LAYER: "F.Cu",
                has_pcb_position.layer_type.BOTTOM_LAYER: "B.Cu",
            }

            if coord[3] == has_pcb_position.layer_type.NONE:
                raise Exception(f"Component {module}({fp.name}) has no layer defined")

            logger.info(f"Placing {fp.name} at {coord} layer {layer_name[coord[3]]}")
            self.move_fp(fp, coord[:3], layer_name[coord[3]])

    # Geometry ----------------------------------------------------------------
    class Geometry:
        Point2D = tuple[float, float]
        # TODO fix all Point2D functions to use Point
        Point = has_pcb_position.Point

        @staticmethod
        def mirror(axis: tuple[float | None, float | None], structure: list[Point2D]):
            return [
                (
                    2 * axis[0] - x if axis[0] is not None else x,
                    2 * axis[1] - y if axis[1] is not None else y,
                )
                for (x, y) in structure
            ]

        @staticmethod
        def abs_pos(parent: Point, child: Point) -> Point:
            rot_deg = parent[2] + child[2]

            rot = rot_deg / 360 * 2 * math.pi

            x, y = parent[:2]
            cx, cy = child[:2]

            rx = round(cx * math.cos(rot) + cy * math.sin(rot), 2)
            ry = round(-cx * math.sin(rot) + cy * math.cos(rot), 2)

            # print(f"Rotate {round(cx,2),round(cy,2)},
            # by {round(rot,2),parent[2]} to {rx,ry}")

            # TODO not sure what this is supposed to do
            # for i in range(2, len(parent)):
            #    if len(child) <= i:
            #        continue
            #    if parent[i] != 0 and child[i] != 0:
            #        logger.warn(f"Adding non-zero values: {parent[i]=} + {child[i]=}")

            # TODO check if this works everywhere
            out = (
                # XY
                x + rx,
                y + ry,
                # ROT
                *(c1 + c2 for c1, c2 in zip(parent[2:3], child[2:3])),
                # Layer
                *child[3:],
            )

            return out

        @staticmethod
        def translate(vec: Point2D, structure: list[Point2D]) -> list[Point2D]:
            return [tuple(map(add, vec, point)) for point in structure]

        @classmethod
        def rotate(
            cls, axis: Point2D, structure: list[Point2D], angle_deg: float
        ) -> list[Point2D]:
            theta = np.radians(angle_deg)
            c, s = np.cos(theta), np.sin(theta)
            R = np.array(((c, -s), (s, c)))

            return cls.translate(
                (-axis[0], -axis[1]),
                [
                    tuple(R @ np.array(point))
                    for point in cls.translate(axis, structure)
                ],
            )

        C = TypeVar("C", tuple[float, float], tuple[float, float, float])

        @staticmethod
        def triangle(start: C, width: float, depth: float, count: int):
            x1, y1 = start[:2]

            n = count - 1
            cy = width / n

            ys = [round(y1 + cy * i, 2) for i in range(count)]
            xs = [
                round(x1 + depth * (1 - abs(1 - 1 / n * i * 2)), 2)
                for i in range(count)
            ]

            return list(zip(xs, ys))

        @staticmethod
        def line(start: C, length: float, count: int):
            x1, y1 = start[:2]

            n = count - 1
            cy = length / n

            ys = [round(y1 + cy * i, 2) for i in range(count)]
            xs = [x1] * count

            return list(zip(xs, ys))

        @staticmethod
        def line2(start: C, end: C, count: int):
            x1, y1 = start[:2]
            x2, y2 = end[:2]

            n = count - 1
            cx = (x2 - x1) / n
            cy = (y2 - y1) / n

            ys = [round(y1 + cy * i, 2) for i in range(count)]
            xs = [round(x1 + cx * i, 2) for i in range(count)]

            return list(zip(xs, ys))

        @staticmethod
        def find_circle_center(p1, p2, p3):
            """
            Finds the center of the circle passing through the three given points.
            """
            # Compute the midpoints
            mid1 = (p1 + p2) / 2
            mid2 = (p2 + p3) / 2

            # Compute the slopes of the lines
            m1 = (p2[1] - p1[1]) / (p2[0] - p1[0])
            m2 = (p3[1] - p2[1]) / (p3[0] - p2[0])

            # The slopes of the perpendicular bisectors
            perp_m1 = -1 / m1
            perp_m2 = -1 / m2

            # Equations of the perpendicular bisectors
            # y = perp_m1 * (x - mid1[0]) + mid1[1]
            # y = perp_m2 * (x - mid2[0]) + mid2[1]

            # Solving for x
            x = (mid2[1] - mid1[1] + perp_m1 * mid1[0] - perp_m2 * mid2[0]) / (
                perp_m1 - perp_m2
            )

            # Solving for y using one of the bisector equations
            y = perp_m1 * (x - mid1[0]) + mid1[1]

            return np.array([x, y])

        @staticmethod
        def approximate_arc(p_start, p_mid, p_end, resolution=10):
            p_start, p_mid, p_end = (np.array(p) for p in (p_start, p_mid, p_end))

            # Calculate the center of the circle
            center = PCB_Transformer.Geometry.find_circle_center(p_start, p_mid, p_end)

            # Calculate start, mid, and end angles
            start_angle = np.arctan2(p_start[1] - center[1], p_start[0] - center[0])
            mid_angle = np.arctan2(p_mid[1] - center[1], p_mid[0] - center[0])
            end_angle = np.arctan2(p_end[1] - center[1], p_end[0] - center[0])

            # Adjust angles if necessary
            if start_angle > mid_angle:
                start_angle -= 2 * np.pi
            if mid_angle > end_angle:
                mid_angle -= 2 * np.pi

            # Radius of the circle
            r = np.linalg.norm(p_start - center)

            # Compute angles of line segment endpoints
            angles = np.linspace(start_angle, end_angle, resolution + 1)

            # Compute points on the arc
            points = np.array(
                [[center[0] + r * np.cos(a), center[1] + r * np.sin(a)] for a in angles]
            )

            # Create line segments
            segments = [(points[i], points[i + 1]) for i in range(resolution)]

            seg_no_np = [(tuple(a), tuple(b)) for a, b in segments]

            return seg_no_np
