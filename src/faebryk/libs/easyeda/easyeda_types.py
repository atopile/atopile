# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from dataclasses import dataclass, field
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────────────


class EePadShape(str, Enum):
    ELLIPSE = "ELLIPSE"
    RECT = "RECT"
    OVAL = "OVAL"
    POLYGON = "POLYGON"


class EeFpType(str, Enum):
    SMD = "smd"
    THT = "tht"


class EePinType(int, Enum):
    UNSPECIFIED = 0
    INPUT = 1
    OUTPUT = 2
    BIDIRECTIONAL = 3
    POWER = 4


# ── Footprint types ──────────────────────────────────────────────────────────


@dataclass
class EeFpPad:
    shape: EePadShape
    center_x: float  # mm
    center_y: float  # mm
    width: float  # mm
    height: float  # mm
    layer_id: int
    net: str
    number: str
    hole_radius: float  # mm
    points: str  # space-separated raw points (still in EE units for polygon)
    rotation: float
    id: str
    hole_length: float  # mm
    hole_point: str
    is_plated: bool
    is_locked: bool


@dataclass
class EeFpTrack:
    stroke_width: float  # mm
    layer_id: int
    net: str
    points: str  # space-separated raw points (EE units)
    id: str
    is_locked: bool


@dataclass
class EeFpHole:
    center_x: float  # mm
    center_y: float  # mm
    radius: float  # mm
    id: str
    is_locked: bool


@dataclass
class EeFpCircle:
    center_x: float  # mm
    center_y: float  # mm
    radius: float  # mm
    stroke_width: float  # mm
    layer_id: int
    id: str
    is_locked: bool


@dataclass
class EeFpArc:
    stroke_width: float  # mm
    layer_id: int
    net: str
    path: str  # SVG path string
    helper_dots: str
    id: str
    is_locked: bool


@dataclass
class EeFpVia:
    center_x: float  # mm
    center_y: float  # mm
    diameter: float  # mm
    net: str
    radius: float  # mm
    id: str
    is_locked: bool


@dataclass
class EeFpText:
    center_x: float  # mm
    center_y: float  # mm
    stroke_width: float  # mm
    rotation: float
    mirror: str
    layer_id: int
    net: str
    font_size: float  # mm
    text: str
    text_path: str
    visible: bool
    id: str
    is_locked: bool


@dataclass
class EeFpRect:
    pos_x: float  # mm
    pos_y: float  # mm
    width: float  # mm
    height: float  # mm
    stroke_width: float  # mm (not used for layer mapping)
    id: str
    layer_id: int
    is_locked: bool


@dataclass
class Ee3dModelInfo:
    name: str
    uuid: str
    translation_x: float  # EE units
    translation_y: float  # EE units
    translation_z: float  # EE units
    rotation_x: float
    rotation_y: float
    rotation_z: float


@dataclass
class EeFootprint:
    name: str
    fp_type: EeFpType
    bbox_x: float  # mm
    bbox_y: float  # mm
    pads: list[EeFpPad] = field(default_factory=list)
    tracks: list[EeFpTrack] = field(default_factory=list)
    holes: list[EeFpHole] = field(default_factory=list)
    vias: list[EeFpVia] = field(default_factory=list)
    circles: list[EeFpCircle] = field(default_factory=list)
    arcs: list[EeFpArc] = field(default_factory=list)
    rects: list[EeFpRect] = field(default_factory=list)
    texts: list[EeFpText] = field(default_factory=list)
    model_3d: Ee3dModelInfo | None = None


# ── Symbol types ─────────────────────────────────────────────────────────────


@dataclass
class EeSymPin:
    name: str
    number: str
    pos_x: float  # EE units
    pos_y: float  # EE units
    rotation: int
    pin_type: EePinType
    has_dot: bool
    has_clock: bool
    length: int  # in EE pixel units


@dataclass
class EeSymRect:
    pos_x: float
    pos_y: float
    width: float
    height: float


@dataclass
class EeSymCircle:
    center_x: float
    center_y: float
    radius: float
    fill: bool


@dataclass
class EeSymEllipse:
    center_x: float
    center_y: float
    radius_x: float
    radius_y: float
    fill: bool


@dataclass
class EeSymPolyline:
    points: str  # space-separated coordinates
    fill: bool
    is_polygon: bool


@dataclass
class EeSymArc:
    path: str  # SVG path string
    fill: bool


@dataclass
class EeSymPath:
    paths: str  # SVG path string
    fill: bool


@dataclass
class EeSymbolUnit:
    bbox_x: float
    bbox_y: float
    pins: list[EeSymPin] = field(default_factory=list)
    rectangles: list[EeSymRect] = field(default_factory=list)
    circles: list[EeSymCircle] = field(default_factory=list)
    ellipses: list[EeSymEllipse] = field(default_factory=list)
    arcs: list[EeSymArc] = field(default_factory=list)
    polylines: list[EeSymPolyline] = field(default_factory=list)
    paths: list[EeSymPath] = field(default_factory=list)


@dataclass
class EeSymbolInfo:
    name: str
    prefix: str
    package: str | None
    manufacturer: str | None
    datasheet: str | None
    lcsc_id: str | None
    jlc_id: str | None


@dataclass
class EeSymbol:
    info: EeSymbolInfo
    units: list[EeSymbolUnit] = field(default_factory=list)
