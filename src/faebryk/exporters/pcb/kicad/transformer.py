# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import pprint
import re
from abc import abstractmethod
from operator import add
from typing import Any, List, Tuple, TypeVar

import numpy as np
from faebryk.core.core import (
    Module,
    ModuleInterface,
    ModuleInterfaceTrait,
    ModuleTrait,
    Node,
)
from faebryk.core.graph import Graph
from faebryk.library.Electrical import Electrical
from faebryk.library.Footprint import (
    Footprint as FFootprint,
)
from faebryk.library.has_footprint import has_footprint
from faebryk.library.has_kicad_footprint import has_kicad_footprint
from faebryk.library.has_overriden_name import has_overriden_name
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.library.Net import Net as FNet
from faebryk.library.Pad import Pad as FPad
from faebryk.libs.geometry.basic import Geometry
from faebryk.libs.kicad.pcb import (
    PCB,
    UUID,
    Arc,
    At,
    Font,
    Footprint,
    FP_Text,
    Geom,
    GR_Arc,
    GR_Line,
    GR_Text,
    Line,
    Net,
    Pad,
    Rect,
    Segment,
    Segment_Arc,
    Text,
    Via,
    Zone,
)
from faebryk.libs.kicad.pcb import (
    Node as PCB_Node,
)
from faebryk.libs.util import find, flatten

logger = logging.getLogger(__name__)


