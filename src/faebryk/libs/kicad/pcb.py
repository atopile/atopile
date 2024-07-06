# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import uuid
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Generic, List, Tuple, TypeVar

import sexpdata
from faebryk.libs.kicad.sexp import prettify_sexp_string
from sexpdata import Symbol


class Node:
    def __init__(self, node) -> None:
        assert isinstance(node, list)
        self.node = node

    @classmethod
    def from_node(cls, node: "Node"):
        return cls(node.node)

    def get(self, key: List[Callable[[Any], bool]]) -> List["Node"]:
        result = [
            Node(search_node)
            for search_node in self.node
            if isinstance(search_node, list) and key[0](search_node)
        ]
        # assert len(result) > 0, f"not found in {self}"

        if len(key) == 1:
            return result
        else:
            return [sub for next_node in result for sub in next_node.get(key[1:])]

    def get_recursive(self, key: Callable[[Any], bool]) -> List["Node"]:
        result = [
            Node(search_node)
            for search_node in self.node
            if isinstance(search_node, list) and key(search_node)
        ]

        result += [
            sub
            for next_node in self.node
            if isinstance(next_node, list)
            for sub in Node(next_node).get_recursive(key)
        ]

        return result

    def get_prop(self, key: str | list[str], recursive=False) -> List["Node"]:
        if isinstance(key, str):
            key = [key]

        def func(n):
            return len(n) > 0 and n[0] in ([Symbol(k) for k in key])

        if recursive:
            return self.get_recursive(func)
        return self.get([func])

    def append(self, node: "Node"):
        self.node.append(node.node)

    def __str__(self) -> str:
        return str(self.node)

    def delete(self):
        self.node.clear()
        self.node.append(None)

    def __repr__(self) -> str:
        return repr(self.node)

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, __value: object) -> bool:
        return str(self) == str(__value)


class FileNode(Node):
    @classmethod
    def load(cls, path: Path):
        return cls(sexpdata.loads(path.read_text()))

    def garbage_collect(self):
        def remove_empty(x):
            if type(x) in [list, tuple]:
                rec = map(remove_empty, x)
                return [o for o in rec if (o is not None) and (o not in [[], tuple()])]
            return x

        cleaned = remove_empty(self.node)
        self.node = cleaned

    def dump(self, path: Path):
        self.garbage_collect()
        sexpout = sexpdata.dumps(self.node)
        out = prettify_sexp_string(sexpout)

        return path.write_text(out)


class UUID(Node):
    @property
    def uuid(self) -> str:
        return self.node[1]

    @uuid.setter
    def uuid(self, value: str):
        self.node[1] = value

    @staticmethod
    def gen_uuid(mark: str = ""):
        # format: d864cebe-263c-4d3f-bbd6-bb51c6d2a608
        value = uuid.uuid4().hex

        suffix = mark.encode().hex()
        value = value[: -len(suffix)] + suffix

        DASH_IDX = [8, 12, 16, 20]
        formatted = value
        for i, idx in enumerate(DASH_IDX):
            formatted = formatted[: idx + i] + "-" + formatted[idx + i :]

        return formatted

    def is_marked(self, mark: str):
        suffix = mark.encode().hex()
        return self.uuid.replace("-", "").endswith(suffix)

    @classmethod
    def factory(cls, value: str | None = None):
        # generate uuid
        value = value or cls.gen_uuid()

        return cls([Symbol("uuid"), value])


class Geom(Node):
    Coord = Tuple[float, float]
    sym: None | str = None

    class Stroke(Node):
        @classmethod
        def factory(cls, width_mm: float, type: str):
            return cls(
                [
                    Symbol("stroke"),
                    [Symbol("width"), width_mm],
                    [Symbol("type"), Symbol(type)],
                ]
            )

    @property
    def layer_name(self) -> str:
        return self.get_prop("layer")[0].node[1]


