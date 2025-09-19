import logging
import re
import uuid
from abc import abstractmethod
from base64 import b64decode, b64encode
from copy import deepcopy
from dataclasses import dataclass, field
from enum import auto
from typing import Optional

import zstd
from dataclasses_json.undefined import CatchAll

from faebryk.libs.checksum import Checksum
from faebryk.libs.sexp.dataclass_sexp import (
    SEXP_File,
    Symbol,
    SymEnum,
    dump_single,
    netlist_type,
    sexp_field,
)
from faebryk.libs.util import KeyErrorAmbiguous, compare_dataclasses, once

logger = logging.getLogger(__name__)

# TODO find complete examples of the fileformats, maybe in the kicad repo


# @kicad10
KICAD_FP_VERSION = 20241229


class PropertyNotSet(Exception):
    pass


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

    def __add__(self, other: "C_xy") -> "C_xyr":
        return C_xyr(x=self.x + other.x, y=self.y + other.y, r=self.r)


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
    @dataclass(kw_only=True)
    class C_font:
        face: Optional[str] = None
        size: C_wh
        thickness: Optional[float] = None
        bold: Optional[bool] = None
        italic: Optional[bool] = None
        unresolved_font_name: Optional[str] = None

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

    hide: bool | None = False

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

        def _only_one_of(lst: list[C_effects.C_justify.E_justify]):
            dups = [j for j in justifys if j in lst]
            if len(dups) > 1:
                raise KeyErrorAmbiguous(dups)

        _only_one_of([J.mirror, J.normal])
        _only_one_of([J.left, J.right, J.center_horizontal])
        _only_one_of([J.top, J.bottom, J.center_vertical])


@dataclass
class C_pts:
    @dataclass
    class C_arc:
        start: C_xy
        mid: C_xy
        end: C_xy

    xys: list[C_xy] = field(**sexp_field(multidict=True), default_factory=list)
    arcs: list[C_arc] = field(**sexp_field(multidict=True), default_factory=list)


@dataclass(kw_only=True)
class C_kicad_footprint_file_header(SEXP_File):
    @dataclass(kw_only=True)
    class C_footprint_file_header:
        name: str = field(**sexp_field(positional=True))
        version: int = field(default=KICAD_FP_VERSION)
        generator: str = ""
        generator_version: str = ""
        unknown: CatchAll = None

    footprint: C_footprint_file_header


@dataclass
class C_kicad_pcb_file_header(SEXP_File):
    @dataclass
    class C_kicad_pcb_header:
        version: int = field(**sexp_field())
        generator: str
        generator_version: str
        unknown: CatchAll = None

    kicad_pcb: C_kicad_pcb_header


def gen_uuid(mark: str = ""):
    # format: d864cebe-263c-4d3f-bbd6-bb51c6d2a608
    value = uuid.uuid4().hex

    suffix = mark.encode().hex()
    if suffix:
        value = value[: -len(suffix)] + suffix

    DASH_IDX = [8, 12, 16, 20]
    formatted = value
    for i, idx in enumerate(DASH_IDX):
        formatted = formatted[: idx + i] + "-" + formatted[idx + i :]

    return UUID(formatted)


def compare_without_uuid[T](before: T, after: T):
    return compare_dataclasses(before, after, skip_keys=("uuid",))


@dataclass(kw_only=True)
class C_property_base:
    name: str
    value: str


class HasPropertiesMixin:
    @abstractmethod
    def add_property(self, name: str, value: str): ...

    name: str
    propertys: dict[str, C_property_base]

    def get_property(self, name: str) -> str:
        if name not in self.propertys:
            raise PropertyNotSet(f"Property `{name}` not set")
        return self.propertys[name].value

    def try_get_property(self, name: str) -> str | None:
        if name not in self.propertys:
            return None
        return self.propertys[name].value

    @property
    def property_dict(self) -> dict[str, str]:
        return {k: v.value for k, v in self.propertys.items()}

    def _hashable(self, remove_uuid: bool = True) -> str:
        copy = deepcopy(self)

        try:
            del copy.propertys["checksum"]
        except KeyError:
            pass

        out = dump_single(copy)

        if remove_uuid:
            out = re.sub(r"\(uuid \"[^\"]*\"\)", "", out)

        return out

    def set_checksum(self):
        if "checksum" in self.propertys:
            del self.propertys["checksum"]

        self.add_property("checksum", Checksum.build(self._hashable()))

    def verify_checksum(self):
        checksum_stated = self.get_property("checksum")

        try:
            Checksum.verify(checksum_stated, self._hashable())
        except Checksum.Mismatch:
            # legacy
            Checksum.verify(checksum_stated, self._hashable(remove_uuid=False))


@dataclass
class C_data:
    compressed: list[Symbol] = field(**sexp_field(positional=True))

    @property
    @once
    def merged(self):
        return "".join(str(v) for v in self.compressed)

    @property
    @once
    def uncompressed(self) -> bytes:
        assert self.merged.startswith("|") and self.merged.endswith("|")
        return zstd.decompress(b64decode(self.merged[1:-1]))

    @classmethod
    def compress(cls, data: bytes):
        # from kicad:common/embedded_files.cpp
        b64 = b64encode(zstd.compress(data)).decode()
        CHUNK_LEN = 76
        # chunk string to 76 characters
        chunks = [b64[i : i + CHUNK_LEN] for i in range(0, len(b64), CHUNK_LEN)]
        chunks[0] = "|" + chunks[0]
        chunks[-1] = chunks[-1] + "|"
        return cls(compressed=[Symbol(c) for c in chunks])
