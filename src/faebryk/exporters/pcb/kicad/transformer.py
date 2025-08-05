# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import copy
import logging
import re
from collections import defaultdict
from dataclasses import asdict, fields
from enum import Enum, StrEnum, auto
from itertools import pairwise
from math import floor
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    TypeVar,
)

import numpy as np
from deprecated import deprecated
from more_itertools import first
from shapely import Polygon

# import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node
from faebryk.core.trait import TraitNotFound
from faebryk.libs.exceptions import DeprecatedException, UserException, downgrade
from faebryk.libs.geometry.basic import Geometry
from faebryk.libs.kicad.fileformats_common import C_pts
from faebryk.libs.kicad.fileformats_common import (
    gen_uuid as _gen_uuid,
)
from faebryk.libs.kicad.fileformats_latest import (
    UUID,
    C_arc,
    C_circle,
    C_curve,
    C_effects,
    C_footprint,
    C_fp_text,
    C_group,
    C_image,
    C_kicad_pcb_file,
    C_line,
    C_net,
    C_polygon,
    C_rect,
    C_stroke,
    C_table,
    C_text,
    C_text_box,
    C_text_layer,
    C_wh,
    C_xy,
    C_xyr,
    C_xyz,
    E_fill,
    _SingleOrMultiLayer,
)
from faebryk.libs.sexp.dataclass_sexp import filter_fields, visit_dataclass
from faebryk.libs.util import (
    FuncSet,
    KeyErrorNotFound,
    Tree,
    cast_assert,
    dataclass_as_kwargs,
    find,
    groupby,
    hash_string,
    re_in,
    yield_missing,
)

logger = logging.getLogger(__name__)


PCB = C_kicad_pcb_file.C_kicad_pcb
Footprint = PCB.C_pcb_footprint
Pad = Footprint.C_pad
Net = C_net

# TODO remove
GR_Line = C_line
GR_Text = C_text
Font = C_effects.C_font
Zone = PCB.C_zone
Arc = C_arc
Rect = C_rect
Via = PCB.C_via
Line = C_line

Geom = C_line | C_arc | C_rect | C_circle | C_polygon | C_curve

Point = Geometry.Point
Point2D = Geometry.Point2D

Justify = C_effects.C_justify.E_justify
Alignment = tuple[Justify, Justify, Justify]
Alignment_Default = (
    Justify.center_horizontal,
    Justify.center_vertical,
    Justify.normal,
)

if TYPE_CHECKING:
    import faebryk.library._F as F


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
        return [
            obj.gr_lines,
            obj.gr_arcs,
            obj.gr_circles,
            obj.gr_rects,
            obj.gr_curves,
            obj.gr_polys,
        ]
    elif isinstance(obj, Footprint):
        return [obj.fp_lines, obj.fp_arcs, obj.fp_circles, obj.fp_rects]

    raise TypeError()


def get_all_geos(obj: PCB | Footprint) -> list[Geom]:
    candidates = get_all_geo_containers(obj)

    return [geo for geos in candidates for geo in geos]