class Zone(Node):
    class OutlineHatchMode(StrEnum):
        EDGE = "edge"
        FULL = "full"
        NONE = "none"

    class PadConnectMode(StrEnum):
        NONE = "no"
        SOLID = "yes"
        THERMAL_RELIEFS = ""
        THRU_HOLE_ONLY = "thru_hole_only"

    class FillMode(StrEnum):
        SOLID = ""
        HATCHED = "hatch"

    class HatchFillBorderAlgorithm(StrEnum):
        HATCH_THICKNESS = "hatch_thickness"

    class CornerSmoothingMode(StrEnum):
        NONE = ""
        FILLET = "fillet"
        CHAMFER = "chamfer"

    class IslandRemovalMode(StrEnum):
        DO_NOT_REMOVE = "1"
        REMOVE_ALL = ""
        BELOW_AREA_LIMIT = "2"

    @property
    def net(self) -> int:
        return int(self.get_prop("net")[0].node[1])

    @property
    def net_name(self) -> str:
        return self.get_prop("net_name")[0].node[1]

    @property
    def layer(self) -> str:
        return self.get_prop("layer")[0].node[1]

    @property
    def name(self) -> str:
        return self.get_prop("name")[0].node[1]

    @property
    def hatch_outline_mode(self) -> OutlineHatchMode:
        return self.get_prop("hatch")[0].node[1]

    @property
    def hatch_outline_pitch(self) -> float:
        return self.get_prop("hatch")[0].node[2]

    @property
    def priority(self) -> int:
        return self.get_prop("priority")[0].node[1]

    @property
    def uuid(self) -> UUID:
        return UUID.from_node(self.get_prop("uuid")[0])

    @classmethod
    def factory(
        cls,
        net: int,
        net_name: str,
        layer: str,
        uuid: UUID,
        name: str,
        polygon: List[Geom.Coord],
        locked: bool = False,
        outline_hatch_mode: OutlineHatchMode = OutlineHatchMode.EDGE,
        outline_hatch_pitch: float = 0.5,
        priority: int = 0,
        connect_pads_mode: PadConnectMode = PadConnectMode.SOLID,
        zone_pad_clearance: float = 0.5,
        zone_min_thickness: float = 0.25,
        filled_areas_thickness: bool = False,
        fill_mode: FillMode = FillMode.SOLID,
        hatch_fill_thickness: float = 1,
        hatch_fill_gap: float = 1.5,
        hatch_fill_orientation: float = 0,
        hatch_fill_smoothing_level: int = 1,
        hatch_fill_smoothing_value: float = 0,
        hatch_fill_border_algorithm: HatchFillBorderAlgorithm = HatchFillBorderAlgorithm.HATCH_THICKNESS,  # noqa: E501
        hatch_fill_min_hole_area: float = 0.3,
        pad_connection_thermal_gap: float = 0.5,
        pad_connection_thermal_bridge_width: float = 0.25,
        corner_smoothing_mode: CornerSmoothingMode = CornerSmoothingMode.NONE,
        corner_smoothing_radius: float = 1,
        island_removal_mode: IslandRemovalMode = IslandRemovalMode.DO_NOT_REMOVE,
        island_removal_min_area: float = 10.0,
    ):
        return Zone(
            [
                Symbol("zone"),
                [Symbol("net"), net],
                [Symbol("net_name"), net_name],
                [Symbol("layer"), layer],
                uuid.node,
                [Symbol("name"), name],
                [Symbol("locked"), yes_no(locked)],
                [Symbol("hatch"), Symbol(outline_hatch_mode), outline_hatch_pitch],
                [Symbol("priority"), priority],
                [
                    Symbol("connect_pads"),
                    Symbol(connect_pads_mode),
                    [Symbol("clearance"), zone_pad_clearance],
                ],
                [Symbol("min_thickness"), zone_min_thickness],
                [Symbol("filled_areas_thickness"), yes_no(filled_areas_thickness)],
                [
                    Symbol("fill"),
                    Symbol("yes"),
                    [Symbol("mode"), Symbol(fill_mode)] if fill_mode else [],
                    [Symbol("hatch_thickness"), hatch_fill_thickness],
                    [Symbol("hatch_gap"), hatch_fill_gap],
                    [Symbol("hatch_orientation"), hatch_fill_orientation],
                    [Symbol("hatch_smoothing_level"), hatch_fill_smoothing_level],
                    [Symbol("hatch_smoothing_value"), hatch_fill_smoothing_value],
                    [
                        Symbol("hatch_border_algorithm"),
                        Symbol(hatch_fill_border_algorithm),
                    ],
                    [Symbol("hatch_min_hole_area"), hatch_fill_min_hole_area],
                    [Symbol("thermal_gap"), pad_connection_thermal_gap],
                    [
                        Symbol("thermal_bridge_width"),
                        pad_connection_thermal_bridge_width,
                    ],
                    [Symbol("smoothing"), Symbol(corner_smoothing_mode)]
                    if corner_smoothing_mode
                    else [],
                    [Symbol("radius"), corner_smoothing_radius],
                    [Symbol("island_removal_mode"), Symbol(island_removal_mode)],
                    [Symbol("island_area_min"), island_removal_min_area],
                ],
                [
                    Symbol("polygon"),
                    [Symbol("pts"), *[[Symbol("xy"), *p] for p in polygon]],
                ],
            ]
        )


