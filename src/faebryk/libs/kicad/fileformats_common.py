import logging
import uuid
from dataclasses import dataclass, field
from enum import auto
from typing import Optional

from faebryk.libs.sexp.dataclass_sexp import Symbol, SymEnum, netlist_type, sexp_field
from faebryk.libs.util import KeyErrorAmbiguous

logger = logging.getLogger(__name__)

# TODO find complete examples of the fileformats, maybe in the kicad repo


class UUID(str):
    pass


@dataclass
class C_xy:
    x: float = field(**sexp_field(positional=True))
    y: float = field(**sexp_field(positional=True))

    def __sub__(self, other: "C_xy") -> "C_xy":
        return C_xy(x=self.x - other.x, y=self.y - other.y)

    def __add__(self, other: "C_xy") -> "C_xy":
        return C_xy(x=self.x + other.x, y=self.y + other.y)

    def rotate(self, center: "C_xy", angle: float) -> "C_xy":
        import math

        angle = -angle  # rotate kicad style counter-clockwise

        # Translate point to origin
        translated_x = self.x - center.x
        translated_y = self.y - center.y

        # Convert angle to radians
        angle = math.radians(angle)

        # Rotate
        rotated_x = translated_x * math.cos(angle) - translated_y * math.sin(angle)
        rotated_y = translated_x * math.sin(angle) + translated_y * math.cos(angle)

        # Translate back
        new_x = rotated_x + center.x
        new_y = rotated_y + center.y

        return C_xy(x=new_x, y=new_y)


@dataclass
class C_xyz:
    x: float = field(**sexp_field(positional=True))
    y: float = field(**sexp_field(positional=True))
    z: float = field(**sexp_field(positional=True))


@dataclass
class C_xyr:
    x: float = field(**sexp_field(positional=True))
    y: float = field(**sexp_field(positional=True))
    r: float = field(**sexp_field(positional=True), default=0)


@dataclass
class C_wh:
    w: float = field(**sexp_field(positional=True))
    h: Optional[float] = field(**sexp_field(positional=True), default=None)


@dataclass
class C_stroke:
    class E_type(SymEnum):
        solid = auto()
        default = auto()
        dash_dot_dot = auto()
        dash_dot = auto()
        dash = auto()
        dot = auto()

    width: float
    type: E_type


@dataclass
class C_effects:
    @dataclass
    class C_font:
        size: C_wh
        thickness: Optional[float] = None

    @dataclass
    class C_justify:
        class E_justify(SymEnum):
            center_horizontal = ""
            left = auto()
            right = auto()
            center_vertical = ""
            bottom = auto()
            top = auto()
            normal = ""
            mirror = auto()

        justifys: list[E_justify] = field(
            **sexp_field(positional=True), default_factory=list
        )

    font: C_font

    @staticmethod
    def preprocess_shitty_hide(c_effects: netlist_type):
        if isinstance(c_effects, list) and c_effects[-1] == Symbol("hide"):
            c_effects[-1] = [Symbol("hide"), Symbol("yes")]
        return c_effects

    hide: bool = False

    # Legal:
    # (justify mirror right)
    # (justify bottom)
    justifys: list[C_justify] = field(
        **sexp_field(multidict=True), default_factory=list
    )

    def get_justifys(self) -> list[C_justify.E_justify]:
        return [j_ for j in self.justifys for j_ in j.justifys]

    def __post_init__(self):
        justifys = set(self.get_justifys())

        J = C_effects.C_justify.E_justify

        def _only_one_of(lst: list[J]):
            dups = [j for j in justifys if j in lst]
            if len(dups) > 1:
                raise KeyErrorAmbiguous(dups)

        _only_one_of([J.mirror, J.normal])
        _only_one_of([J.left, J.right, J.center_horizontal])
        _only_one_of([J.top, J.bottom, J.center_vertical])


@dataclass
class C_pts:
    xys: list[C_xy] = field(**sexp_field(multidict=True), default_factory=list)


def gen_uuid(mark: str = ""):
    # format: d864cebe-263c-4d3f-bbd6-bb51c6d2a608
    value = uuid.uuid4().hex

    suffix = mark.encode().hex()
    if suffix:
        if len(suffix) >= len(value):
            value = suffix[: len(value)]
        else:
            value = value[: -len(suffix)] + suffix

    DASH_IDX = [8, 12, 16, 20]
    formatted = value
    for i, idx in enumerate(DASH_IDX):
        formatted = formatted[: idx + i] + "-" + formatted[idx + i :]

    return UUID(formatted)