class PCB_Transformer:
    class has_linked_kicad_footprint(Module.TraitT.decless()):
        """
        Link applied to:
        - Modules which are represented in the PCB
        - F.Footprint which are represented in the PCB
        """

        def __init__(self, fp: Footprint, transformer: "PCB_Transformer") -> None:
            super().__init__()
            self.fp = fp
            self.transformer = transformer

        def get_fp(self):
            return self.fp

        def get_transformer(self):
            return self.transformer

    class has_linked_kicad_pad(ModuleInterface.TraitT.decless()):
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

    class has_linked_kicad_net(ModuleInterface.TraitT.decless()):
        def __init__(self, net: Net, transformer: "PCB_Transformer") -> None:
            super().__init__()
            self.net = net
            self.transformer = transformer

        def get_net(self):
            return self.net

        def get_transformer(self):
            return self.transformer

    def __init__(self, pcb: PCB, graph: Graph, app: Module) -> None:
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

        self._net_number_generator = iter(
            yield_missing({net.number for net in self.pcb.nets})
        )
        """Yield available net numbers"""

        self.default_component_insert_point = C_xyr(x=0, y=0, r=0)

        self.attach()

    def attach(self):
        """Bind footprints and nets from the PCB to the graph."""
        import faebryk.library._F as F

        for node, fp in PCB_Transformer.map_footprints(self.graph, self.pcb).items():
            if node.has_trait(F.has_footprint):
                self.bind_footprint(fp, node)
            else:
                node.add(self.has_linked_kicad_footprint(fp, self))

            fp_props = {
                k: v
                for k, v in fp.property_dict.items()
                if re_in(k, PCB_Transformer.INCLUDE_DESCRIPTIVE_PROPERTIES_FROM_PCB())
            }
            node_props = (
                t.get_properties()
                if (t := node.try_get_trait(F.has_descriptive_properties))
                else {}
            )
            # node takes precedence over fp
            merged = fp_props | node_props
            node.add(F.has_descriptive_properties_defined(merged))

        for f_net, pcb_net in self.map_nets().items():
            self.bind_net(pcb_net, f_net)

    def check_unattached_fps(self):
        """
        Check that all the nodes with a footprint, have a linked footprint in the PCB
        """
        import faebryk.library._F as F

        unattached_nodes = {
            node
            for node, trait in GraphFunctions(self.graph).nodes_with_trait(
                F.has_footprint
            )
            if not node.has_trait(PCB_Transformer.has_linked_kicad_footprint)
        }
        if unattached_nodes:
            raise UserException(
                f"Failed to attach {len(unattached_nodes)} node(s) to footprints: "
                f"{', '.join(f'`{node.get_full_name()}`' for node in unattached_nodes)}"
            )

    @staticmethod
    def map_footprints(graph: Graph, pcb: PCB) -> dict[Module, Footprint]:
        """
        Attach as many nodes <> footprints as possible, and
        return the set of nodes that were missing footprints.
        """
        # Now, try to map between the footprints and the layout
        footprint_map: dict[Module, Footprint] = {}
        fps_by_atopile_addr = {
            f.propertys["atopile_address"].value: f
            for f in pcb.footprints
            if "atopile_address" in f.propertys
        }
        fps_by_path = {f.path: f for f in pcb.footprints if f.path is not None}

        # Also try nodes without footprints, because they might get them later
        for module in GraphFunctions(graph).nodes_of_type(Module):
            atopile_addr = module.get_full_name()

            # First, try to find the footprint by the atopile address
            if fp := fps_by_atopile_addr.get(atopile_addr):
                footprint_map[module] = fp
                continue

            # Then, try to find the footprint by the path (which looks like a UUID)
            hashed_addr = hash_string(atopile_addr)
            # TODO: @v0.4 remove this, it's a fallback for v0.2 designs
            if fp := fps_by_path.get(f"/{hashed_addr}/{hashed_addr}"):
                with downgrade(DeprecatedException):
                    raise DeprecatedException(
                        f"`{module.get_full_name()}` is linked to the layout using v0.2"
                        " mechanism, please save the design to update."
                    )
                footprint_map[module] = fp
                continue

        return footprint_map

    def bind_footprint(self, pcb_fp: Footprint, module: Module):
        """
        Generates links between:
        - Module and PCB Footprint
        - F.Footprint and PCB Footprint
        - F.Pad and PCB Pads
        """
        import faebryk.library._F as F

        module.add(self.has_linked_kicad_footprint(pcb_fp, self))

        # By now, the node being bound MUST have a footprint
        g_fp = module.get_trait(F.has_footprint).get_footprint()
        g_fp.add(self.has_linked_kicad_footprint(pcb_fp, self))
        pin_names = g_fp.get_trait(F.has_kicad_footprint).get_pin_names()
        # F.Pad is a ModuleInterface - don't be tricked
        pcb_pads = FuncSet[Footprint.C_pad](pcb_fp.pads)
        for fpad in g_fp.get_children(direct_only=True, types=ModuleInterface):
            pads = [
                pad
                for pad in pcb_pads
                if pad.name == pin_names[cast_assert(F.Pad, fpad)]
            ]
            pcb_pads -= FuncSet(pads)
            if not pads:
                logger.warning(f"No PCB pads for pad in design: {fpad}")
            fpad.add(self.has_linked_kicad_pad(pcb_fp, pads, self))

        # This may leave some pads on the PCB unlinked to the design
        # This is useful for things like mounting holes, but checks
        # linking less robustly
        if pcb_pads and logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"No pads in design for PCB pads: {pcb_pads}")

    def map_nets(self, match_threshold: float = 0.8) -> dict["F.Net", Net]:
        """
        Create a mapping between the internal nets and the nets defined in the PCB file.

        This relies on linking between the footprints and pads, so must be called after.
        """
        import faebryk.library._F as F

        if match_threshold < 0.5:
            # This is because we rely on being >50% sure to ensure we're the most
            # likely match.
            raise ValueError("match_threshold must be at least 0.5")

        known_nets: dict["F.Net", Net] = {}
        pcb_nets_by_name: dict[str, Net] = {n.name: n for n in self.pcb.nets}
        mapped_net_names = set()

        named_nets = {
            n
            for n in GraphFunctions(self.graph).nodes_of_type(F.Net)
            if n.has_trait(F.has_overriden_name)
        }

        for net in named_nets:
            total_pads = 0
            # map from net name to the number of pads we've
            # linked corroborating its accuracy
            net_candidates: Mapping[str, int] = defaultdict(int)

            for ato_pad, ato_fp in net.get_connected_pads().items():
                if pcb_pad_t := ato_pad.try_get_trait(
                    PCB_Transformer.has_linked_kicad_pad
                ):
                    # In the (strange) case something's handeled by another transformer,
                    # we skip it without counting it towards the total pads.
                    if pcb_pad_t.get_transformer() is not self:
                        continue

                    pcb_fp, pcb_pads = pcb_pad_t.get_pad()

                    # This practically means that if the pads to which a net is
                    # connected varies within a single component, we're going to ignore
                    # it. This could probably be improved to be a little more subtle
                    # within-component net matching, for later
                    net_names = set(
                        pcb_pad.net.name if pcb_pad.net is not None else None
                        for pcb_pad in pcb_pads
                    )
                    conflicting = net_names & mapped_net_names
                    net_names -= mapped_net_names

                    if (
                        len(net_names) == 1
                        and (net_name := first(net_names)) is not None
                    ):
                        net_candidates[net_name] += 1
                    elif len(net_names) == 0 and conflicting:
                        logger.warning(
                            "Net name has already been used: %s",
                            ", ".join(f"`{n}`" for n in conflicting),
                        )

                total_pads += 1

            if net_candidates:
                best_net_name = max(net_candidates, key=lambda x: net_candidates[x])
                if (
                    best_net_name
                    and net_candidates[best_net_name] > total_pads * match_threshold
                ):
                    known_nets[net] = pcb_nets_by_name[best_net_name]
                    mapped_net_names.add(best_net_name)

        return known_nets

    def bind_net(self, pcb_net: Net, net: "F.Net"):
        net.add(self.has_linked_kicad_net(pcb_net, self))

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

    def get_net(self, net: "F.Net") -> Net:
        import faebryk.library._F as F

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

        content = [
            geo
            for geo in get_all_geos(fp)
            if any(layer in layers for layer in geo.get_layers())
        ]

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
                if "Edge.Cuts" in pcb_geo.get_layers()
            ]
            + [
                geo_to_lines(fp_geo, fp)
                for fp in self.pcb.footprints
                for fp_geo in get_all_geos(fp)
                if "Edge.Cuts" in fp_geo.get_layers()
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
    def _get_pad(ffp: "F.Footprint", intf: "F.Electrical"):
        import faebryk.library._F as F

        pin_map = ffp.get_trait(F.has_kicad_footprint).get_pin_names()
        pin_name = find(
            pin_map.items(),
            lambda pad_and_name: intf.is_connected_to(pad_and_name[0].net),
        )[1]

        fp = PCB_Transformer.get_fp(ffp)
        pad = find(fp.pads, lambda p: p.name == pin_name)

        return fp, pad

    @staticmethod
    def get_pad(intf: "F.Electrical") -> tuple[Footprint, Pad, Node]:
        obj, ffp = F.Footprint.get_footprint_of_parent(intf)
        fp, pad = PCB_Transformer._get_pad(ffp, intf)

        return fp, pad, obj

    @staticmethod
    def get_pad_pos_any(intf: "F.Electrical"):
        try:
            fpads = F.Pad.find_pad_for_intf_with_parent_that_has_footprint(intf)
        except KeyErrorNotFound:
            # intf has no parent with footprint
            return []

        return [PCB_Transformer.get_fpad_pos(fpad) for fpad in fpads]

    @staticmethod
    def get_pad_pos(intf: "F.Electrical"):
        try:
            fpad = F.Pad.find_pad_for_intf_with_parent_that_has_footprint_unique(intf)
        except ValueError:
            return None

        return PCB_Transformer.get_fpad_pos(fpad)

    @staticmethod
    def get_fpad_pos(fpad: "F.Pad"):
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
        # TODO this doesnt work for every type (e.g arc_segment, gr_lines)
        # see get_container for better solution
        key = prefix + type(node).__name__.removeprefix("C_") + "s"

        assert hasattr(root, key)

        target = getattr(root, key)
        assert isinstance(target, list)
        assert all(isinstance(x, type(node)) for x in target)
        return target

    @staticmethod
    def get_pcb_container[R](obj: R, pcb: PCB) -> list[R]:
        match obj:
            case PCB.C_pcb_footprint():
                return pcb.footprints  # type: ignore
            case PCB.C_segment():
                return pcb.segments  # type: ignore
            case PCB.C_arc_segment():
                return pcb.arcs  # type: ignore
            case PCB.C_via():
                return pcb.vias  # type: ignore
            case PCB.C_zone():
                return pcb.zones  # type: ignore
            case C_line():
                return pcb.gr_lines  # type: ignore
            case C_arc():
                return pcb.gr_arcs  # type: ignore
            case C_rect():
                return pcb.gr_rects  # type: ignore
            case C_circle():
                return pcb.gr_circles  # type: ignore
            case C_polygon():
                return pcb.gr_polys  # type: ignore
            case C_curve():
                return pcb.gr_curves  # type: ignore
            case C_text():
                return pcb.gr_texts  # type: ignore
            case C_text_box():
                return pcb.gr_text_boxs  # type: ignore
            case C_image():
                return pcb.images  # type: ignore
            case C_table():
                return pcb.tables  # type: ignore
            case _:
                raise TypeError(f"Unsupported object type: {type(obj)}")

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
            if any(
                [zone.layers is not None and layer in zone.layers for zone in zones]
            ):
                logger.warning(f"Zone already exists in {layer=}")
                return

        self.pcb.zones.append(
            Zone(
                net=net.number,
                net_name=net.name,
                layers=layers if len(layers) > 1 else None,
                uuid=self.gen_uuid(mark=True),
                name=f"layer_fill_{net.name}",
                polygon=C_polygon(pts=C_pts([point2d_to_coord(p) for p in polygon])),
                min_thickness=0.2,
                filled_areas_thickness=False,
                fill=Zone.C_fill(
                    enable=Zone.C_fill.E_yes.yes,
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
        group = C_group(
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
                fill=E_fill.yes,
                layer=layer,
                uuid=self.gen_uuid(mark=True),
            )
        )

    def insert_jlcpcb_serial(
        self,
        center_at: C_xyr,
        layer="F.SilkS",
    ):
        assert layer.endswith("SilkS"), (
            "JLCPCB serial number must be on silk screen layer"
        )
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
        import faebryk.library._F as F

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
            to = C_xyr(*coord[:3])
            self.move_fp(fp, to, layer)

            # Label
            if not any([x.text == "FBRK:autoplaced" for x in fp.fp_texts]):
                rot_angle = (to.r - fp.at.r) % 360
                fp.fp_texts.append(
                    C_fp_text(
                        type=C_fp_text.E_type.user,
                        text="FBRK:autoplaced",
                        at=C_xyr(0, 0, rot_angle),
                        effects=C_fp_text.C_fp_text_effects(font=self.font),
                        uuid=self.gen_uuid(mark=True),
                        layer=C_text_layer("User.5"),
                    )
                )

    @staticmethod
    def move_fp(fp: Footprint, coord: C_xyr, layer: str):
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

            # Mirror the footprint geometry about the Y-axis when flipping layers
            # so that everything remains readable from the top view.
            for pad in fp.pads:
                pad.layers = [_flip(x) for x in pad.layers]
                # Mirror pad centre and rotation
                pad.at.y = -pad.at.y
                if pad.at.r:
                    pad.at.r = (360 - pad.at.r) % 360

            # Mirror the remaining primitives inside the footprint.
            for obj in get_all_geos(fp) + fp.fp_texts + list(fp.propertys.values()):
                # Objects that expose an `at` attribute (text & properties)
                if isinstance(obj, (C_fp_text, C_footprint.C_property)):
                    obj.at.y = -obj.at.y
                    if obj.at.r:
                        obj.at.r = (360 - obj.at.r) % 360

                # Geometric primitives -------------------------------------------------
                if isinstance(obj, (C_line, C_rect)):
                    obj.start.y = -obj.start.y
                    obj.end.y = -obj.end.y
                elif isinstance(obj, C_arc):
                    obj.start.y = -obj.start.y
                    obj.mid.y = -obj.mid.y
                    obj.end.y = -obj.end.y
                elif isinstance(obj, C_circle):
                    obj.center.y = -obj.center.y
                    obj.end.y = -obj.end.y
                elif isinstance(obj, (C_polygon, C_curve)) and hasattr(obj, "pts"):
                    # Flip every stored point; keep X, negate Y
                    obj.pts.xys = [pt.__class__(pt.x, -pt.y) for pt in obj.pts.xys]  # type: ignore[attr-defined]

                if isinstance(obj, C_footprint.C_property):
                    obj = obj.layer
                if isinstance(obj, C_fp_text):
                    obj = obj.layer

                match obj:
                    case _SingleOrMultiLayer():
                        obj.apply_to_layers(_flip)
                    case _:
                        obj.layer = _flip(obj.layer)

    @staticmethod
    def move_object(obj: Any, vector: C_xy):
        match obj:
            case PCB.C_segment():
                obj.start += vector
                obj.end += vector
            case PCB.C_arc_segment():
                obj.start += vector
                obj.mid += vector
                obj.end += vector
            case PCB.C_via():
                obj.at += vector
            case PCB.C_zone():
                obj.polygon.pts.xys = [pt + vector for pt in obj.polygon.pts.xys]
                for p in obj.filled_polygon:
                    p.pts.xys = [pt + vector for pt in p.pts.xys]
            case C_line():
                obj.start += vector
                obj.end += vector
            case C_arc():
                obj.start += vector
                obj.mid += vector
                obj.end += vector
            case C_circle():
                obj.center += vector
                obj.end += vector
            case C_rect():
                obj.start += vector
                obj.end += vector
            case C_polygon():
                obj.pts.xys = [pt + vector for pt in obj.pts.xys]
            case C_curve():
                obj.pts.xys = [pt + vector for pt in obj.pts.xys]
            case C_text():
                obj.at += vector
            case C_text_box():
                obj.start += vector
                if obj.end:
                    obj.end += vector
                if obj.pts:
                    obj.pts[:] = [pt + vector for pt in obj.pts]
            case C_image():
                obj.at += vector
            case C_table():
                for cell in obj.cells.table_cells:
                    cell.start += vector
                    if cell.end:
                        cell.end += vector
                    if cell.pts:
                        cell.pts[:] = [pt + vector for pt in cell.pts]
            case _:
                raise TypeError(f"Unsupported object type: {type(obj)}")

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
        arc_start = point2d_to_coord(tuple(arc_start))  # type: ignore
        arc_center = point2d_to_coord(tuple(arc_center))  # type: ignore
        arc_end = point2d_to_coord(tuple(arc_end))  # type: ignore

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
            layers=["Edge.Cuts"],
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
                if "Edge.Cuts" not in geo.get_layers():
                    continue
                self.delete_geo(geo)

        # round corners between lines
        if corner_radius_mm > 0:
            geometry = self.round_corners(geometry, corner_radius_mm)

        # create Edge.Cuts geometries
        for geo in geometry:
            assert "Edge.Cuts" in geo.get_layers(), (
                f"Geometry {geo} is not on Edge.Cuts layer"
            )

            self.insert_geo(geo)

        # find bounding box

    # Silkscreen -----------------------------------------------------------------------
    class Side(Enum):
        TOP = auto()
        BOTTOM = auto()
        LEFT = auto()
        RIGHT = auto()

    def hide_all_designators(
        self,
    ) -> None:
        for _, fp in self.get_all_footprints():
            fp.propertys["Reference"].hide = True

            for txt in [txt for txt in fp.fp_texts if txt.text == "${REFERENCE}"]:
                txt.effects.hide = True

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
        try:
            import git

            try:
                repo = git.Repo(search_parent_directories=True)
                git_human_version = repo.git.describe("--always")
            except (
                git.InvalidGitRepositoryError,
                git.NoSuchPathError,
                git.GitCommandError,
            ):
                logger.warning("Cannot get git project version")
                git_human_version = "Cannot get git project version"
        except ImportError:
            # Fall back to direct string if git executable is not available
            logger.warning("git executable not installed, cannot get git version")
            git_human_version = "git executable not installed"

        self.insert_text(
            text=git_human_version,
            at=center_at,
            layer=layer,
            font=font,
            alignment=alignment,
            knockout=knockout,
        )

    # Netlist application --------------------------------------------------------------
    def _fp_common_fields_dict(self, lib_footprint: C_footprint) -> dict[str, Any]:
        """Generate a dict of the common fields of a lib footprint and pcb footprint"""
        return {
            field.name: getattr(lib_footprint, field.name)
            for field in fields(C_footprint)
        }

    @staticmethod
    def _hash_lib_fp(lib_fp: C_footprint) -> str:
        dict_ = asdict(filter_fields(lib_fp, ["uuid"]))

        # Ignore the name field. It's not meaningful and we override it
        dict_["name"] = None

        return hash_string(repr(dict_))

    _FP_LIB_HASH = "__atopile_lib_fp_hash__"

    def _set_lib_fp_hash(
        self, footprint: Footprint, lib_footprint: C_footprint
    ) -> None:
        """Create a hidden property which stores the original lib footprint hash
        so we can detect if the footprint has truly been updated, or if it's
        merely been renamed"""
        footprint.propertys[self._FP_LIB_HASH] = self._make_fp_property(
            property_name=self._FP_LIB_HASH,
            layer="User.9",
            value=self._hash_lib_fp(lib_footprint),
            uuid=self.gen_uuid(mark=True),
        )

    def insert_footprint(
        self, lib_footprint: C_footprint, at: C_xyr | None = None
    ) -> Footprint:
        """Insert a footprint into the pcb, at optionally a specific position"""
        if at is None:
            # Copy the data structure so if we later mutate it we don't
            # end up w/ those changes everywhere
            at = copy.deepcopy(self.default_component_insert_point)

        lib_attrs = self._fp_common_fields_dict(lib_footprint)

        lib_attrs["pads"] = [
            C_kicad_pcb_file.C_kicad_pcb.C_pcb_footprint.C_pad(
                **{
                    # Cannot use asdict because it converts children dataclasses too
                    **(dataclass_as_kwargs(p)),
                    # We have to handle the rotation separately because
                    # it must consider the rotation of the parent footprint
                    "at": C_xyr(x=p.at.x, y=p.at.y, r=p.at.r + at.r),
                },
            )
            for p in lib_footprint.pads
        ]

        footprint = Footprint(
            uuid=self.gen_uuid(mark=True),
            at=at,
            **lib_attrs,
        )

        self._set_lib_fp_hash(footprint, lib_footprint)

        self.pcb.footprints.append(footprint)

        return footprint

    class BoardSide(StrEnum):
        FRONT = "F.Cu"
        BACK = "B.Cu"

    def _set_footprint_side(
        self, footprint: Footprint, side: BoardSide, logger: logging.Logger
    ) -> None:
        """Set the side a footprint is on by mutating the footprint."""
        # First, check the side the footprint's currently on
        current_side = self.BoardSide(footprint.layer)

        # If the side is the same, do nothing
        if current_side == side:
            return

        # FIXME: this function is currently limited in it's ability to make these flips
        # This means it's liable to mangle the footprint's data on update.
        if ref_prop := footprint.propertys.get("Reference"):
            ref = ref_prop.value
        else:
            ref = "Unknown"

        logger.warning(f"Flipping {ref} side. Scrutinize this footprint in the PCB.")

        # Otherwise, flip the footprint to the other side
        # FIXME: we're flipping based on the naming conventiong of "F." and "B."
        # there are no guarantees that this will be robust with new versions of KiCAD
        def _flip(layer: str) -> str:
            if layer.startswith("F."):
                return layer.replace("F.", "B.", 1)
            elif layer.startswith("B."):
                return layer.replace("B.", "F.", 1)

            # User.* layers, for example, aren't flipped and that's fine
            return layer

        def _backup_flip(obj):
            """Shitty flip function which should only be used as a backup."""
            if obj is None:
                return

            for it in visit_dataclass(obj):
                obj = it.value
                path = it.path
                name_path = it.name_path

                # This only works for strings, so skip everything else
                if not isinstance(obj, str):
                    continue

                if len(name_path) < 2:
                    continue

                # path ends with: [..., container, str]
                container = path[-2]

                # objects that have a "layer" property
                if name_path[-2] == "layer" and hasattr(container, "layer"):
                    container.layer = _flip(obj)

                # dicts which have a "layer" key
                elif name_path[-2] == "[layer]" and isinstance(container, dict):
                    # This is based on how dataclass_dfs serialises names
                    assert "layer" in container
                    container["layer"] = _flip(obj)

                # lists which have a "layer" key
                # name_path ends with: [..., "layer", list, str]
                elif (
                    len(name_path) > 2
                    and name_path[-3]
                    in [
                        "layer",
                        "layers",
                        "[layer]",
                        "[layers]",
                    ]
                    and isinstance(container, list)
                ):
                    # Replace the layer string with the flipped one
                    container[container.index(obj)] = _flip(obj)

        # Flip the pads
        for pad in footprint.pads:
            pad.layers = [_flip(lay) for lay in pad.layers]

            # Flip the primitives
            # FIXME: flip pad primitives
            _backup_flip(pad.unknown)

        # Flip the properties
        for prop in footprint.propertys.values():
            prop.layer.layer = _flip(prop.layer.layer)

        # Flip primitives
        for line in footprint.fp_lines:
            line.apply_to_layers(_flip)

        for arc in footprint.fp_arcs:
            arc.apply_to_layers(_flip)

        for circle in footprint.fp_circles:
            circle.apply_to_layers(_flip)

        for rect in footprint.fp_rects:
            rect.apply_to_layers(_flip)

        for text in footprint.fp_texts:
            text.layer.layer = _flip(text.layer.layer)

        for polygon in footprint.fp_poly:
            polygon.apply_to_layers(_flip)

        # Flip anything unknown
        _backup_flip(footprint.unknown)

        # Mark the footprint as being on the other side
        footprint.layer = _flip(footprint.layer)

    def update_footprint_from_lib(
        self, footprint: Footprint, lib_footprint: C_footprint
    ) -> Footprint:
        """
        Update a footprint with all the properties specified in the lib footprint.

        This will disconnect the footprint from any nets - which subsequentially
        must be reconnected.
        """
        original_side = self.BoardSide(footprint.layer)

        updates = self._fp_common_fields_dict(lib_footprint)
        updates["pads"] = [
            C_kicad_pcb_file.C_kicad_pcb.C_pcb_footprint.C_pad(
                **{
                    # Cannot use asdict because it converts children dataclasses too
                    **dataclass_as_kwargs(p),
                    # We have to handle the rotation separately because
                    # because it must consider the rotation of the parent footprint
                    "at": C_xyr(x=p.at.x, y=p.at.y, r=p.at.r + footprint.at.r),
                },
            )
            for p in lib_footprint.pads
        ]
        updates["propertys"] = {
            **footprint.propertys,
            **updates["propertys"],
        }
        for name, update in updates.items():
            setattr(footprint, name, update)

        # Update the lib footprint hash, so we can avoid unnecessary updates later
        self._set_lib_fp_hash(footprint, lib_footprint)

        # Set the boardside of the footprint
        self._set_footprint_side(footprint, original_side, logger)

        return footprint

    def remove_footprint(self, footprint: Footprint) -> None:
        """Remove a footprint from the pcb"""
        self.pcb.footprints.remove(footprint)

    def insert_net(self, name: str) -> Net:
        """Insert a net into the pcb and return it"""
        net = Net(name=name, number=next(self._net_number_generator))
        self.pcb.nets.append(net)
        return net

    def remove_net(self, net: Net):
        """Remove a net from the pcb"""
        self.pcb.nets.remove(net)

        # Disconnect pads on footprints
        for fp in self.pcb.footprints:
            for pad in fp.pads:
                if pad.net is not None and pad.net.number == net.number:
                    pad.net.name = ""
                    pad.net.number = 0

        # Disconnect zones
        for zone in self.pcb.zones:
            if zone.net == net.number and zone.net_name == net.name:
                zone.net_name = ""
                zone.net = 0

        # Disconnect vias, and routing
        for route in self.pcb.segments + self.pcb.arcs + self.pcb.vias:
            if route.net == net.number:
                route.net = 0

    def rename_net(self, net: Net, new_name: str):
        """Rename a new, including all it's connected pads"""
        # This is what does the renaming on the net at the top-level
        net.name = new_name

        # Update all the footprints
        for fp in self.pcb.footprints:
            for pad in fp.pads:
                if pad.net is not None and pad.net.number == net.number:
                    pad.net.name = new_name

        # Update zone names
        for zone in self.pcb.zones:
            if zone.net == net.number:
                zone.net_name = new_name

        # Vias and routing are attached only via number,
        # so we don't need to do anything

    def _make_fp_property(
        self,
        property_name: str,
        layer: str,
        value: str,
        uuid: str,
        hide: bool = True,
    ) -> C_footprint.C_property:
        return C_footprint.C_property(
            name=property_name,
            value=value,
            layer=C_text_layer(layer=layer),
            uuid=UUID(uuid),
            effects=C_fp_text.C_fp_text_effects(font=self.font),
            at=C_xyr(x=0, y=0, r=0),
            hide=hide,
        )

    @staticmethod
    def INCLUDE_DESCRIPTIVE_PROPERTIES_FROM_PCB() -> list[str]:
        """
        Returns a list of properties that should be included from the PCB to the
        footprint.
        """
        from faebryk.libs.app.picking import Properties

        return [
            *[p.value for p in Properties],
            "JLCPCB description",
        ]

    def apply_design(self, logger: logging.Logger = logger):
        """Apply the design to the pcb"""
        import faebryk.library._F as F
        from faebryk.libs.part_lifecycle import PartLifecycle

        lifecycle = PartLifecycle.singleton()

        # Re-attach everything one more time
        # Re-attach everything one more time
        # We rely on this to reliably update the pcb
        self.attach()

        gf = GraphFunctions(self.graph)

        # Update footprints
        processed_fps = FuncSet[Footprint]()

        # Spacing algorithm to neatly insert new footprints
        # Each component group is clustered around their immediate parent
        # Each new component in the cluster is inserted with one vertical spacing
        # Each new cluster is inserted with one horizontal spacing

        DEFAULT_HORIZONTAL_SPACING = 10
        DEFAULT_VERTICAL_SPACING = 10
        CANVAS_EXTENT = 2147  # KiCad canvas goes to +/- approx. 2147mm in X and Y

        def _incremented_point(point: C_xyr, dx: int = 0, dy: int = 0) -> C_xyr:
            return C_xyr(x=point.x + dx, y=point.y + dy, r=point.r)

        def _iter_modules(tree: Tree[Module]):
            # yields nodes with footprints in a sensible order
            grouped = groupby(tree, lambda c: c.has_trait(F.has_footprint))
            yield from grouped[True]
            for child in grouped[False]:
                yield from _iter_modules(tree[child])

        def _get_cluster(component: Module) -> Node | None:
            if (parent := component.get_parent()) is not None:
                return cast_assert(Node, parent[0])
            return None

        components = _iter_modules(self.app.get_tree(types=Module))
        clusters = groupby(components, _get_cluster)

        if clusters:
            # scaled to fit all clusters inside the canvas boundary
            horizontal_spacing = min(
                floor(CANVAS_EXTENT / len(clusters)), DEFAULT_HORIZONTAL_SPACING
            )
            vertical_spacing = min(
                floor(CANVAS_EXTENT / max(len(clusters[c]) for c in clusters)),
                DEFAULT_VERTICAL_SPACING,
            )
        else:
            horizontal_spacing = DEFAULT_HORIZONTAL_SPACING
            vertical_spacing = DEFAULT_VERTICAL_SPACING

        cluster_point = copy.deepcopy(self.default_component_insert_point)
        insert_point = copy.deepcopy(self.default_component_insert_point)
        for cluster in clusters:
            insert_point = copy.deepcopy(cluster_point)
            cluster_has_footprints = False

            for component in clusters[cluster]:
                # If this component isn't the most special in it's chain of
                # specialization then skip it. We should only pick components that are
                # the most special.
                if component is not component.get_most_special():
                    continue

                pcb_fp, new_fp = lifecycle.pcb.ingest_footprint(
                    self, component, logger, insert_point
                )
                if new_fp:
                    insert_point = _incremented_point(
                        insert_point, dy=-vertical_spacing
                    )
                    cluster_has_footprints = True

                processed_fps.add(pcb_fp)

            if cluster_has_footprints:
                cluster_point = _incremented_point(cluster_point, dx=horizontal_spacing)

        ## Remove footprints that aren't present in the design
        # TODO: figure out how this should work with some
        # concept of a --tidy flag or the likes
        # Should this remove unmarked footprints?

        for pcb_fp in FuncSet[Footprint](self.pcb.footprints) - processed_fps:
            if ref_prop := pcb_fp.propertys.get("Reference"):
                removed_fp_ref = ref_prop.value
            else:
                # This should practically never occur
                removed_fp_ref = "<no reference>"
            logger.info(
                f"Removing outdated component with Reference `{removed_fp_ref}`",
                extra={"markdown": True},
            )
            self.remove_footprint(pcb_fp)

        # Update nets
        # Every bus has at least one net with name at this point
        f_nets_by_name = {
            n.get_trait(F.has_overriden_name).get_name(): n
            for n in gf.nodes_of_type(F.Net)
            if n.has_trait(F.has_overriden_name)
        }

        processed_nets = FuncSet[Net]()
        for net_name, f_net in f_nets_by_name.items():
            ## Rename existing nets if needed
            # We do this instead of ripping things up to:
            # - update zones, vias etc...
            # - minimally modify the PCB -> less chance we break something small
            if linked_net_t := f_net.try_get_trait(self.has_linked_kicad_net):
                pcb_net = linked_net_t.get_net()
                if pcb_net.name != net_name:
                    logger.info(
                        f"Renaming net `{pcb_net.name}`->`{net_name}`",
                        extra={"markdown": True},
                    )
                    self.rename_net(pcb_net, net_name)

            ## Add missing nets
            else:
                logger.info(f"Adding net `{net_name}`", extra={"markdown": True})
                pcb_net = self.insert_net(net_name)
                self.bind_net(pcb_net, f_net)

            ## Connect pads to nets
            pads_on_net = list(f_net.get_connected_pads().keys())
            if not pads_on_net:
                logger.warning(f"No pads on net `{net_name}`.")

            for f_pad in pads_on_net:
                # FIXME: if this happens its typically due to a floating component
                # which wasn't prebviously added to the layout
                try:
                    pcb_pads_connected_to_pad = f_pad.get_trait(
                        self.has_linked_kicad_pad
                    ).get_pad()[1]
                except TraitNotFound as ex:
                    # FIXME: replace this with more robust
                    raise RuntimeError(
                        f"No linked KiCAD pad found for `{f_pad.get_full_name()}`."
                        " This is caused by the component floating, rather than"
                        " being attached to the app's tree."
                    ) from ex

                # We needn't check again here for a lack of pcb pads on the atopile pad
                # because we've already raised a warning on binding of the trait
                for pcb_pad in pcb_pads_connected_to_pad:
                    pcb_pad.net = C_net(name=pcb_net.name, number=pcb_net.number)

            processed_nets.add(pcb_net)

        ## Remove nets that aren't present in the design
        for pcb_net in FuncSet[Net](self.pcb.nets) - processed_nets:
            # Net number == 0 and name == "" are the default values
            # They represent unconnected to nets, so skip them
            if pcb_net.number == 0:
                assert pcb_net.name == ""
                continue

            logger.info(
                f"Removing net `{pcb_net.name}`",
                extra={"markdown": True},
            )
            self.remove_net(pcb_net)