class Line(Geom):
    @property
    def start(self) -> Geom.Coord:
        return tuple(self.get_prop("start")[0].node[1:])

    @property
    def end(self) -> Geom.Coord:
        return tuple(self.get_prop("end")[0].node[1:])

    @classmethod
    def factory(
        cls,
        start: Geom.Coord,
        end: Geom.Coord,
        stroke: Geom.Stroke,
        layer: str,
        uuid: UUID,
    ):
        assert cls.sym is not None
        return cls(
            [
                Symbol(cls.sym),
                [Symbol("start"), *start],
                [Symbol("end"), *end],
                stroke.node,
                [Symbol("layer"), layer],
                uuid.node,
            ]
        )


class FP_Line(Line):
    sym = "fp_line"


class GR_Line(Line):
    sym = "gr_line"


class Arc(Geom):
    @property
    def start(self) -> Geom.Coord:
        return tuple(self.get_prop("start")[0].node[1:])

    @property
    def mid(self) -> Geom.Coord:
        return tuple(self.get_prop("mid")[0].node[1:])

    @property
    def end(self) -> Geom.Coord:
        return tuple(self.get_prop("end")[0].node[1:])

    @classmethod
    def factory(
        cls,
        start: Geom.Coord,
        mid: Geom.Coord,
        end: Geom.Coord,
        stroke: Geom.Stroke,
        layer: str,
        uuid: UUID,
    ):
        assert cls.sym is not None
        return cls(
            [
                Symbol(cls.sym),
                [Symbol("start"), *start],
                [Symbol("mid"), *mid],
                [Symbol("end"), *end],
                stroke.node,
                [Symbol("layer"), layer],
                uuid.node,
            ]
        )


class GR_Arc(Arc):
    sym = "gr_arc"


class FP_Arc(Arc):
    sym = "fp_arc"


class Rect(Geom):
    @property
    def start(self) -> Geom.Coord:
        return tuple(self.get_prop("start")[0].node[1:])

    @property
    def end(self) -> Geom.Coord:
        return tuple(self.get_prop("end")[0].node[1:])

    @classmethod
    def factory(
        cls,
        start: Geom.Coord,
        end: Geom.Coord,
        stroke: Geom.Stroke,
        fill_type: str,
        layer: str,
        uuid: Node,
    ):
        assert cls.sym is not None
        return cls(
            [
                Symbol(cls.sym),
                [Symbol("start"), *start],
                [Symbol("end"), *end],
                stroke.node,
                [Symbol("fill"), Symbol(fill_type)],
                [Symbol("layer"), layer],
                uuid.node,
            ]
        )


class GR_Rect(Rect):
    sym = "gr_rect"


class FP_Rect(Rect):
    sym = "fp_rect"


class Circle(Geom):
    @property
    def center(self) -> Geom.Coord:
        return tuple(self.get_prop("center")[0].node[1:])

    @property
    def end(self) -> Geom.Coord:
        return tuple(self.get_prop("end")[0].node[1:])

    @classmethod
    def factory(
        cls,
        center: Geom.Coord,
        end: Geom.Coord,
        stroke: Geom.Stroke,
        fill_type: str,
        layer: str,
        uuid: UUID,
    ):
        assert cls.sym is not None
        return cls(
            [
                Symbol(cls.sym),
                [Symbol("center"), *center],
                [Symbol("end"), *end],
                stroke.node,
                [Symbol("fill"), Symbol(fill_type)],
                [Symbol("layer"), layer],
                uuid.node,
            ]
        )