class PCB_Transformer:
    class has_linked_kicad_footprint(ModuleTrait):
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

    class has_linked_kicad_pad(ModuleInterfaceTrait):
        @abstractmethod
        def get_pad(self) -> tuple[Footprint, Pad]: ...

        @abstractmethod
        def get_transformer(self) -> "PCB_Transformer": ...

    class has_linked_kicad_pad_defined(has_linked_kicad_pad.impl()):
        def __init__(
            self, fp: Footprint, pad: Pad, transformer: "PCB_Transformer"
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
        FONT = Font.factory(
            size=(1 / FONT_SCALE, 1 / FONT_SCALE),
            thickness=0.15 / FONT_SCALE,
        )
        self.font = FONT

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

            g_fp.add_trait(self.has_linked_kicad_footprint_defined(fp, self))
            node.add_trait(self.has_linked_kicad_footprint_defined(fp, self))

            pin_names = g_fp.get_trait(has_kicad_footprint).get_pin_names()
            for fpad in g_fp.IFs.get_all():
                assert isinstance(fpad, FPad)
                pad = fp.get_pad(pin_names[fpad])
                fpad.add_trait(
                    PCB_Transformer.has_linked_kicad_pad_defined(fp, pad, self)
                )

        attached = {
            gif.node: gif.node.get_trait(self.has_linked_kicad_footprint).get_fp()
            for gif in self.graph.G.nodes
            if gif.node.has_trait(self.has_linked_kicad_footprint)
        }
        logger.debug(f"Attached: {pprint.pformat(attached)}")

    def cleanup(self):
        # delete auto-placed objects
        candidates = flatten(
            [self.pcb.vias, self.pcb.segments, self.pcb.text, self.pcb.zones]
        )
        for obj in candidates:
            if self.is_marked(obj):
                obj.delete()

        # TODO maybe faebryk layer?
        CLEAN_LAYERS = re.compile(r"^User.[2-9]$")
        for geo in self.pcb.geoms:
            if CLEAN_LAYERS.match(geo.layer_name) is None:
                continue
            geo.delete()
        self.pcb.garbage_collect()

    T = TypeVar("T")

    @staticmethod
    def flipped(input_list: list[tuple[T, int]]) -> list[tuple[T, int]]:
        return [(x, (y + 180) % 360) for x, y in reversed(input_list)]

    def gen_uuid(self, mark: bool = False):
        return UUID.factory(UUID.gen_uuid(mark="FBRK" if mark else ""))

    @staticmethod
    def is_marked(obj) -> bool:
        return obj.uuid.is_marked("FBRK")

    # Getter ---------------------------------------------------------------------------
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
                lines = Geometry.approximate_arc(*arc, resolution=10)
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
                    tuple(Geometry.abs_pos(parent.at.coord, x) for x in line)
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

    @staticmethod
    def _get_pad(ffp: FFootprint, intf: Electrical):
        pin_map = ffp.get_trait(has_kicad_footprint).get_pin_names()
        pin_name = find(
            pin_map.items(),
            lambda pad_and_name: intf.is_connected_to(pad_and_name[0].IFs.net)
            is not None,
        )[1]

        fp = PCB_Transformer.get_fp(ffp)
        pad = fp.get_pad(pin_name)

        return fp, pad

    @staticmethod
    def get_pad(intf: Electrical) -> tuple[Footprint, Pad, Node]:
        obj, ffp = FFootprint.get_footprint_of_parent(intf)
        fp, pad = PCB_Transformer._get_pad(ffp, intf)

        return fp, pad, obj

    @staticmethod
    def get_pad_pos_any(intf: Electrical) -> list[tuple[FPad, Geometry.Point]]:
        try:
            fpads = FPad.find_pad_for_intf_with_parent_that_has_footprint(intf)
        except ValueError:
            # intf has no parent with footprint
            return []

        return [PCB_Transformer._get_pad_pos(fpad) for fpad in fpads]

    @staticmethod
    def get_pad_pos(intf: Electrical) -> tuple[FPad, Geometry.Point] | None:
        try:
            fpad = FPad.find_pad_for_intf_with_parent_that_has_footprint_unique(intf)
        except ValueError:
            return None

        return PCB_Transformer._get_pad_pos(fpad)

    @staticmethod
    def _get_pad_pos(fpad: FPad):
        fp, pad = fpad.get_trait(PCB_Transformer.has_linked_kicad_pad).get_pad()

        point3d = Geometry.abs_pos(fp.at.coord, pad.at.coord)

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

    def get_layer_id(self, layer: str) -> int:
        copper_layers = {layer: i for i, layer in enumerate(self.get_copper_layers())}
        return copper_layers[layer]

    def get_layer_name(self, layer_id: int) -> str:
        copper_layers = {i: layer for i, layer in enumerate(self.get_copper_layers())}
        return copper_layers[layer_id]

    # Insert ---------------------------------------------------------------------------
    def insert(self, node: PCB_Node, mark: bool = True):
        if hasattr(node, "uuid"):
            node.uuid.uuid = self.gen_uuid(mark=mark).uuid
        self.pcb.append(node)

    # TODO
    def insert_plane(self, layer: str, net: Any):
        raise NotImplementedError()

    def insert_via(
        self, coord: tuple[float, float], net: str, size_drill: tuple[float, float]
    ):
        self.insert(
            Via.factory(
                at=At.factory(coord),
                size_drill=size_drill,
                layers=("F.Cu", "B.Cu"),
                net=net,
                uuid=self.gen_uuid(mark=True),
            )
        )

    def insert_text(self, text: str, at: "At", font: Font, front: bool = True):
        self.insert(
            GR_Text.factory(
                text=text,
                at=at,
                layer=f"{'F' if front else 'B'}.SilkS",
                font=font,
                uuid=self.gen_uuid(mark=True),
                lrjustify=Text.Justify.MIRROR if not front else Text.Justify.LEFT,
                udjustify=Text.Justify.TOP,
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
                        uuid=self.gen_uuid(mark=True),
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
                        uuid=self.gen_uuid(mark=True),
                    )
                )

        for part in parts:
            self.insert(part)

    def insert_geo(self, geo: Geom):
        self.insert(geo)

    def insert_via_next_to(
        self,
        intf: ModuleInterface,
        clearance: tuple[float, float],
        size_drill: tuple[float, float],
    ):
        fp, pad, _ = self.get_pad(intf)

        rel_target = tuple(map(add, pad.at.coord, clearance))
        coord = Geometry.abs_pos(fp.at.coord, rel_target)

        self.insert_via(coord[:2], pad.net, size_drill)

        # print("Inserting via for", ".".join([y for x,y in intf.get_hierarchy()]),
        # "at:", coord, "in net:", net)
        ...

    def insert_via_triangle(
        self,
        intfs: list[ModuleInterface],
        depth: float,
        clearance: float,
        size_drill: tuple[float, float],
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
        shape = Geometry.triangle(
            Geometry.abs_pos(fp.at.coord, start),
            width=width,
            depth=depth,
            count=len(pads),
        )

        # clearance
        shape = Geometry.translate(
            tuple([clearance if x != 0 else 0 for x in rect]), shape
        )

        # place vias
        for pad, point in zip(pads, shape):
            self.insert_via(point, pad.net, size_drill)

    def insert_via_line(
        self,
        intfs: list[ModuleInterface],
        length: float,
        clearance: float,
        angle_deg: float,
        size_drill: tuple[float, float],
    ):
        raise NotImplementedError()
        # get pcb pads
        fp_pads = list(map(self.get_pad, intfs))
        pads = [x[1] for x in fp_pads]
        fp = fp_pads[0][0]

        # from first & last pad
        start = pads[0].at.coord
        abs_start = Geometry.abs_pos(fp.at.coord, start)

        shape = Geometry.line(
            start=abs_start,
            length=length,
            count=len(pads),
        )

        shape = Geometry.rotate(
            axis=abs_start[:2],
            structure=shape,
            angle_deg=angle_deg,
        )

        # clearance
        shape = Geometry.translate((clearance, 0), shape)

        # place vias
        for pad, point in zip(pads, shape):
            self.insert_via(point, pad.net, size_drill)

    def insert_via_line2(
        self,
        intfs: list[ModuleInterface],
        length: tuple[float, float],
        clearance: tuple[float, float],
        size_drill: tuple[float, float],
    ):
        # get pcb pads
        fp_pads = list(map(self.get_pad, intfs))
        pads = [x[1] for x in fp_pads]
        fp = fp_pads[0][0]

        # from first & last pad
        start = tuple(map(add, pads[0].at.coord, clearance))
        abs_start = Geometry.abs_pos(fp.at.coord, start)

        shape = Geometry.line2(
            start=abs_start,
            end=Geometry.abs_pos(abs_start, length),
            count=len(pads),
        )

        # place vias
        for pad, point in zip(pads, shape):
            self.insert_via(point, pad.net, size_drill)

    def get_net_obj_bbox(self, net: Net, layer: str, tolerance=0.0):
        vias = self.pcb.vias
        pads = [(pad, fp) for fp in self.pcb.footprints for pad in fp.pads]

        net_vias = [via for via in vias if via.net == net.id]
        net_pads = [
            (pad, fp) for pad, fp in pads if pad.net == net.id and layer in pad.layers
        ]
        coords = [via.at.coord for via in net_vias] + [
            Geometry.abs_pos(fp.at.coord, pad.at.coord) for pad, fp in net_pads
        ]

        # TODO ugly, better get pcb boundaries
        if not coords:
            coords = [(-1e3, -1e3), (1e3, 1e3)]

        bbox = Geometry.bbox(coords, tolerance=tolerance)

        return Geometry.rect_to_polygon(bbox)

    def insert_zone(self, net: Net, layer: str, polygon: list[Geometry.Point2D]):
        zones = self.pcb.zones

        # check if exists
        zones = self.pcb.zones
        # TODO check bbox
        if any([zone.layer == layer for zone in zones]):
            # raise Exception(f"Zone already exists in {layer=}")
            logger.warning(f"Zone already exists in {layer=}")
            return

        self.insert(
            Zone.factory(
                net=net.id,
                net_name=net.name,
                layer=layer,
                uuid=self.gen_uuid(mark=True),
                name=f"layer_fill_{net.name}",
                polygon=polygon,
            )
        )

    # Positioning ----------------------------------------------------------------------
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

            logger.debug(f"Placing {fp.name} at {coord} layer {layer_name[coord[3]]}")
            self.move_fp(fp, coord[:3], layer_name[coord[3]])

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
        flip = fp.layer != layer

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
                uuid=self.gen_uuid(mark=True),
                layer="User.5",
            )
        )

    # Edge -----------------------------------------------------------------------------
    # TODO: make generic
    def connect_lines_via_radius(
        self,
        line1: Line,
        line2: Line,
        radius: float,
    ) -> Tuple[GR_Line, GR_Arc, GR_Line]:
        # Assert if the endpoints of the lines are not connected
        assert line1.end == line2.start, "The endpoints of the lines are not connected."

        # Assert if the radius is less than or equal to zero
        assert radius > 0, "The radius must be greater than zero."

        v1 = np.array(line1.start) - np.array(line1.end)
        v2 = np.array(line2.end) - np.array(line2.start)
        v1 = v1 / np.linalg.norm(v1)
        v2 = v2 / np.linalg.norm(v2)

        v_middle = v1 * radius + v2 * radius
        v_middle_norm = v_middle / np.linalg.norm(v_middle)
        v_center = v_middle - v_middle_norm * radius

        # calculate the arc center
        arc_center = np.array(line1.end) + v_center

        # calculate the arc start and end points
        arc_end = np.array(line2.start) + v2 * radius
        arc_start = np.array(line1.end) + v1 * radius

        # convert to tuples
        arc_start = tuple(arc_start)
        arc_center = tuple(arc_center)
        arc_end = tuple(arc_end)

        logger.debug(f"{v_middle=}")
        logger.debug(f"{v_middle_norm=}")
        logger.debug(f"{v_center=}")

        logger.debug(f"line intersection: {line1.end} == {line2.start}")
        logger.debug(f"line1: {line1.start} -> {line1.end}")
        logger.debug(f"line2: {line2.start} -> {line2.end}")
        logger.debug(f"v1: {v1}")
        logger.debug(f"v2: {v2}")
        logger.debug(f"v_middle: {v_middle}")
        logger.debug(f"radius: {radius}")
        logger.debug(f"arc_start: {arc_start}")
        logger.debug(f"arc_center: {arc_center}")
        logger.debug(f"arc_end: {arc_end}")

        # Create the arc
        arc = GR_Arc.factory(
            start=arc_start,
            mid=arc_center,
            end=arc_end,
            stroke=GR_Line.Stroke.factory(0.05, "default"),
            layer="Edge.Cuts",
            uuid=self.gen_uuid(mark=True),
        )

        # Create new lines
        new_line1 = GR_Line.factory(
            start=line1.start,
            end=arc_start,
            stroke=GR_Line.Stroke.factory(0.05, "default"),
            layer="Edge.Cuts",
            uuid=self.gen_uuid(mark=True),
        )
        new_line2 = GR_Line.factory(
            start=arc_end,
            end=line2.end,
            stroke=GR_Line.Stroke.factory(0.05, "default"),
            layer="Edge.Cuts",
            uuid=self.gen_uuid(mark=True),
        )

        return new_line1, arc, new_line2

    def create_rectangular_edgecut(
        self,
        width_mm: float,
        height_mm: float,
        rounded_corners: bool = False,
        corner_radius_mm: float = 0.0,
    ) -> List[Geom] | List[GR_Line]:
        """
        Create a rectengular board outline (edge cut)
        """
        # make 4 line objects where the end of the last line is the begining of the next
        lines = [
            GR_Line.factory(
                start=(0, 0),
                end=(width_mm, 0),
                stroke=GR_Line.Stroke.factory(0.05, "default"),
                layer="Edge.Cuts",
                uuid=self.gen_uuid(mark=True),
            ),
            GR_Line.factory(
                start=(width_mm, 0),
                end=(width_mm, height_mm),
                stroke=GR_Line.Stroke.factory(0.05, "default"),
                layer="Edge.Cuts",
                uuid=self.gen_uuid(mark=True),
            ),
            GR_Line.factory(
                start=(width_mm, height_mm),
                end=(0, height_mm),
                stroke=GR_Line.Stroke.factory(0.05, "default"),
                layer="Edge.Cuts",
                uuid=self.gen_uuid(mark=True),
            ),
            GR_Line.factory(
                start=(0, height_mm),
                end=(0, 0),
                stroke=GR_Line.Stroke.factory(0.05, "default"),
                layer="Edge.Cuts",
                uuid=self.gen_uuid(mark=True),
            ),
        ]
        if rounded_corners:
            rectangle_geometry = []
            # calculate from a line pair sharing a corner, a line pair with an arc in
            # between using connect_lines_via_radius.
            # replace the original line pair with the new line pair and arc
            for i in range(len(lines)):
                line1 = lines[i]
                line2 = lines[(i + 1) % len(lines)]
                new_line1, arc, new_line2 = self.connect_lines_via_radius(
                    line1,
                    line2,
                    corner_radius_mm,
                )
                lines[i] = new_line1
                lines[(i + 1) % len(lines)] = new_line2
                rectangle_geometry.append(arc)
            for line in lines:
                rectangle_geometry.append(line)

            return rectangle_geometry
        else:
            # Create the rectangle without rounded corners using lines
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
            if isinstance(geo, GR_Line):
                # plot a line
                plt.plot([geo.start[0], geo.end[0]], [geo.start[1], geo.end[1]])
            elif isinstance(geo, GR_Arc):
                plot_arc(geo.start, geo.mid, geo.end)
                plt.plot([geo.start[0], geo.end[0]], [geo.start[1], geo.end[1]])
        plt.show()

    def set_pcb_outline_complex(
        self,
        geometry: List[Geom] | List[GR_Line],
        remove_existing_outline: bool = True,
    ):
        """
        Create a board outline (edge cut) consisting out of
        different geometries
        """

        # TODO: remove
        # self.plot_board_outline(geometry)

        # remove existing lines on Egde.cuts layer
        if remove_existing_outline:
            for geo in self.pcb.geoms:
                if geo.sym not in ["gr_line", "gr_arc"]:
                    continue
                if geo.layer_name != "Edge.Cuts":
                    continue
                geo.delete()

        # create Edge.Cuts geometries
        for geo in geometry:
            assert (
                geo.layer_name == "Edge.Cuts"
            ), f"Geometry {geo} is not on Edge.Cuts layer"

            self.pcb.append(geo)

        # find bounding box
