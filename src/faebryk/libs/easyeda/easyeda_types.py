# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from dataclasses import dataclass, field


def _to_mm(dim: float) -> float:
    """Convert EasyEDA internal units to mm."""
    return float(dim) * 10 * 0.0254


# ── Footprint types ──────────────────────────────────────────────────────────


@dataclass
class EeFpPad:
    shape: str  # ELLIPSE, RECT, OVAL, POLYGON
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
    cx: float  # mm
    cy: float  # mm
    radius: float  # mm
    stroke_width: float  # mm
    layer_id: int
    id: str
    is_locked: bool


@dataclass
class EeFpArc:
    stroke_width: float  # EE units (converted during build)
    layer_id: int
    net: str
    path: str  # SVG path string
    helper_dots: str
    id: str
    is_locked: bool


@dataclass
class EeFpRect:
    x: float  # mm
    y: float  # mm
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
    fp_type: str  # "smd" or "tht"
    bbox_x: float  # mm
    bbox_y: float  # mm
    pads: list[EeFpPad] = field(default_factory=list)
    tracks: list[EeFpTrack] = field(default_factory=list)
    holes: list[EeFpHole] = field(default_factory=list)
    circles: list[EeFpCircle] = field(default_factory=list)
    arcs: list[EeFpArc] = field(default_factory=list)
    rects: list[EeFpRect] = field(default_factory=list)
    model_3d: Ee3dModelInfo | None = None


# ── Symbol types ─────────────────────────────────────────────────────────────


@dataclass
class EeSymPin:
    name: str
    number: str
    pos_x: float  # EE units
    pos_y: float  # EE units
    rotation: int
    pin_type: int  # 0=unspecified, 1=input, 2=output, 3=bidirectional, 4=power
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
    package: str
    manufacturer: str
    datasheet: str
    lcsc_id: str
    jlc_id: str


@dataclass
class EeSymbol:
    info: EeSymbolInfo
    units: list[EeSymbolUnit] = field(default_factory=list)


# ── Tests ─────────────────────────────────────────────────────────────────────

import pytest  # noqa: E402


def test_to_mm():
    assert _to_mm(0) == 0
    # 100 * 10 * 0.0254 = 25.4
    assert _to_mm(100) == pytest.approx(25.4, abs=0.01)
    assert _to_mm(1000) == pytest.approx(254.0, abs=0.1)


def test_to_mm_negative():
    assert _to_mm(-100) == pytest.approx(-25.4, abs=0.01)
