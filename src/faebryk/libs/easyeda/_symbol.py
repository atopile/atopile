# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""Single-pass EasyEDA → KiCad symbol builder.

Takes raw API JSON and produces a KiCad SymbolFile directly — no intermediate
dataclasses. Each ``_build_*`` method parses its tilde-split fields and constructs
KiCad types in one step.
"""

import logging

from faebryk.libs.easyeda._arc import (
    arc_midpoint,
    compute_arc,
    parse_svg_path_for_arc,
)
from faebryk.libs.easyeda._parse import (
    bool_field,
    get,
    has_fill,
    parse_float,
    parse_int,
)
from faebryk.libs.easyeda._types import EePinType
from faebryk.libs.easyeda._units import to_mm
from faebryk.libs.kicad.fileformats import kicad

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

_KI_PIN_TYPE = {
    EePinType.UNSPECIFIED: kicad.schematic.E_pin_type.UNSPECIFIED,
    EePinType.INPUT: kicad.schematic.E_pin_type.INPUT,
    EePinType.OUTPUT: kicad.schematic.E_pin_type.OUTPUT,
    EePinType.BIDIRECTIONAL: kicad.schematic.E_pin_type.BIDIRECTIONAL,
    EePinType.POWER: kicad.schematic.E_pin_type.POWER_IN,
}

_SYM_DEFAULT_STROKE = kicad.schematic.Stroke(
    width=0,
    type=kicad.schematic.E_stroke_type.DEFAULT,
    color=kicad.schematic.Color(r=0, g=0, b=0, a=0),
)
_SYM_FILL_BG = kicad.schematic.Fill(type=kicad.schematic.E_fill_type.BACKGROUND)
_SYM_FILL_NONE = kicad.schematic.Fill(type=kicad.schematic.E_fill_type.NONE)
_SYM_PIN_EFFECTS = kicad.pcb.Effects(
    font=kicad.pcb.Font(
        size=kicad.pcb.Wh(w=1.27, h=1.27),
        thickness=None,
        bold=None,
        italic=None,
    ),
    hide=None,
    justify=None,
)


# ── KiCad constructor helpers ────────────────────────────────────────────────


def _ki_font(
    size: kicad.pcb.Wh,
    thickness: float | None = None,
) -> kicad.pcb.Font:
    return kicad.pcb.Font(size=size, thickness=thickness, bold=None, italic=None)


def _ki_effects(
    font: kicad.pcb.Font,
    justify: kicad.pcb.Justify | None = None,
    hide: bool | None = None,
) -> kicad.pcb.Effects:
    return kicad.pcb.Effects(font=font, hide=hide, justify=justify)


# ── SymbolBuilder ────────────────────────────────────────────────────────────


class SymbolBuilder:
    """Build a KiCad SymbolFile directly from raw EasyEDA API data."""

    def __init__(self, cad_data: dict, fp_lib_name: str):
        self._data = cad_data["dataStr"]
        self._info = self._data["head"]["c_para"]
        self._fp_lib_name = fp_lib_name
        self._bbox_x = float(self._data["head"]["x"])  # EE units (raw)
        self._bbox_y = float(self._data["head"]["y"])  # EE units (raw)
        self._subparts = cad_data.get("subparts")
        self._shapes = self._data["shape"]

        # Metadata exposed for callers
        self._name = self._info["name"]
        self._prefix = self._info["pre"]
        self._package = self._info.get("package")
        self._manufacturer = self._info.get("BOM_Manufacturer")
        self._datasheet = cad_data["lcsc"].get("url")
        self._lcsc_id = cad_data["lcsc"].get("number")
        self._jlc_id = self._info.get("BOM_JLCPCB Part Class")

    @property
    def datasheet(self) -> str | None:
        return self._datasheet

    @property
    def lcsc_id(self) -> str | None:
        return self._lcsc_id

    # ── coordinate helpers ───────────────────────────────────────────────

    def _xy(
        self, x: float, y: float, bbox_x: float, bbox_y: float
    ) -> tuple[float, float]:
        """Symbol coordinate: subtract bbox (with int truncation), convert to mm, flip Y."""
        return (
            round(to_mm(int(x) - int(bbox_x)), 2),
            round(-to_mm(int(y) - int(bbox_y)), 2),
        )

    def _fill(self, filled: bool) -> kicad.schematic.Fill:
        return _SYM_FILL_BG if filled else _SYM_FILL_NONE

    # ── text helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _sanitize_name(name: str) -> str:
        return name.replace(" ", "").replace("/", "_")

    @staticmethod
    def _apply_text_style(text: str) -> str:
        if text.endswith("#"):
            text = f"~{{{text[:-1]}}}"
        return text

    @staticmethod
    def _apply_pin_name_style(pin_name: str) -> str:
        return "/".join(
            SymbolBuilder._apply_text_style(txt) for txt in pin_name.split("/")
        )

    # ── polyline helper ──────────────────────────────────────────────────

    def _make_polyline(
        self, coords: list[tuple[float, float]]
    ) -> kicad.schematic.Polyline | None:
        if not coords:
            return None
        pts = [kicad.pcb.Xy(x=x, y=y) for x, y in coords]
        is_closed = len(pts) >= 2 and pts[0].x == pts[-1].x and pts[0].y == pts[-1].y
        return kicad.schematic.Polyline(
            pts=kicad.schematic.Pts(xys=pts),
            stroke=_SYM_DEFAULT_STROKE,
            fill=self._fill(is_closed),
        )

    # ── shape builders ───────────────────────────────────────────────────

    def _build_pin(
        self, line: str, bbox_x: float, bbox_y: float
    ) -> kicad.schematic.SymbolPin | None:
        segments = line.split("^^")
        if len(segments) < 7:
            return None

        settings = segments[0].split("~")[1:]  # skip "P" designator
        if len(settings) < 7:
            return None

        # Pin path segment (index 2)
        pin_path_seg = segments[2].split("~")
        path_str = pin_path_seg[0] if pin_path_seg else ""
        path_str = path_str.replace("v", "h")

        pin_length = 0
        if "h" in path_str:
            try:
                pin_length = abs(int(float(path_str.split("h")[-1])))
            except (ValueError, IndexError):
                pin_length = 0

        # Name segment (index 3)
        name_seg = segments[3].split("~")
        pin_name = name_seg[4] if len(name_seg) > 4 else ""
        pin_name = pin_name.replace(" ", "")

        # Dot segment (index 5)
        dot_seg = segments[5].split("~")
        has_dot = bool_field(dot_seg[0]) if dot_seg else False

        # Clock segment (index 6)
        clock_seg = segments[6].split("~")
        has_clock = bool_field(clock_seg[0]) if clock_seg else False

        # Pin number from spice_pin_number (settings[2])
        number = settings[2].replace(" ", "") if len(settings) > 2 else ""

        # Pin type
        pin_type_raw = parse_int(settings[1] if len(settings) > 1 else "0")
        try:
            pin_type = EePinType(pin_type_raw)
        except ValueError:
            pin_type = EePinType.UNSPECIFIED

        pos_x = parse_float(settings[3])
        pos_y = parse_float(settings[4])
        rotation = parse_int(settings[5])

        # Convert directly to KiCad
        pin_x, pin_y = self._xy(pos_x, pos_y, bbox_x, bbox_y)

        if has_dot and has_clock:
            pin_style = kicad.schematic.E_pin_style.INVERTED_CLOCK
        elif has_dot:
            pin_style = kicad.schematic.E_pin_style.INVERTED
        elif has_clock:
            pin_style = kicad.schematic.E_pin_style.CLOCK
        else:
            pin_style = kicad.schematic.E_pin_style.LINE

        return kicad.schematic.SymbolPin(
            at=kicad.pcb.Xyr(
                x=pin_x,
                y=pin_y,
                r=(180 + rotation) % 360,
            ),
            length=round(to_mm(pin_length), 2),
            type=_KI_PIN_TYPE.get(
                pin_type,
                kicad.schematic.E_pin_type.UNSPECIFIED,
            ),
            style=pin_style,
            name=kicad.schematic.PinName(
                name=self._apply_pin_name_style(pin_name),
                effects=_SYM_PIN_EFFECTS,
            ),
            number=kicad.schematic.PinNumber(number=number, effects=_SYM_PIN_EFFECTS),
        )

    def _build_rect(
        self, line: str, bbox_x: float, bbox_y: float
    ) -> kicad.schematic.Rect:
        f = line.split("~")[1:]
        pos_x = parse_float(get(f, 0))
        pos_y = parse_float(get(f, 1))
        width = parse_float(get(f, 4))
        height = parse_float(get(f, 5))

        x0, y0 = self._xy(pos_x, pos_y, bbox_x, bbox_y)
        x1 = round(to_mm(int(width)) + x0, 2)
        y1 = round(-to_mm(int(height)) + y0, 2)

        return kicad.schematic.Rect(
            start=kicad.pcb.Xy(x=x0, y=y0),
            end=kicad.pcb.Xy(x=x1, y=y1),
            stroke=_SYM_DEFAULT_STROKE,
            fill=_SYM_FILL_BG,
        )

    def _build_circle(
        self, line: str, bbox_x: float, bbox_y: float
    ) -> kicad.schematic.Circle:
        f = line.split("~")[1:]
        cx = parse_float(get(f, 0))
        cy = parse_float(get(f, 1))
        radius = parse_float(get(f, 2))
        fill = has_fill(f, 5)

        x, y = self._xy(cx, cy, bbox_x, bbox_y)
        r = round(to_mm(radius), 2)

        return kicad.schematic.Circle(
            center=kicad.pcb.Xy(x=x, y=y),
            end=kicad.pcb.Xy(x=round(x + r, 2), y=y),
            stroke=_SYM_DEFAULT_STROKE,
            fill=self._fill(fill),
        )

    def _build_ellipse(
        self, line: str, bbox_x: float, bbox_y: float
    ) -> kicad.schematic.Circle | None:
        f = line.split("~")[1:]
        cx = parse_float(get(f, 0))
        cy = parse_float(get(f, 1))
        rx = parse_float(get(f, 2))
        ry = parse_float(get(f, 3))

        if rx != ry:
            return None

        x, y = self._xy(cx, cy, bbox_x, bbox_y)
        r = round(to_mm(rx), 2)

        return kicad.schematic.Circle(
            center=kicad.pcb.Xy(x=x, y=y),
            end=kicad.pcb.Xy(x=round(x + r, 2), y=y),
            stroke=_SYM_DEFAULT_STROKE,
            fill=_SYM_FILL_NONE,
        )

    def _build_polyline(
        self, line: str, bbox_x: float, bbox_y: float, is_polygon: bool
    ) -> kicad.schematic.Polyline | None:
        f = line.split("~")[1:]
        points_raw = get(f, 0)
        fill = has_fill(f, 4)

        raw_pts = points_raw.split()
        coords = [
            self._xy(float(raw_pts[i]), float(raw_pts[i + 1]), bbox_x, bbox_y)
            for i in range(0, len(raw_pts) - 1, 2)
        ]

        if is_polygon or fill:
            coords.append(coords[0])

        return self._make_polyline(coords)

    def _build_path(
        self, line: str, bbox_x: float, bbox_y: float
    ) -> kicad.schematic.Polyline | None:
        f = line.split("~")[1:]
        paths_raw = get(f, 0)

        raw_pts = paths_raw.split()
        coords: list[tuple[float, float]] = []
        i = 0
        while i < len(raw_pts):
            cmd = raw_pts[i]
            if cmd in ("M", "L") and i + 2 < len(raw_pts):
                coords.append(
                    self._xy(
                        float(raw_pts[i + 1]),
                        float(raw_pts[i + 2]),
                        bbox_x,
                        bbox_y,
                    )
                )
                i += 3
            elif cmd == "Z":
                if coords:
                    coords.append(coords[0])
                i += 1
            elif cmd == "C":
                i += 7  # skip cubic bezier
            else:
                i += 1

        return self._make_polyline(coords)

    def _build_arc(
        self, line: str, bbox_x: float, bbox_y: float
    ) -> kicad.schematic.Arc | None:
        f = line.split("~")[1:]
        path = get(f, 0)
        fill = has_fill(f, 5)

        try:
            parsed = parse_svg_path_for_arc(path)
            if parsed is None:
                return None
            move_x, move_y, arc_params = parsed
            (
                rx_raw,
                ry_raw,
                x_rot,
                large_arc,
                sweep,
                end_x_raw,
                end_y_raw,
            ) = arc_params

            start_x = to_mm(move_x - bbox_x)
            start_y = to_mm(move_y - bbox_y)
            arc_end_x = to_mm(end_x_raw - bbox_x)
            arc_end_y = to_mm(end_y_raw - bbox_y)
            rx = to_mm(rx_raw)
            ry = to_mm(ry_raw)

            cx, cy, extent = compute_arc(
                start_x,
                start_y,
                rx,
                ry,
                x_rot,
                large_arc,
                sweep,
                arc_end_x,
                arc_end_y,
            )

            # Schematic Y axis is flipped
            if not large_arc:
                cy, start_y, arc_end_y = (
                    -cy,
                    -start_y,
                    -arc_end_y,
                )
            else:
                extent = 360 - extent

            radius = max(rx, ry)
            mid_x, mid_y = arc_midpoint(cx, cy, radius, x_rot, extent)

            return kicad.schematic.Arc(
                start=kicad.pcb.Xy(x=round(start_x, 2), y=round(start_y, 2)),
                mid=kicad.pcb.Xy(x=round(mid_x, 2), y=round(mid_y, 2)),
                end=kicad.pcb.Xy(
                    x=round(arc_end_x, 2),
                    y=round(arc_end_y, 2),
                ),
                stroke=_SYM_DEFAULT_STROKE,
                fill=self._fill(fill),
            )
        except Exception as e:
            logger.warning(f"Failed to parse symbol arc: {e}")
            return None

    # ── unit builder ─────────────────────────────────────────────────────

    def _build_unit(
        self,
        shapes: list[str],
        bbox_x: float,
        bbox_y: float,
        unit_name: str,
    ) -> tuple[kicad.schematic.SymbolUnit, list[float]]:
        """Build one symbol unit, return (unit, pin_y_values)."""
        sch_pins: list[kicad.schematic.SymbolPin] = []
        sch_rects: list[kicad.schematic.Rect] = []
        sch_circles: list[kicad.schematic.Circle] = []
        sch_polylines: list[kicad.schematic.Polyline] = []
        sch_arcs: list[kicad.schematic.Arc] = []
        pin_ys: list[float] = []

        for line in shapes:
            designator = line.split("~")[0]
            match designator:
                case "P":
                    if pin := self._build_pin(line, bbox_x, bbox_y):
                        sch_pins.append(pin)
                        pin_ys.append(pin.at.y)
                case "R":
                    sch_rects.append(self._build_rect(line, bbox_x, bbox_y))
                case "C":
                    sch_circles.append(self._build_circle(line, bbox_x, bbox_y))
                case "E":
                    if c := self._build_ellipse(line, bbox_x, bbox_y):
                        sch_circles.append(c)
                case "A":
                    if a := self._build_arc(line, bbox_x, bbox_y):
                        sch_arcs.append(a)
                case "PL":
                    if p := self._build_polyline(
                        line, bbox_x, bbox_y, is_polygon=False
                    ):
                        sch_polylines.append(p)
                case "PG":
                    if p := self._build_polyline(line, bbox_x, bbox_y, is_polygon=True):
                        sch_polylines.append(p)
                case "PT":
                    if p := self._build_path(line, bbox_x, bbox_y):
                        sch_polylines.append(p)
                case "T":
                    pass
                case _:
                    logger.warning(f"Unknown symbol designator: {designator}")

        unit = kicad.schematic.SymbolUnit(
            name=unit_name,
            polylines=sch_polylines,
            circles=sch_circles,
            rectangles=sch_rects,
            arcs=sch_arcs,
            pins=sch_pins,
        )
        return unit, pin_ys

    # ── build ────────────────────────────────────────────────────────────

    def build(self) -> kicad.symbol.SymbolFile:
        """Build a KiCad SymbolFile."""

        sanitized_name = self._sanitize_name(self._name)

        ki_units: list[kicad.schematic.SymbolUnit] = []
        all_pin_ys: list[float] = []

        if self._subparts:
            unit_number = 1
            for unit_data in self._subparts:
                unit_name = f"{sanitized_name}_{unit_number}_1"
                unit, pin_ys = self._build_unit(
                    unit_data["dataStr"]["shape"],
                    self._bbox_x,
                    self._bbox_y,
                    unit_name,
                )
                ki_units.append(unit)
                all_pin_ys.extend(pin_ys)
                unit_number += 1
        else:
            unit_name = f"{sanitized_name}_0_1"
            unit, pin_ys = self._build_unit(
                self._shapes,
                self._bbox_x,
                self._bbox_y,
                unit_name,
            )
            ki_units.append(unit)
            all_pin_ys.extend(pin_ys)

        # ── Symbol properties ──
        y_low = min(all_pin_ys) if all_pin_ys else 0
        y_high = max(all_pin_ys) if all_pin_ys else 0
        field_offset = 5.08

        sym_effects = _ki_effects(
            font=_ki_font(size=kicad.pcb.Wh(w=1.27, h=1.27)),
        )

        properties: list[kicad.schematic.Property] = [
            kicad.schematic.Property(
                name="Reference",
                value=self._prefix.replace("?", ""),
                id=0,
                at=kicad.pcb.Xyr(x=0, y=y_high + field_offset, r=0),
                effects=sym_effects,
            ),
            kicad.schematic.Property(
                name="Value",
                value=self._name,
                id=1,
                at=kicad.pcb.Xyr(x=0, y=y_low - field_offset, r=0),
                effects=sym_effects,
            ),
        ]

        next_id = 2
        next_y = field_offset + 2.54

        optional_props = [
            (
                "Footprint",
                f"{self._fp_lib_name}:{self._package}" if self._package else None,
            ),
            ("Datasheet", self._datasheet),
            ("Manufacturer", self._manufacturer),
            ("LCSC Part", self._lcsc_id),
            ("JLC Part", self._jlc_id),
        ]

        for prop_name, value in optional_props:
            if value:
                properties.append(
                    kicad.schematic.Property(
                        name=prop_name,
                        value=value,
                        id=next_id,
                        at=kicad.pcb.Xyr(x=0, y=y_low - next_y, r=0),
                        effects=sym_effects,
                    )
                )
                next_id += 1
                next_y += 2.54

        return kicad.symbol.SymbolFile(
            kicad_sym=kicad.symbol.SymbolLib(
                version=20241229,
                generator="faebryk_convert",
                symbols=[
                    kicad.schematic.Symbol(
                        name=sanitized_name,
                        power=False,
                        propertys=properties,
                        pin_numbers=None,
                        pin_names=None,
                        in_bom=True,
                        on_board=True,
                        symbols=ki_units,
                        convert=None,
                    )
                ],
            )
        )


# ── Test helpers ──────────────────────────────────────────────────────────────


def _make_pin_line(
    *,
    name: str = "X",
    number: str = "1",
    pos_x: int = 350,
    pos_y: int = 290,
    rotation: int = 180,
    pin_type: int = 0,
    has_dot: bool = False,
    has_clock: bool = False,
    length: int = 10,
) -> str:
    """Construct a raw EasyEDA pin line for testing."""
    return (
        f"P~show~{pin_type}~{number}~{pos_x}~{pos_y}~{rotation}~id1~0"
        f"^^{pos_x}~{pos_y}"
        f"^^M {pos_x} {pos_y} h{length}~#000000"
        f"^^0~0~0~0~{name}~start~~~#000000"
        f"^^0~0~0~0~{number}~end~~~#000000"
        f"^^{1 if has_dot else 0}~0~0"
        f"^^{1 if has_clock else 0}~M 0 0 L 0 0 L 0 0"
    )


def _make_sym_data(
    *,
    shapes: list[str],
    bbox_x: int = 400,
    bbox_y: int = 300,
    name: str = "TEST",
    prefix: str = "U?",
    package: str = "PKG",
) -> dict:
    """Minimal cad_data dict for edge-case symbol tests."""
    return {
        "dataStr": {
            "head": {
                "c_para": {
                    "name": name,
                    "pre": prefix,
                    "package": package,
                    "BOM_Manufacturer": "",
                    "BOM_JLCPCB Part Class": "",
                },
                "x": bbox_x,
                "y": bbox_y,
            },
            "shape": shapes,
        },
        "lcsc": {"number": "", "url": ""},
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

import pytest  # noqa: E402

from faebryk.libs.easyeda._footprint import (  # noqa: E402
    _opamp_cad_data,
    _resistor_cad_data,
    _tht_cad_data,
)


def test_build_sym_resistor_structure():
    result = SymbolBuilder(_resistor_cad_data(), fp_lib_name="easyeda2kicad").build()
    assert isinstance(result, kicad.symbol.SymbolFile)
    assert len(result.kicad_sym.symbols) == 1
    assert result.kicad_sym.symbols[0].name == "0603WAF1001T5E"


def test_build_sym_resistor_pins():
    result = SymbolBuilder(_resistor_cad_data(), fp_lib_name="easyeda2kicad").build()
    unit = result.kicad_sym.symbols[0].symbols[0]
    assert len(unit.pins) == 2
    assert {p.number.number for p in unit.pins} == {"1", "2"}


def test_build_sym_resistor_rectangle():
    result = SymbolBuilder(_resistor_cad_data(), fp_lib_name="easyeda2kicad").build()
    unit = result.kicad_sym.symbols[0].symbols[0]
    assert len(unit.rectangles) == 1


def test_build_sym_resistor_properties():
    result = SymbolBuilder(_resistor_cad_data(), fp_lib_name="easyeda2kicad").build()
    symbol = result.kicad_sym.symbols[0]
    prop_names = {p.name for p in symbol.propertys}
    assert "Reference" in prop_names
    assert "Value" in prop_names
    assert "Footprint" in prop_names
    assert "Datasheet" in prop_names
    assert "LCSC Part" in prop_names


def test_build_sym_resistor_footprint_property():
    result = SymbolBuilder(_resistor_cad_data(), fp_lib_name="mylib").build()
    symbol = result.kicad_sym.symbols[0]
    fp_prop = next(p for p in symbol.propertys if p.name == "Footprint")
    assert fp_prop.value == "mylib:R0603"


def test_build_sym_opamp_pins():
    result = SymbolBuilder(_opamp_cad_data(), fp_lib_name="easyeda2kicad").build()
    unit = result.kicad_sym.symbols[0].symbols[0]
    assert len(unit.pins) == 8


def test_build_sym_opamp_pin_orientation():
    result = SymbolBuilder(_opamp_cad_data(), fp_lib_name="easyeda2kicad").build()
    unit = result.kicad_sym.symbols[0].symbols[0]
    orientations = {p.at.r for p in unit.pins}
    assert 0 in orientations
    assert 180 in orientations


def test_build_sym_opamp_circles():
    result = SymbolBuilder(_opamp_cad_data(), fp_lib_name="easyeda2kicad").build()
    unit = result.kicad_sym.symbols[0].symbols[0]
    assert len(unit.circles) >= 1


def test_build_sym_version():
    result = SymbolBuilder(_resistor_cad_data(), fp_lib_name="easyeda2kicad").build()
    assert result.kicad_sym.version == 20241229


def test_build_sym_datasheet_property():
    builder = SymbolBuilder(_resistor_cad_data(), fp_lib_name="lib")
    assert builder.datasheet == "https://lcsc.com/product-detail/C21190.html"
    assert builder.lcsc_id == "C21190"


# ── KiCad serialization ─────────────────────────────────────────────────────


def test_kicad_sym_dumps():
    result = SymbolBuilder(_resistor_cad_data(), fp_lib_name="easyeda2kicad").build()
    text = kicad.dumps(result)
    assert "kicad_symbol_lib" in text
    assert "0603WAF1001T5E" in text


def test_kicad_opamp_sym_dumps():
    result = SymbolBuilder(_opamp_cad_data(), fp_lib_name="easyeda2kicad").build()
    text = kicad.dumps(result)
    assert "1OUT" in text
    assert "VCC" in text
    assert "pin" in text.lower()


# ── Pin style edge cases ────────────────────────────────────────────────────


def test_symbol_pin_name_overbar():
    data = _make_sym_data(
        shapes=[_make_pin_line(name="RESET#", pin_type=1)],
    )
    pin = (
        SymbolBuilder(data, fp_lib_name="lib")
        .build()
        .kicad_sym.symbols[0]
        .symbols[0]
        .pins[0]
    )
    assert pin.name.name == "~{RESET}"


def test_symbol_pin_dot_style():
    data = _make_sym_data(
        shapes=[_make_pin_line(name="EN", has_dot=True)],
    )
    pin = (
        SymbolBuilder(data, fp_lib_name="lib")
        .build()
        .kicad_sym.symbols[0]
        .symbols[0]
        .pins[0]
    )
    assert pin.style == "inverted"


def test_symbol_pin_clock_style():
    data = _make_sym_data(
        shapes=[_make_pin_line(name="CLK", has_clock=True)],
    )
    pin = (
        SymbolBuilder(data, fp_lib_name="lib")
        .build()
        .kicad_sym.symbols[0]
        .symbols[0]
        .pins[0]
    )
    assert pin.style == "clock"


def test_symbol_pin_inverted_clock_style():
    data = _make_sym_data(
        shapes=[_make_pin_line(name="CLK", has_dot=True, has_clock=True)],
    )
    pin = (
        SymbolBuilder(data, fp_lib_name="lib")
        .build()
        .kicad_sym.symbols[0]
        .symbols[0]
        .pins[0]
    )
    assert pin.style == "inverted_clock"