class GR_Circle(Circle):
    sym = "gr_circle"


class FP_Circle(Circle):
    sym = "fp_circle"


ALL_GEOMS = [
    FP_Line,
    FP_Arc,
    FP_Rect,
    FP_Circle,
    GR_Line,
    GR_Arc,
    GR_Rect,
    GR_Circle,
]


def get_geoms(node: Node, prefix: str):
    return [
        geotype.from_node(n)
        for geotype in ALL_GEOMS
        for n in node.get_prop(geotype.sym)
        if geotype.sym.startswith(prefix)
    ]


class PCB(FileNode):
    @property
    def footprints(self) -> List["Footprint"]:
        return [Footprint.from_node(n) for n in self.get_prop("footprint")]

    @property
    def vias(self) -> List["Via"]:
        return [Via.from_node(n) for n in self.get_prop("via")]

    @property
    def zones(self) -> List["Zone"]:
        return [Zone.from_node(n) for n in self.get_prop("zone")]

    @property
    def text(self) -> List["GR_Text"]:
        return [GR_Text.from_node(n) for n in self.get_prop("gr_text")]

    @property
    def segments(self) -> List["Segment"]:
        return [Segment.from_node(n) for n in self.get_prop("segment")]

    @property
    def nets(self) -> List["Net"]:
        return [Net.from_node(n) for n in self.get_prop("net")]

    @property
    def geoms(self) -> List["Geom"]:
        return get_geoms(self, "gr")

    @property
    def layer_names(self) -> List["str"]:
        return [n[1] for n in self.get_prop("layers")[0].node[1:]]

    def __repr__(self):
        return object.__repr__(self)


class Footprint(Node):
    Coord = Tuple[float, float, float]

    @property
    def reference(self) -> "FP_Text":
        return FP_Text.from_node(
            self.get([lambda n: n[0:2] == [Symbol("property"), "Reference"]])[0]
        )

    @property
    def value(self) -> "FP_Text":
        return FP_Text.from_node(
            self.get([lambda n: n[0:2] == [Symbol("property"), "Value"]])[0]
        )

    @property
    def user_text(self) -> List["FP_Text"]:
        return list(
            map(
                FP_Text.from_node,
                self.get([lambda n: n[0:2] == [Symbol("fp_text"), "user"]]),
            )
        )

    @property
    def layer(self) -> str:
        return self.get_prop("layer")[0].node[1]

    @layer.setter
    def layer(self, value: str):
        self.get_prop("layer")[0].node[1] = value

    @property
    def geoms(self) -> List["Geom"]:
        return get_geoms(self, "fp")

    @property
    def pads(self) -> List["Pad"]:
        return [Pad.from_node(n) for n in self.get_prop("pad")]

    def get_pad(self, name: str) -> "Pad":
        return Pad.from_node(self.get([lambda x: x[:2] == [Symbol("pad"), name]])[0])

    @property
    def at(self):
        return At[Footprint.Coord].from_node(self.get_prop("at")[0])

    @property
    def name(self) -> str:
        return self.node[1]

    @name.setter
    def name(self, value: str):
        self.node[1] = value

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}({self.name}, {self.reference.text},"
            f" {self.value.text})"
        )


class Pad(Node):
    Coord = tuple[float, float]

    @property
    def at(self):
        return At[Pad.Coord].from_node(self.get_prop("at")[0])

    @property
    def layers(self):
        return self.get_prop("layers")[0].node[1:]

    @property
    def name(self) -> str:
        return self.node[1]

    @property
    def net(self) -> str | None:
        net = self.get_prop("net")
        if not net:
            return None
        return net[0].node[1]

    @property
    def size(self) -> Tuple[float, float]:
        return tuple(self.get_prop("size")[0].node[1:3])

    @size.setter
    def size(self, value: Tuple[float, float]):
        self.get_prop("size")[0].node[1:3] = value


