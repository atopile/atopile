# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

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
        tstamp: str,
    ):
        assert cls.sym is not None
        return cls(
            [
                Symbol(cls.sym),
                [Symbol("start"), *start],
                [Symbol("end"), *end],
                stroke.node,
                [Symbol("layer"), layer],
                [Symbol("tstamp"), tstamp],
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
        tstamp: str,
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
                [Symbol("tstamp"), tstamp],
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
        tstamp: str,
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
                [Symbol("tstamp"), tstamp],
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
        tstamp: str,
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
                [Symbol("tstamp"), tstamp],
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


class PCB(Node):
    @property
    def footprints(self) -> List["Footprint"]:
        return [Footprint.from_node(n) for n in self.get_prop("footprint")]

    @property
    def vias(self) -> List["Via"]:
        return [Via.from_node(n) for n in self.get_prop("via")]

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
        pcbsexpout = sexpdata.dumps(self.node)
        out = prettify_sexp_string(pcbsexpout)

        return path.write_text(out)

    def __repr__(self):
        return object.__repr__(self)


class Footprint(Node):
    Coord = Tuple[float, float, float]

    @property
    def reference(self) -> "FP_Text":
        return FP_Text.from_node(
            self.get([lambda n: n[0:2] == [Symbol("fp_text"), Symbol("reference")]])[0]
        )

    @property
    def value(self) -> "FP_Text":
        return FP_Text.from_node(
            self.get([lambda n: n[0:2] == [Symbol("fp_text"), Symbol("value")]])[0]
        )

    @property
    def user_text(self) -> List["FP_Text"]:
        return list(
            map(
                FP_Text.from_node,
                self.get([lambda n: n[0:2] == [Symbol("fp_text"), Symbol("user")]]),
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
    def net(self) -> str:
        return self.get_prop("net")[0].node[1]

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

    @classmethod
    def factory(
        cls,
        at: "At",
        size_drill: Dimensions,
        layers: Tuple[str, str],
        net: str,
        tstamp: str,
    ):
        return cls(
            [
                Symbol("via"),
                at.node,
                [Symbol("size"), size_drill[0]],
                [Symbol("drill"), size_drill[1]],
                [Symbol("layers"), *layers],
                [Symbol("net"), net],
                [Symbol("tstamp"), tstamp],
            ]
        )


class Text(Node):
    Font = Tuple[float, float, float]
    TEXT_IDX = None

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
        font = self.get_prop("effects")[0].get_prop("font")[0]
        font.get_prop("size")[0].node[1:3] = value[0:2]
        font.get_prop("thickness")[0].node[1] = value[2]

    def __repr__(self) -> str:
        return f"Text[{self.node}]"

    @classmethod
    def factory(
        cls, text: str, at: "At", layer: str, font: Font, tstamp: str, text_type: str
    ):
        # TODO make more generic
        return Text(
            [
                Symbol(text_type),
                text,
                at.node,
                [Symbol("layer"), layer],
                [
                    Symbol("effects"),
                    [
                        Symbol("font"),
                        [Symbol("size"), *font[0:2]],
                        [Symbol("thickness"), font[2]],
                    ],
                ],
                [Symbol("tstamp"), tstamp],
            ]
        )


class FP_Text(Text):
    TEXT_IDX = 2

    @property
    def text_type(self) -> str:
        return self.node[1].value()

    @classmethod
    def factory(cls, text: str, at: "At", layer: str, font: Text.Font, tstamp: str):
        generic = Text.factory(text, at, layer, font, tstamp, text_type="fp_text")
        generic.node.insert(1, Symbol("user"))
        return generic


class GR_Text(Text):
    TEXT_IDX = 1

    @classmethod
    def factory(cls, text: str, at: "At", layer: str, font: Text.Font, tstamp: str):
        return Text.factory(text, at, layer, font, tstamp, text_type="gr_text")


T = TypeVar("T", Tuple[float, float], Tuple[float, float, float])


class At(Generic[T], Node):
    Coord = T

    @property
    def coord(self) -> Coord:
        # TODO
        if len(self.node[1:]) < 3:
            return tuple(self.node[1:] + [0])
        return tuple(self.node[1:4])

    @coord.setter
    def coord(self, value: Coord):
        self.node[1:4] = list(value)

    @classmethod
    def factory(cls, value: Coord):
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


class Segment(Node):
    Coord = Tuple[float, float]

    @classmethod
    def factory(
        cls,
        start: Coord,
        end: Coord,
        width: float,
        layer: str,
        net_id: int,
        tstamp: str,
    ):
        return cls(
            [
                Symbol("segment"),
                [Symbol("start"), *start],
                [Symbol("end"), *end],
                [Symbol("width"), width],
                [Symbol("layer"), layer],
                [Symbol("net"), net_id],
                [Symbol("tstamp"), tstamp],
            ]
        )


class Segment_Arc(Node):
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
        tstamp: str,
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
                [Symbol("tstamp"), tstamp],
            ]
        )