class Via(Node):
    Dimensions = Tuple[float, float]

    @property
    def at(self):
        return At.from_node(self.get_prop("at")[0])

    @property
    def size_drill(self):
        return (self.get_prop("size")[0].node[1], self.get_prop("drill")[0].node[1])

    @property
    def uuid(self) -> UUID:
        return UUID.from_node(self.get_prop("uuid")[0])

    @property
    def net(self) -> str:
        return self.get_prop("net")[0].node[1]

    @classmethod
    def factory(
        cls,
        at: "At",
        size_drill: Dimensions,
        layers: Tuple[str, str],
        net: str,
        uuid: UUID,
    ):
        return cls(
            [
                Symbol("via"),
                at.node,
                [Symbol("size"), size_drill[0]],
                [Symbol("drill"), size_drill[1]],
                [Symbol("layers"), *layers],
                [Symbol("net"), net],
                uuid.node,
            ]
        )


class Font(Node):
    @classmethod
    def factory(
        cls,
        size: Tuple[float, float],
        thickness: float,
        bold: bool = False,
        face: str = "",
    ):
        return cls(
            [
                Symbol("font"),
                [Symbol("size"), *size],
                [Symbol("thickness"), thickness],
                [Symbol("bold"), Symbol("yes" if bold else "no")],
                [Symbol("face"), face],
            ]
        )


class Text(Node):
    class Justify(StrEnum):
        MIRROR = "mirror"
        LEFT = "left"
        RIGHT = "right"
        CENTER = ""
        BOTTOM = "bottom"
        TOP = "top"

    TEXT_IDX = None
    TEXT_TYPE = None

    @property
    def layer(self) -> Node:
        return self.get_prop("layer")[0]

    @layer.setter
    def layer(self, value: str):
        self.layer.node[1] = value

    @property
    def text(self) -> str:
        assert self.TEXT_IDX is not None
        return self.node[self.TEXT_IDX]

    @text.setter
    def text(self, value: str):
        assert self.TEXT_IDX is not None
        self.node[self.TEXT_IDX] = value

    @property
    def uuid(self) -> UUID:
        return UUID.from_node(self.get_prop("uuid")[0])

    @property
    def at(self):
        return At.from_node(self.get_prop("at")[0])

    @property
    def font(self) -> Font:
        font = self.get_prop("effects")[0].get_prop("font")[0]
        return (
            font.get_prop("size")[0].node[1:3] + font.get_prop("thickness")[0].node[1]
        )

    @font.setter
    def font(self, value: Font):
        self.get_prop("effects")[0].node[1][:] = value.node[:]

    def __repr__(self) -> str:
        return f"Text[{self.node}]"

    @classmethod
    def factory(
        cls,
        text: str,
        at: "At",
        layer: str,
        font: Font,
        uuid: UUID,
        text_type: str | None = None,
        locked: bool = False,
        knockout: bool = False,
        lrjustify: Justify = Justify.CENTER,
        udjustify: Justify = Justify.CENTER,
    ):
        text_type = text_type or cls.TEXT_TYPE
        assert text_type

        # TODO make more generic
        return Text(
            [
                Symbol(text_type),
                text,
                [Symbol("locked"), yes_no(locked)],
                at.node,
                [Symbol("layer"), layer, Symbol("knockout") if knockout else None],
                [
                    Symbol("effects"),
                    font.node,
                    [Symbol("justify"), Symbol(lrjustify), Symbol(udjustify)],
                ],
                uuid.node,
            ]
        )


class FP_Text(Text):
    TEXT_IDX = 2
    TEXT_TYPE = "fp_text"

    @property
    def text_type(self) -> str:
        return self.node[1].value()

    @classmethod
    def factory(
        cls,
        text: str,
        at: "At",
        layer: str,
        font: Font,
        uuid: UUID,
        locked: bool = False,
        knockout: bool = False,
        lrjustify: Text.Justify = Text.Justify.CENTER,
        udjustify: Text.Justify = Text.Justify.CENTER,
    ):
        generic = Text.factory(
            text_type=cls.TEXT_TYPE,
            text=text,
            at=at,
            layer=layer,
            font=font,
            uuid=uuid,
            locked=locked,
            knockout=knockout,
            lrjustify=lrjustify,
            udjustify=udjustify,
        )

        # TODO: Why is this needed?
        generic.node.insert(1, Symbol("user"))
        return generic


class GR_Text(Text):
    TEXT_IDX = 1
    TEXT_TYPE = "gr_text"


T = TypeVar("T", Tuple[float, float], Tuple[float, float, float])


class At(Generic[T], Node):
    Coord = T

    @property
    def coord(self) -> T:
        # TODO
        if len(self.node[1:]) < 3:
            return tuple(self.node[1:] + [0])
        return tuple(self.node[1:4])

    @coord.setter
    def coord(self, value: T):
        self.node[1:4] = list(value)

    @classmethod
    def factory(cls, value: T):
        out = cls([Symbol("at")])
        out.coord = value
        return out


class Net(Node):
    @property
    def id(self):
        return self.node[1]

    @property
    def name(self):
        return self.node[2]

    @classmethod
    def factory(cls, net_id: int, net_name: str):
        return cls(
            [
                Symbol("net"),
                net_id,
                net_name,
            ]
        )


class _Segment(Node):
    @property
    def width(self) -> float:
        return self.get_prop("width")[0].node[1]

    @property
    def uuid(self) -> UUID:
        return UUID.from_node(self.get_prop("uuid")[0])


class Segment(_Segment):
    Coord = Tuple[float, float]

    @classmethod
    def factory(
        cls,
        start: Coord,
        end: Coord,
        width: float,
        layer: str,
        net_id: int,
        uuid: UUID,
    ):
        return cls(
            [
                Symbol("segment"),
                [Symbol("start"), *start],
                [Symbol("end"), *end],
                [Symbol("width"), width],
                [Symbol("layer"), layer],
                [Symbol("net"), net_id],
                uuid.node,
            ]
        )


class Segment_Arc(_Segment):
    Coord = Tuple[float, float]

    @classmethod
    def factory(
        cls,
        start: Coord,
        mid: Coord,
        end: Coord,
        width: float,
        layer: str,
        net_id: int,
        uuid: UUID,
    ):
        return cls(
            [
                Symbol("arc"),
                [Symbol("start"), *start],
                [Symbol("mid"), *mid],
                [Symbol("end"), *end],
                [Symbol("width"), width],
                [Symbol("layer"), layer],
                [Symbol("net"), net_id],
                uuid.node,
            ]
        )


def yes_no(value: bool) -> Symbol:
    return Symbol("yes" if value else "no")


class fp_lib_table(FileNode):
    class lib(Node):
        @property
        def name(self):
            return self.get_prop("name")[0].node[1]

        @property
        def type(self):
            return self.get_prop("type")[0].node[1]

        @property
        def uri(self):
            return self.get_prop("uri")[0].node[1]

        @property
        def options(self):
            return self.get_prop("options")[0].node[1]

        @property
        def descr(self):
            return self.get_prop("descr")[0].node[1]

        @classmethod
        def factory(
            cls,
            name: str,
            uri: str,
            uri_prj_relative: bool = True,
            type: str = "KiCad",
            options: str = "",
            descr: str = "",
        ):
            if uri_prj_relative:
                assert not uri.startswith("/")
                assert not uri.startswith("${KIPRJMOD}")
                uri = "${KIPRJMOD}/" + uri

            return cls(
                [
                    Symbol("lib"),
                    [Symbol("name"), name],
                    [Symbol("type"), type],
                    [Symbol("uri"), uri],
                    [Symbol("options"), options],
                    [Symbol("descr"), descr],
                ]
            )

    @property
    def version(self):
        return self.get_prop("version")[0].node[1]

    @property
    def libs(self):
        return [fp_lib_table.lib.from_node(n) for n in self.get_prop("lib")]

    def add_lib(self, lib: "fp_lib_table.lib"):
        self.node.append(lib.node)

    @classmethod
    def factory(cls, version: int, libs: "list[fp_lib_table.lib] | None" = None):
        libs = libs or []
        return cls(
            [
                Symbol("fp_lib_table"),
                [Symbol("version"), version],
                *[[Symbol("lib"), lib.node] for lib in libs],
            ]
        )
