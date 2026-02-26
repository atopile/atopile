# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""Build KiCad typed models directly from parsed EasyEDA data."""

import logging
import math
import re

from faebryk.libs.easyeda.easyeda_types import EeFootprint, EeSymbol, _to_mm
from faebryk.libs.kicad.fileformats import kicad

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

KI_PAD_SHAPE = {
    "ELLIPSE": "circle",
    "RECT": "rect",
    "OVAL": "oval",
    "POLYGON": "custom",
}

KI_PAD_LAYERS: dict[int, list[str]] = {
    1: ["F.Cu", "F.Paste", "F.Mask"],
    2: ["B.Cu", "B.Paste", "B.Mask"],
    3: ["F.SilkS"],
    11: ["*.Cu", "*.Paste", "*.Mask"],
    13: ["F.Fab"],
    15: ["Dwgs.User"],
}

KI_PAD_LAYERS_THT: dict[int, list[str]] = {
    1: ["F.Cu", "F.Mask"],
    2: ["B.Cu", "B.Mask"],
    3: ["F.SilkS"],
    11: ["*.Cu", "*.Mask"],
    13: ["F.Fab"],
    15: ["Dwgs.User"],
}

KI_LAYERS: dict[int, str] = {
    1: "F.Cu",
    2: "B.Cu",
    3: "F.SilkS",
    4: "B.SilkS",
    5: "F.Paste",
    6: "B.Paste",
    7: "F.Mask",
    8: "B.Mask",
    10: "Edge.Cuts",
    11: "Edge.Cuts",
    12: "Cmts.User",
    13: "F.Fab",
    14: "B.Fab",
    15: "Dwgs.User",
    101: "F.Fab",
}

KI_PIN_TYPE = {
    0: "unspecified",
    1: "input",
    2: "output",
    3: "bidirectional",
    4: "power_in",
}

WORKAROUND_SMD_3D_MODEL_FIX = True


# ── Arc geometry ─────────────────────────────────────────────────────────────


def _compute_arc(
    start_x: float,
    start_y: float,
    radius_x: float,
    radius_y: float,
    angle: float,
    large_arc_flag: bool,
    sweep_flag: bool,
    end_x: float,
    end_y: float,
) -> tuple[float, float, float]:
    """
    Elliptical arc endpoint-to-center conversion (W3C SVG spec).
    Returns (center_x, center_y, angle_extent).
    """
    dx2 = (start_x - end_x) / 2.0
    dy2 = (start_y - end_y) / 2.0

    angle_rad = math.radians(angle % 360.0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    x1 = cos_a * dx2 + sin_a * dy2
    y1 = -sin_a * dx2 + cos_a * dy2

    radius_x = abs(radius_x)
    radius_y = abs(radius_y)
    rx2 = radius_x * radius_x
    ry2 = radius_y * radius_y
    x1_2 = x1 * x1
    y1_2 = y1 * y1

    radii_check = (x1_2 / rx2 + y1_2 / ry2) if rx2 != 0 and ry2 != 0 else 0
    if radii_check > 1:
        radius_x *= math.sqrt(radii_check)
        radius_y *= math.sqrt(radii_check)
        rx2 = radius_x * radius_x
        ry2 = radius_y * radius_y

    sign = -1 if large_arc_flag == sweep_flag else 1
    sq = 0.0
    denom = rx2 * y1_2 + ry2 * x1_2
    if denom > 0:
        sq = (rx2 * ry2 - rx2 * y1_2 - ry2 * x1_2) / denom
    sq = max(sq, 0)
    coef = sign * math.sqrt(sq)
    cx1 = coef * ((radius_x * y1) / radius_y) if radius_y != 0 else 0
    cy1 = coef * -((radius_y * x1) / radius_x) if radius_x != 0 else 0

    sx2 = (start_x + end_x) / 2.0
    sy2 = (start_y + end_y) / 2.0
    cx = sx2 + (cos_a * cx1 - sin_a * cy1)
    cy = sy2 + (sin_a * cx1 + cos_a * cy1)

    ux = (x1 - cx1) / radius_x if radius_x != 0 else 0
    uy = (y1 - cy1) / radius_y if radius_y != 0 else 0
    vx = (-x1 - cx1) / radius_x if radius_x != 0 else 0
    vy = (-y1 - cy1) / radius_y if radius_y != 0 else 0

    n = math.sqrt((ux * ux + uy * uy) * (vx * vx + vy * vy))
    p = ux * vx + uy * vy
    cross_sign = -1 if (ux * vy - uy * vx) < 0 else 1

    if n != 0 and abs(p / n) < 1:
        angle_extent = math.degrees(cross_sign * math.acos(p / n))
    else:
        angle_extent = 360 + 359

    if not sweep_flag and angle_extent > 0:
        angle_extent -= 360
    elif sweep_flag and angle_extent < 0:
        angle_extent += 360

    extent_sign = 1 if angle_extent < 0 else -1
    angle_extent = (abs(angle_extent) % 360) * extent_sign

    return cx, cy, angle_extent


def _arc_midpoint(
    cx: float, cy: float, radius: float, angle_start: float, angle_end: float
) -> tuple[float, float]:
    mid_angle = (angle_start + angle_end) / 2
    return (
        cx + radius * math.cos(mid_angle),
        cy + radius * math.sin(mid_angle),
    )


def _fp_to_ki(dim: str | float) -> float:
    """Convert EasyEDA raw units (possibly string) to KiCad mm, rounded."""
    try:
        return round(_to_mm(float(dim)), 2)
    except ValueError, TypeError:
        return 0.0


def _angle_to_ki(rotation: float) -> float:
    if math.isnan(rotation):
        return 0.0
    return -(360 - rotation) if rotation > 180 else rotation


# ── Footprint builder ────────────────────────────────────────────────────────


def build_footprint(
    ee_fp: EeFootprint,
    model_path: str | None = None,
) -> kicad.footprint.FootprintFile:
    """Build a KiCad FootprintFile directly from parsed EeFootprint data."""

    bbox_x = ee_fp.bbox_x
    bbox_y = ee_fp.bbox_y

    pads: list[kicad.pcb.Pad] = []
    lines: list[kicad.pcb.Line] = []
    circles: list[kicad.pcb.Circle] = []
    arcs: list[kicad.pcb.Arc] = []
    texts: list[kicad.pcb.FpText] = []
    models: list[kicad.pcb.Model] = []

    # ── Pads ──
    for ee_pad in ee_fp.pads:
        is_tht = ee_pad.hole_radius > 0
        pad_type = "thru_hole" if is_tht else "smd"
        shape = KI_PAD_SHAPE.get(ee_pad.shape, "custom")

        layer_map = KI_PAD_LAYERS_THT if is_tht else KI_PAD_LAYERS
        layers = layer_map.get(ee_pad.layer_id, [])

        pos_x = round(ee_pad.center_x - bbox_x, 2)
        pos_y = round(ee_pad.center_y - bbox_y, 2)
        width = round(max(ee_pad.width, 0.01), 2)
        height = round(max(ee_pad.height, 0.01), 2)
        orientation = round(_angle_to_ki(ee_pad.rotation), 2)

        number = ee_pad.number
        if "(" in number and ")" in number:
            number = number.split("(")[1].split(")")[0]

        # Drill
        drill = None
        if ee_pad.hole_radius > 0:
            hr = round(ee_pad.hole_radius, 2)
            hl = round(ee_pad.hole_length, 2) if ee_pad.hole_length else 0
            if hl and hl != 0:
                max_dist_hole = max(hr * 2, hl)
                if height - max_dist_hole >= width - max_dist_hole:
                    drill = kicad.pcb.PadDrill(
                        shape="oval", size_x=round(hr * 2, 2), size_y=hl
                    )
                else:
                    drill = kicad.pcb.PadDrill(
                        shape="oval", size_x=hl, size_y=round(hr * 2, 2)
                    )
            else:
                drill = kicad.pcb.PadDrill(size_x=round(2 * hr, 2))

        # Custom polygon pad
        primitives = None
        point_list = [_fp_to_ki(p) for p in re.findall(r"\S+", ee_pad.points)]

        if shape == "custom" and point_list:
            width = 0.005
            height = 0.005
            orientation = 0

            poly_pts = [
                kicad.pcb.Xy(
                    x=round(point_list[i] - bbox_x - pos_x, 2),
                    y=round(point_list[i + 1] - bbox_y - pos_y, 2),
                )
                for i in range(0, len(point_list) - 1, 2)
            ]
            if poly_pts:
                primitives = kicad.pcb.PadPrimitives(
                    gr_polys=[
                        kicad.pcb.Polygon(
                            pts=kicad.pcb.Pts(xys=poly_pts),
                            layers=[],
                        )
                    ]
                )

        pads.append(
            kicad.pcb.Pad(
                name=number,
                type=pad_type,
                shape=shape,
                at=kicad.pcb.Xyr(
                    x=pos_x, y=pos_y, r=orientation if orientation else None
                ),
                size=kicad.pcb.Wh(w=width, h=height),
                drill=drill,
                layers=layers,
                uuid=kicad.gen_uuid(),
                primitives=primitives,
            )
        )

    # ── Tracks → Lines ──
    for ee_track in ee_fp.tracks:
        layer_str = (
            " ".join(KI_PAD_LAYERS[ee_track.layer_id])
            if ee_track.layer_id in KI_PAD_LAYERS
            else "F.Fab"
        )
        stroke_w = round(max(ee_track.stroke_width, 0.01), 2)

        point_list = [_fp_to_ki(p) for p in re.findall(r"\S+", ee_track.points)]
        for i in range(0, len(point_list) - 2, 2):
            lines.append(
                kicad.pcb.Line(
                    start=kicad.pcb.Xy(
                        x=round(point_list[i] - bbox_x, 2),
                        y=round(point_list[i + 1] - bbox_y, 2),
                    ),
                    end=kicad.pcb.Xy(
                        x=round(point_list[i + 2] - bbox_x, 2),
                        y=round(point_list[i + 3] - bbox_y, 2),
                    ),
                    layer=layer_str,
                    layers=[layer_str],
                    stroke=kicad.pcb.Stroke(width=stroke_w, type="solid"),
                    locked=False,
                    uuid=kicad.gen_uuid(),
                )
            )

    # ── Holes → thru_hole pads ──
    for ee_hole in ee_fp.holes:
        size = round(ee_hole.radius * 2, 2)
        pads.append(
            kicad.pcb.Pad(
                name="",
                type="thru_hole",
                shape="circle",
                at=kicad.pcb.Xyr(
                    x=round(ee_hole.center_x - bbox_x, 2),
                    y=round(ee_hole.center_y - bbox_y, 2),
                ),
                size=kicad.pcb.Wh(w=size, h=size),
                drill=kicad.pcb.PadDrill(size_x=size),
                layers=["*.Cu", "*.Mask"],
                uuid=kicad.gen_uuid(),
            )
        )

    # ── Vias → thru_hole pads ──
    for ee_via in ee_fp.vias:
        drill_size = round(ee_via.radius * 2, 2)
        diameter = round(ee_via.diameter, 2)
        pads.append(
            kicad.pcb.Pad(
                name="",
                type="thru_hole",
                shape="circle",
                at=kicad.pcb.Xyr(
                    x=round(ee_via.center_x - bbox_x, 2),
                    y=round(ee_via.center_y - bbox_y, 2),
                ),
                size=kicad.pcb.Wh(w=diameter, h=diameter),
                drill=kicad.pcb.PadDrill(size_x=drill_size),
                layers=["*.Cu", "*.Paste", "*.Mask"],
                uuid=kicad.gen_uuid(),
            )
        )

    # ── Circles ──
    for ee_circle in ee_fp.circles:
        cx = round(ee_circle.cx - bbox_x, 2)
        cy = round(ee_circle.cy - bbox_y, 2)
        circles.append(
            kicad.pcb.Circle(
                center=kicad.pcb.Xy(x=cx, y=cy),
                end=kicad.pcb.Xy(x=round(cx + ee_circle.radius, 2), y=cy),
                layer=KI_LAYERS.get(ee_circle.layer_id, "F.Fab"),
                layers=[],
                stroke=kicad.pcb.Stroke(
                    width=round(max(ee_circle.stroke_width, 0.01), 2), type="solid"
                ),
                locked=False,
                uuid=kicad.gen_uuid(),
            )
        )

    # ── Rectangles → 4 Lines ──
    for ee_rect in ee_fp.rects:
        layer = (
            " ".join(KI_PAD_LAYERS[ee_rect.layer_id])
            if ee_rect.layer_id in KI_PAD_LAYERS
            else "F.Fab"
        )
        stroke = kicad.pcb.Stroke(
            width=round(max(ee_rect.stroke_width, 0.01), 2), type="solid"
        )

        sx = round(ee_rect.x - bbox_x, 2)
        sy = round(ee_rect.y - bbox_y, 2)
        w = round(ee_rect.width, 2)
        h = round(ee_rect.height, 2)

        starts_x = [sx, sx + w, sx + w, sx]
        starts_y = [sy, sy, sy + h, sy]
        ends_x = [sx + w, sx + w, sx, sx]
        ends_y = [sy, sy + h, sy + h, sy]

        for i in range(4):
            lines.append(
                kicad.pcb.Line(
                    start=kicad.pcb.Xy(x=starts_x[i], y=starts_y[i]),
                    end=kicad.pcb.Xy(x=ends_x[i], y=ends_y[i]),
                    layer=layer,
                    layers=[layer],
                    stroke=stroke,
                    locked=False,
                    uuid=kicad.gen_uuid(),
                )
            )

    # ── Arcs ──
    for ee_arc in ee_fp.arcs:
        arc_path = ee_arc.path.replace(",", " ").replace("M ", "M").replace("A ", "A")
        try:
            start_part, arc_part = arc_path.split("A", 1)
            start_xy = start_part[1:].split(" ", 1)
            sx = _fp_to_ki(start_xy[0]) - bbox_x
            sy = _fp_to_ki(start_xy[1]) - bbox_y

            params = arc_part.replace("  ", " ").strip().split(" ", 6)
            svg_rx = _fp_to_ki(params[0])
            svg_ry = _fp_to_ki(params[1])
            x_rot = float(params[2])
            large_arc = params[3] == "1"
            sweep = params[4] == "1"
            ex = _fp_to_ki(params[5]) - bbox_x
            ey = _fp_to_ki(params[6]) - bbox_y

            if svg_ry == 0:
                continue

            center_x, center_y, extent = _compute_arc(
                sx, sy, svg_rx, svg_ry, x_rot, large_arc, sweep, ex, ey
            )

            # Round to 2dp to match old pipeline: KiFootprintArc stores all
            # float fields via round_float_values() and the v5 template uses
            # {:.2f}. The text round-trip (serialize → parse) produces clean
            # 2dp floats that _calc_arc_midpoint then rotates.
            center_x = round(center_x, 2)
            center_y = round(center_y, 2)
            extent = round(extent, 2)
            ex = round(ex, 2)
            ey = round(ey, 2)

            center = kicad.pcb.Xy(x=center_x, y=center_y)
            end_xy = kicad.pcb.Xy(x=ex, y=ey)

            # 3-point arc: start, mid, end via rotation around center
            mid = kicad.geo.rotate(end_xy, center, -extent / 2.0)
            end_pt = kicad.geo.rotate(end_xy, center, -extent)

            arcs.append(
                kicad.pcb.Arc(
                    start=kicad.pcb.Xy(x=ex, y=ey),
                    mid=kicad.pcb.Xy(x=mid.x, y=mid.y),
                    end=kicad.pcb.Xy(x=end_pt.x, y=end_pt.y),
                    layer=KI_LAYERS.get(ee_arc.layer_id, "F.Fab"),
                    layers=[],
                    stroke=kicad.pcb.Stroke(
                        width=max(_fp_to_ki(ee_arc.stroke_width), 0.01), type="solid"
                    ),
                    locked=False,
                    uuid=kicad.gen_uuid(),
                )
            )
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse footprint arc: {e}")
            continue

    # ── Texts ──
    for ee_text in ee_fp.texts:
        layer = KI_LAYERS.get(ee_text.layer_id, "F.Fab")
        if ee_text.type == "N":
            layer = layer.replace(".SilkS", ".Fab")
        mirror = layer.startswith("B")
        justify = kicad.pcb.Justify(
            justification="left", mirror=mirror if mirror else None
        )
        texts.append(
            kicad.pcb.FpText(
                type=kicad.pcb.E_fp_text_type.USER,
                text=ee_text.text,
                at=kicad.pcb.Xyr(
                    x=round(ee_text.center_x - bbox_x, 2),
                    y=round(ee_text.center_y - bbox_y, 2),
                    r=_angle_to_ki(ee_text.rotation) or None,
                ),
                layer=kicad.pcb.TextLayer(layer=layer),
                hide=not ee_text.is_displayed if not ee_text.is_displayed else None,
                effects=kicad.pcb.Effects(
                    font=kicad.pcb.Font(
                        size=kicad.pcb.Wh(
                            w=round(max(ee_text.font_size, 1), 2),
                            h=round(max(ee_text.font_size, 1), 2),
                        ),
                        thickness=round(max(ee_text.stroke_width, 0.01), 2),
                    ),
                    justify=justify,
                ),
                uuid=kicad.gen_uuid(),
            )
        )

    # ── Fab reference text (%R) ──
    texts.append(
        kicad.pcb.FpText(
            type=kicad.pcb.E_fp_text_type.USER,
            text="%R",
            at=kicad.pcb.Xyr(x=0, y=0),
            layer=kicad.pcb.TextLayer(layer="F.Fab"),
            effects=kicad.pcb.Effects(
                font=kicad.pcb.Font(size=kicad.pcb.Wh(w=1, h=1), thickness=0.15),
            ),
            uuid=kicad.gen_uuid(),
        )
    )

    # ── 3D Model ──
    if ee_fp.model_3d is not None and model_path is not None:
        m3d = ee_fp.model_3d
        # Convert translation to mm
        tx = _to_mm(m3d.translation_x)
        ty = _to_mm(m3d.translation_y)
        tz = _to_mm(m3d.translation_z)

        offset_x = round(tx - bbox_x, 2)
        offset_y = -round(ty - bbox_y, 2)
        offset_z = -round(tz, 2) if ee_fp.fp_type == "smd" else 0

        # Apply SMD 3D model offset workaround
        if WORKAROUND_SMD_3D_MODEL_FIX:
            if ee_fp.fp_type == "smd" or re.search(r"[cCrR]0201", ee_fp.name):
                offset_x = 0
                offset_y = 0

        rot_x = (360 - m3d.rotation_x) % 360
        rot_y = (360 - m3d.rotation_y) % 360
        rot_z = (360 - m3d.rotation_z) % 360

        models.append(
            kicad.pcb.Model(
                path=f"{model_path}/{m3d.name}",
                offset=kicad.pcb.ModelXyz(
                    xyz=kicad.pcb.Xyz(x=offset_x, y=offset_y, z=offset_z)
                ),
                scale=kicad.pcb.ModelXyz(xyz=kicad.pcb.Xyz(x=1, y=1, z=1)),
                rotate=kicad.pcb.ModelXyz(xyz=kicad.pcb.Xyz(x=rot_x, y=rot_y, z=rot_z)),
            )
        )

    # ── Properties ──
    y_low = min((p.at.y for p in pads), default=0)
    y_high = max((p.at.y for p in pads), default=0)

    fp_effects = kicad.pcb.Effects(
        font=kicad.pcb.Font(size=kicad.pcb.Wh(w=1, h=1), thickness=0.15),
    )

    properties = [
        kicad.pcb.Property(
            name="Reference",
            value="REF**",
            at=kicad.pcb.Xyr(x=0, y=round(y_low - 4, 2)),
            layer="F.SilkS",
            uuid=kicad.gen_uuid(),
            effects=fp_effects,
        ),
        kicad.pcb.Property(
            name="Value",
            value=ee_fp.name,
            at=kicad.pcb.Xyr(x=0, y=round(y_high + 4, 2)),
            layer="F.Fab",
            uuid=kicad.gen_uuid(),
            effects=fp_effects,
        ),
    ]

    return kicad.footprint.FootprintFile(
        footprint=kicad.footprint.Footprint(
            name=f"easyeda2kicad:{ee_fp.name}",
            uuid=kicad.gen_uuid(),
            layer="F.Cu",
            propertys=properties,
            attr=["smd"] if ee_fp.fp_type == "smd" else ["through_hole"],
            fp_circles=circles,
            fp_lines=lines,
            fp_arcs=arcs,
            fp_rects=[],
            fp_poly=[],
            fp_texts=texts,
            pads=pads,
            models=models,
            version=20241229,
            generator="faebryk_convert",
            generator_version="v5",
            tags=[],
        )
    )


# ── Symbol builder ───────────────────────────────────────────────────────────


def _sanitize_name(name: str) -> str:
    return name.replace(" ", "").replace("/", "_")


def _apply_text_style(text: str) -> str:
    if text.endswith("#"):
        text = f"~{{{text[:-1]}}}"
    return text


def _apply_pin_name_style(pin_name: str) -> str:
    return "/".join(_apply_text_style(txt) for txt in pin_name.split("/"))


def build_symbol(
    ee_sym: EeSymbol,
    fp_lib_name: str,
) -> kicad.symbol.SymbolFile:
    """Build a KiCad SymbolFile directly from parsed EeSymbol data."""

    info = ee_sym.info
    sanitized_name = _sanitize_name(info.name)

    ki_units: list[kicad.schematic.SymbolUnit] = []
    all_pin_ys: list[float] = []

    default_stroke = kicad.schematic.Stroke(
        width=0, type="default", color=kicad.schematic.Color(r=0, g=0, b=0, a=0)
    )
    fill_bg = kicad.schematic.Fill(type="background")
    fill_none = kicad.schematic.Fill(type="none")
    pin_effects = kicad.pcb.Effects(
        font=kicad.pcb.Font(size=kicad.pcb.Wh(w=1.27, h=1.27)),
    )

    unit_number = 1 if len(ee_sym.units) > 1 else 0
    for ee_unit in ee_sym.units:
        unit_name = f"{sanitized_name}_{unit_number}_1"
        bbox_x = ee_unit.bbox_x
        bbox_y = ee_unit.bbox_y

        sch_pins: list[kicad.schematic.SymbolPin] = []
        sch_polylines: list[kicad.schematic.Polyline] = []
        sch_circles: list[kicad.schematic.Circle] = []
        sch_rects: list[kicad.schematic.Rect] = []
        sch_arcs: list[kicad.schematic.Arc] = []

        # ── Pins ──
        for ee_pin in ee_unit.pins:
            pin_x = round(_to_mm(int(ee_pin.pos_x) - int(bbox_x)), 2)
            pin_y = round(-_to_mm(int(ee_pin.pos_y) - int(bbox_y)), 2)
            all_pin_ys.append(pin_y)

            if ee_pin.has_dot and ee_pin.has_clock:
                pin_style = "inverted_clock"
            elif ee_pin.has_dot:
                pin_style = "inverted"
            elif ee_pin.has_clock:
                pin_style = "clock"
            else:
                pin_style = "line"

            sch_pins.append(
                kicad.schematic.SymbolPin(
                    at=kicad.pcb.Xyr(x=pin_x, y=pin_y, r=(180 + ee_pin.rotation) % 360),
                    length=round(_to_mm(ee_pin.length), 2),
                    type=KI_PIN_TYPE.get(ee_pin.pin_type, "unspecified"),
                    style=pin_style,
                    name=kicad.schematic.PinName(
                        name=_apply_pin_name_style(ee_pin.name), effects=pin_effects
                    ),
                    number=kicad.schematic.PinNumber(
                        number=ee_pin.number, effects=pin_effects
                    ),
                )
            )

        # ── Rectangles ──
        for ee_rect in ee_unit.rectangles:
            x0 = round(_to_mm(int(ee_rect.pos_x) - int(bbox_x)), 2)
            y0 = round(-_to_mm(int(ee_rect.pos_y) - int(bbox_y)), 2)
            x1 = round(_to_mm(int(ee_rect.width)) + x0, 2)
            y1 = round(-_to_mm(int(ee_rect.height)) + y0, 2)

            sch_rects.append(
                kicad.schematic.Rect(
                    start=kicad.pcb.Xy(x=x0, y=y0),
                    end=kicad.pcb.Xy(x=x1, y=y1),
                    stroke=default_stroke,
                    fill=fill_bg,
                )
            )

        # ── Circles ──
        for ee_circle in ee_unit.circles:
            cx = round(_to_mm(int(ee_circle.center_x) - int(bbox_x)), 2)
            cy = round(-_to_mm(int(ee_circle.center_y) - int(bbox_y)), 2)
            r = round(_to_mm(ee_circle.radius), 2)
            fill = fill_bg if ee_circle.fill else fill_none

            sch_circles.append(
                kicad.schematic.Circle(
                    center=kicad.pcb.Xy(x=cx, y=cy),
                    end=kicad.pcb.Xy(x=round(cx + r, 2), y=cy),
                    stroke=default_stroke,
                    fill=fill,
                )
            )

        # ── Ellipses → Circles (only if rx == ry) ──
        for ee_ellipse in ee_unit.ellipses:
            if ee_ellipse.radius_x != ee_ellipse.radius_y:
                continue
            cx = round(_to_mm(int(ee_ellipse.center_x) - int(bbox_x)), 2)
            cy = round(-_to_mm(int(ee_ellipse.center_y) - int(bbox_y)), 2)
            r = round(_to_mm(ee_ellipse.radius_x), 2)

            sch_circles.append(
                kicad.schematic.Circle(
                    center=kicad.pcb.Xy(x=cx, y=cy),
                    end=kicad.pcb.Xy(x=round(cx + r, 2), y=cy),
                    stroke=default_stroke,
                    fill=fill_none,
                )
            )

        # ── Polylines & Polygons ──
        for ee_polyline in ee_unit.polylines:
            raw_pts = re.findall(r"\S+", ee_polyline.points)
            x_pts = [
                round(_to_mm(int(float(raw_pts[i])) - int(bbox_x)), 2)
                for i in range(0, len(raw_pts), 2)
            ]
            y_pts = [
                round(-_to_mm(int(float(raw_pts[i])) - int(bbox_y)), 2)
                for i in range(1, len(raw_pts), 2)
            ]

            if ee_polyline.is_polygon or ee_polyline.fill:
                x_pts.append(x_pts[0])
                y_pts.append(y_pts[0])

            if x_pts and y_pts:
                pts = [
                    kicad.pcb.Xy(x=x_pts[i], y=y_pts[i])
                    for i in range(min(len(x_pts), len(y_pts)))
                ]
                is_closed = (
                    len(pts) >= 2 and pts[0].x == pts[-1].x and pts[0].y == pts[-1].y
                )
                sch_polylines.append(
                    kicad.schematic.Polyline(
                        pts=kicad.schematic.Pts(xys=pts),
                        stroke=default_stroke,
                        fill=fill_bg if is_closed else fill_none,
                    )
                )

        # ── Paths (SVG M/L/Z) ──
        for ee_path in ee_unit.paths:
            raw_pts = re.findall(r"\S+", ee_path.paths)
            x_pts: list[float] = []
            y_pts: list[float] = []
            i = 0
            while i < len(raw_pts):
                cmd = raw_pts[i]
                if cmd in ("M", "L") and i + 2 < len(raw_pts):
                    x_pts.append(
                        round(
                            _to_mm(int(float(raw_pts[i + 1])) - int(bbox_x)),
                            2,
                        )
                    )
                    y_pts.append(
                        round(
                            -_to_mm(int(float(raw_pts[i + 2])) - int(bbox_y)),
                            2,
                        )
                    )
                    i += 3
                elif cmd == "Z":
                    if x_pts and y_pts:
                        x_pts.append(x_pts[0])
                        y_pts.append(y_pts[0])
                    i += 1
                elif cmd == "C":
                    i += 7  # skip cubic bezier
                else:
                    i += 1

            if x_pts and y_pts:
                pts = [
                    kicad.pcb.Xy(x=x_pts[j], y=y_pts[j])
                    for j in range(min(len(x_pts), len(y_pts)))
                ]
                is_closed = (
                    len(pts) >= 2 and pts[0].x == pts[-1].x and pts[0].y == pts[-1].y
                )
                sch_polylines.append(
                    kicad.schematic.Polyline(
                        pts=kicad.schematic.Pts(xys=pts),
                        stroke=default_stroke,
                        fill=fill_bg if is_closed else fill_none,
                    )
                )

        # ── Arcs ──
        for ee_arc in ee_unit.arcs:
            try:
                parsed = _parse_svg_path_for_arc(ee_arc.path)
                if parsed is None:
                    continue
                move_x, move_y, arc_params = parsed
                rx_raw, ry_raw, x_rot, large_arc, sweep, end_x_raw, end_y_raw = (
                    arc_params
                )

                start_x = _to_mm(move_x - bbox_x)
                start_y = _to_mm(move_y - bbox_y)
                arc_end_x = _to_mm(end_x_raw - bbox_x)
                arc_end_y = _to_mm(end_y_raw - bbox_y)
                rx = _to_mm(rx_raw)
                ry = _to_mm(ry_raw)

                cx, cy, extent = _compute_arc(
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

                # Schematic Y axis is flipped; large_arc needs different handling
                if not large_arc:
                    cy, start_y, arc_end_y = -cy, -start_y, -arc_end_y
                else:
                    extent = 360 - extent

                radius = max(rx, ry)
                mid_x, mid_y = _arc_midpoint(cx, cy, radius, x_rot, extent)

                sch_arcs.append(
                    kicad.schematic.Arc(
                        start=kicad.pcb.Xy(x=round(start_x, 2), y=round(start_y, 2)),
                        mid=kicad.pcb.Xy(x=round(mid_x, 2), y=round(mid_y, 2)),
                        end=kicad.pcb.Xy(x=round(arc_end_x, 2), y=round(arc_end_y, 2)),
                        stroke=default_stroke,
                        fill=fill_bg if ee_arc.fill else fill_none,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse symbol arc: {e}")

        ki_units.append(
            kicad.schematic.SymbolUnit(
                name=unit_name,
                polylines=sch_polylines,
                circles=sch_circles,
                rectangles=sch_rects,
                arcs=sch_arcs,
                pins=sch_pins,
            )
        )
        unit_number += 1

    # ── Symbol properties ──
    y_low = min(all_pin_ys) if all_pin_ys else 0
    y_high = max(all_pin_ys) if all_pin_ys else 0
    field_offset = 5.08

    sym_effects = kicad.pcb.Effects(
        font=kicad.pcb.Font(size=kicad.pcb.Wh(w=1.27, h=1.27)),
    )

    properties: list[kicad.schematic.Property] = [
        kicad.schematic.Property(
            name="Reference",
            value=info.prefix.replace("?", ""),
            id=0,
            at=kicad.pcb.Xyr(x=0, y=y_high + field_offset, r=0),
            effects=sym_effects,
        ),
        kicad.schematic.Property(
            name="Value",
            value=info.name,
            id=1,
            at=kicad.pcb.Xyr(x=0, y=y_low - field_offset, r=0),
            effects=sym_effects,
        ),
    ]

    next_id = 2
    next_y = field_offset + 2.54

    if info.package:
        properties.append(
            kicad.schematic.Property(
                name="Footprint",
                value=f"{fp_lib_name}:{info.package}",
                id=next_id,
                at=kicad.pcb.Xyr(x=0, y=y_low - next_y, r=0),
                effects=sym_effects,
            )
        )
        next_id += 1
        next_y += 2.54

    if info.datasheet:
        properties.append(
            kicad.schematic.Property(
                name="Datasheet",
                value=info.datasheet,
                id=next_id,
                at=kicad.pcb.Xyr(x=0, y=y_low - next_y, r=0),
                effects=sym_effects,
            )
        )
        next_id += 1
        next_y += 2.54

    if info.manufacturer:
        properties.append(
            kicad.schematic.Property(
                name="Manufacturer",
                value=info.manufacturer,
                id=next_id,
                at=kicad.pcb.Xyr(x=0, y=y_low - next_y, r=0),
                effects=sym_effects,
            )
        )
        next_id += 1
        next_y += 2.54

    if info.lcsc_id:
        properties.append(
            kicad.schematic.Property(
                name="LCSC Part",
                value=info.lcsc_id,
                id=next_id,
                at=kicad.pcb.Xyr(x=0, y=y_low - next_y, r=0),
                effects=sym_effects,
            )
        )
        next_id += 1
        next_y += 2.54

    if info.jlc_id:
        properties.append(
            kicad.schematic.Property(
                name="JLC Part",
                value=info.jlc_id,
                id=next_id,
                at=kicad.pcb.Xyr(x=0, y=y_low - next_y, r=0),
                effects=sym_effects,
            )
        )

    return kicad.symbol.SymbolFile(
        kicad_sym=kicad.symbol.SymbolLib(
            version=20241229,
            generator="faebryk_convert",
            symbols=[
                kicad.schematic.Symbol(
                    name=sanitized_name,
                    power=False,
                    propertys=properties,
                    in_bom=True,
                    on_board=True,
                    symbols=ki_units,
                )
            ],
        )
    )


def _parse_svg_path_for_arc(
    path: str,
) -> tuple[float, float, tuple[float, float, float, bool, bool, float, float]] | None:
    """Parse an SVG path containing M...A... for arc conversion."""
    path = path.replace(",", " ")
    if "M" not in path or "A" not in path:
        return None

    parts = re.findall(r"([MA])([\s\d.eE+\-]+)", path)
    move_data = None
    arc_data = None
    for cmd, args in parts:
        nums = [float(x) for x in args.split()]
        if cmd == "M" and len(nums) >= 2:
            move_data = (nums[0], nums[1])
        elif cmd == "A" and len(nums) >= 7:
            arc_data = (
                nums[0],
                nums[1],
                nums[2],
                bool(nums[3]),
                bool(nums[4]),
                nums[5],
                nums[6],
            )

    if move_data is None or arc_data is None:
        return None

    return move_data[0], move_data[1], arc_data


# ── Tests ─────────────────────────────────────────────────────────────────────

import pytest  # noqa: E402

from faebryk.libs.easyeda.easyeda_types import (  # noqa: E402
    EeFpHole,
    EeFpPad,
    EeFpRect,
    EeSymbolInfo,
    EeSymbolUnit,
    EeSymPin,
)
from faebryk.libs.easyeda.parser import (  # noqa: E402
    _opamp_cad_data,
    _resistor_cad_data,
    _tht_cad_data,
    parse_footprint,
    parse_symbol,
)


def test_fp_to_ki_conversion():
    assert _fp_to_ki(0) == 0
    assert _fp_to_ki("100") == pytest.approx(25.4, abs=0.01)
    assert _fp_to_ki("invalid") == 0.0


def test_build_fp_resistor_structure():
    fp = parse_footprint(_resistor_cad_data())
    result = build_footprint(fp)
    assert isinstance(result, kicad.footprint.FootprintFile)
    assert result.footprint.name == "easyeda2kicad:R0603"


def test_build_fp_resistor_attr_smd():
    fp = parse_footprint(_resistor_cad_data())
    result = build_footprint(fp)
    assert "smd" in result.footprint.attr


def test_build_fp_resistor_pads():
    fp = parse_footprint(_resistor_cad_data())
    result = build_footprint(fp)
    assert len(result.footprint.pads) == 2
    for pad in result.footprint.pads:
        assert pad.type == "smd"
        assert pad.shape == "rect"
        assert pad.drill is None


def test_build_fp_resistor_pad_positions_are_relative():
    fp = parse_footprint(_resistor_cad_data())
    result = build_footprint(fp)
    for pad in result.footprint.pads:
        assert abs(pad.at.x) < 10
        assert abs(pad.at.y) < 10


def test_build_fp_resistor_lines():
    fp = parse_footprint(_resistor_cad_data())
    result = build_footprint(fp)
    assert len(result.footprint.fp_lines) >= 4


def test_build_fp_resistor_circles():
    fp = parse_footprint(_resistor_cad_data())
    result = build_footprint(fp)
    assert len(result.footprint.fp_circles) == 1


def test_build_fp_resistor_properties():
    fp = parse_footprint(_resistor_cad_data())
    result = build_footprint(fp)
    props = result.footprint.propertys
    assert len(props) == 2
    ref = next(p for p in props if p.name == "Reference")
    val = next(p for p in props if p.name == "Value")
    assert ref.value == "REF**"
    assert val.value == "R0603"


def test_build_fp_resistor_3d_model():
    fp = parse_footprint(_resistor_cad_data())
    result = build_footprint(fp, model_path="/models")
    assert len(result.footprint.models) == 1
    assert result.footprint.models[0].path == "/models/R0603"


def test_build_fp_smd_3d_model_offset_workaround():
    fp = parse_footprint(_resistor_cad_data())
    result = build_footprint(fp, model_path="/models")
    model = result.footprint.models[0]
    assert model.offset.xyz.x == 0
    assert model.offset.xyz.y == 0


def test_build_fp_no_model_without_path():
    fp = parse_footprint(_resistor_cad_data())
    result = build_footprint(fp, model_path=None)
    assert len(result.footprint.models) == 0


def test_build_fp_tht_attr():
    fp = parse_footprint(_tht_cad_data())
    result = build_footprint(fp)
    assert "through_hole" in result.footprint.attr


def test_build_fp_tht_pads_have_drill():
    fp = parse_footprint(_tht_cad_data())
    result = build_footprint(fp)
    tht_pads = [p for p in result.footprint.pads if p.type == "thru_hole"]
    # 8 signal pads + 1 hole (also thru_hole per old behavior)
    assert len(tht_pads) == 9
    for pad in tht_pads:
        assert pad.drill is not None
        assert pad.drill.size_x > 0


def test_build_fp_tht_pad_layers():
    fp = parse_footprint(_tht_cad_data())
    result = build_footprint(fp)
    for pad in result.footprint.pads:
        if pad.type == "thru_hole":
            assert "*.Cu" in pad.layers
            assert "*.Mask" in pad.layers


def test_build_fp_opamp_arc():
    fp = parse_footprint(_opamp_cad_data())
    result = build_footprint(fp)
    assert len(result.footprint.fp_arcs) == 1
    arc = result.footprint.fp_arcs[0]
    assert arc.start is not None
    assert arc.mid is not None
    assert arc.end is not None


def test_build_fp_version_and_generator():
    fp = parse_footprint(_resistor_cad_data())
    result = build_footprint(fp)
    assert result.footprint.version == 20241229
    assert result.footprint.generator == "faebryk_convert"


def test_build_sym_resistor_structure():
    sym = parse_symbol(_resistor_cad_data())
    result = build_symbol(sym, fp_lib_name="easyeda2kicad")
    assert isinstance(result, kicad.symbol.SymbolFile)
    assert len(result.kicad_sym.symbols) == 1
    assert result.kicad_sym.symbols[0].name == "0603WAF1001T5E"


def test_build_sym_resistor_pins():
    sym = parse_symbol(_resistor_cad_data())
    result = build_symbol(sym, fp_lib_name="easyeda2kicad")
    unit = result.kicad_sym.symbols[0].symbols[0]
    assert len(unit.pins) == 2
    assert {p.number.number for p in unit.pins} == {"1", "2"}


def test_build_sym_resistor_rectangle():
    sym = parse_symbol(_resistor_cad_data())
    result = build_symbol(sym, fp_lib_name="easyeda2kicad")
    unit = result.kicad_sym.symbols[0].symbols[0]
    assert len(unit.rectangles) == 1


def test_build_sym_resistor_properties():
    sym = parse_symbol(_resistor_cad_data())
    result = build_symbol(sym, fp_lib_name="easyeda2kicad")
    symbol = result.kicad_sym.symbols[0]
    prop_names = {p.name for p in symbol.propertys}
    assert "Reference" in prop_names
    assert "Value" in prop_names
    assert "Footprint" in prop_names
    assert "Datasheet" in prop_names
    assert "LCSC Part" in prop_names


def test_build_sym_resistor_footprint_property():
    sym = parse_symbol(_resistor_cad_data())
    result = build_symbol(sym, fp_lib_name="mylib")
    symbol = result.kicad_sym.symbols[0]
    fp_prop = next(p for p in symbol.propertys if p.name == "Footprint")
    assert fp_prop.value == "mylib:R0603"


def test_build_sym_opamp_pins():
    sym = parse_symbol(_opamp_cad_data())
    result = build_symbol(sym, fp_lib_name="easyeda2kicad")
    unit = result.kicad_sym.symbols[0].symbols[0]
    assert len(unit.pins) == 8


def test_build_sym_opamp_pin_orientation():
    sym = parse_symbol(_opamp_cad_data())
    result = build_symbol(sym, fp_lib_name="easyeda2kicad")
    unit = result.kicad_sym.symbols[0].symbols[0]
    orientations = {p.at.r for p in unit.pins}
    assert 0 in orientations
    assert 180 in orientations


def test_build_sym_opamp_circles():
    sym = parse_symbol(_opamp_cad_data())
    result = build_symbol(sym, fp_lib_name="easyeda2kicad")
    unit = result.kicad_sym.symbols[0].symbols[0]
    assert len(unit.circles) >= 1


def test_build_sym_version():
    sym = parse_symbol(_resistor_cad_data())
    result = build_symbol(sym, fp_lib_name="easyeda2kicad")
    assert result.kicad_sym.version == 20241229


# ── KiCad serialization round-trip ───────────────────────────────────────────


def test_kicad_fp_dumps():
    fp = parse_footprint(_resistor_cad_data())
    result = build_footprint(fp)
    text = kicad.dumps(result)
    assert text.startswith("(footprint")
    assert "easyeda2kicad:R0603" in text
    assert "REF**" in text


def test_kicad_sym_dumps():
    sym = parse_symbol(_resistor_cad_data())
    result = build_symbol(sym, fp_lib_name="easyeda2kicad")
    text = kicad.dumps(result)
    assert "kicad_symbol_lib" in text
    assert "0603WAF1001T5E" in text


def test_kicad_tht_fp_dumps():
    fp = parse_footprint(_tht_cad_data())
    result = build_footprint(fp)
    text = kicad.dumps(result)
    assert "thru_hole" in text
    assert "(drill" in text


def test_kicad_opamp_fp_dumps():
    fp = parse_footprint(_opamp_cad_data())
    result = build_footprint(fp)
    text = kicad.dumps(result)
    assert "(arc" in text.lower() or "(fp_arc" in text.lower()


def test_kicad_opamp_sym_dumps():
    sym = parse_symbol(_opamp_cad_data())
    result = build_symbol(sym, fp_lib_name="easyeda2kicad")
    text = kicad.dumps(result)
    assert "1OUT" in text
    assert "VCC" in text
    assert "pin" in text.lower()


# ── Arc geometry ─────────────────────────────────────────────────────────────


def test_compute_arc_quarter_circle():
    r = 5
    cx, cy, extent = _compute_arc(
        start_x=r,
        start_y=0,
        radius_x=r,
        radius_y=r,
        angle=0,
        large_arc_flag=False,
        sweep_flag=True,
        end_x=0,
        end_y=r,
    )
    assert cx == pytest.approx(0.0, abs=0.1)
    assert cy == pytest.approx(0.0, abs=0.1)
    assert abs(extent) == pytest.approx(90.0, abs=1.0)


def test_compute_arc_small():
    cx, cy, extent = _compute_arc(
        start_x=10,
        start_y=0,
        radius_x=10,
        radius_y=10,
        angle=0,
        large_arc_flag=False,
        sweep_flag=False,
        end_x=0,
        end_y=-10,
    )
    assert cx == pytest.approx(0.0, abs=0.5)
    assert cy == pytest.approx(0.0, abs=0.5)
    assert abs(extent) == pytest.approx(90.0, abs=2.0)


def test_compute_arc_zero_radius():
    cx, cy, extent = _compute_arc(0, 0, 0, 0, 0, False, False, 1, 1)
    assert math.isfinite(cx)
    assert math.isfinite(cy)


def test_compute_arc_large_vs_small():
    _, _, ext_small = _compute_arc(10, 0, 10, 10, 0, False, True, 0, 10)
    _, _, ext_large = _compute_arc(10, 0, 10, 10, 0, True, True, 0, 10)
    assert abs(ext_large) > abs(ext_small)


def test_compute_arc_sweep_direction():
    _, _, ext_cw = _compute_arc(10, 0, 10, 10, 0, False, True, 0, 10)
    _, _, ext_ccw = _compute_arc(10, 0, 10, 10, 0, False, False, 0, 10)
    assert ext_cw * ext_ccw < 0


def test_compute_arc_real_world():
    cx, cy, extent = _compute_arc(
        start_x=3990.1575,
        start_y=3002.8605,
        radius_x=2.8648,
        radius_y=2.8648,
        angle=0,
        large_arc_flag=False,
        sweep_flag=False,
        end_x=3990.1768,
        end_y=2997.1406,
    )
    assert math.isfinite(cx)
    assert math.isfinite(cy)
    assert math.isfinite(extent)


# ── Edge cases ───────────────────────────────────────────────────────────────


def test_pad_number_with_parentheses():
    fp = EeFootprint(name="TEST", fp_type="smd", bbox_x=0, bbox_y=0)
    fp.pads.append(
        EeFpPad(
            shape="RECT",
            center_x=0,
            center_y=0,
            width=1,
            height=1,
            layer_id=1,
            net="",
            number="A(1)",
            hole_radius=0,
            points="",
            rotation=0,
            id="id1",
            hole_length=0,
            hole_point="",
            is_plated=True,
            is_locked=False,
        )
    )
    result = build_footprint(fp)
    assert result.footprint.pads[0].name == "1"


def test_polygon_pad():
    fp = EeFootprint(name="TEST", fp_type="smd", bbox_x=0, bbox_y=0)
    fp.pads.append(
        EeFpPad(
            shape="POLYGON",
            center_x=0.5,
            center_y=0.5,
            width=1,
            height=1,
            layer_id=1,
            net="",
            number="1",
            hole_radius=0,
            points="0 0 100 0 100 100 0 100",
            rotation=0,
            id="id1",
            hole_length=0,
            hole_point="",
            is_plated=True,
            is_locked=False,
        )
    )
    result = build_footprint(fp)
    pad = result.footprint.pads[0]
    assert pad.shape == "custom"
    assert pad.primitives is not None


def test_rectangle_to_lines():
    fp = EeFootprint(name="TEST", fp_type="smd", bbox_x=0, bbox_y=0)
    fp.rects.append(
        EeFpRect(
            x=1,
            y=1,
            width=2,
            height=3,
            stroke_width=0.1,
            id="id1",
            layer_id=3,
            is_locked=False,
        )
    )
    result = build_footprint(fp)
    assert len(result.footprint.fp_lines) == 4


def test_hole_to_thru_hole():
    fp = EeFootprint(name="TEST", fp_type="tht", bbox_x=0, bbox_y=0)
    fp.holes.append(
        EeFpHole(
            center_x=5,
            center_y=5,
            radius=1.5,
            id="h1",
            is_locked=False,
        )
    )
    result = build_footprint(fp)
    assert len(result.footprint.pads) == 1
    pad = result.footprint.pads[0]
    assert pad.type == "thru_hole"
    assert pad.name == ""
    assert pad.drill is not None
    assert pad.drill.size_x == pytest.approx(3.0, abs=0.01)


def test_oval_drill():
    fp = EeFootprint(name="TEST", fp_type="tht", bbox_x=0, bbox_y=0)
    fp.pads.append(
        EeFpPad(
            shape="ELLIPSE",
            center_x=5,
            center_y=5,
            width=3,
            height=3,
            layer_id=11,
            net="",
            number="1",
            hole_radius=0.5,
            points="",
            rotation=0,
            id="id1",
            hole_length=1.0,
            hole_point="",
            is_plated=True,
            is_locked=False,
        )
    )
    result = build_footprint(fp)
    pad = result.footprint.pads[0]
    assert pad.drill is not None
    assert pad.drill.shape == "oval"


def _make_test_sym(pin: EeSymPin) -> EeSymbol:
    """Helper to build a minimal EeSymbol with a single pin for testing."""
    sym = EeSymbol(
        info=EeSymbolInfo(
            name="TEST",
            prefix="U?",
            package="PKG",
            manufacturer="",
            datasheet="",
            lcsc_id="",
            jlc_id="",
        ),
    )
    sym.units.append(EeSymbolUnit(bbox_x=400, bbox_y=300, pins=[pin]))
    return sym


def _make_test_pin(**kwargs) -> EeSymPin:
    defaults = dict(
        name="X",
        number="1",
        pos_x=350,
        pos_y=290,
        rotation=180,
        pin_type=0,
        has_dot=False,
        has_clock=False,
        length=10,
    )
    defaults.update(kwargs)
    return EeSymPin(**defaults)


def test_symbol_pin_name_overbar():
    sym = _make_test_sym(_make_test_pin(name="RESET#", pin_type=1))
    pin = build_symbol(sym, fp_lib_name="lib").kicad_sym.symbols[0].symbols[0].pins[0]
    assert pin.name.name == "~{RESET}"


def test_symbol_pin_dot_style():
    sym = _make_test_sym(_make_test_pin(name="EN", has_dot=True))
    pin = build_symbol(sym, fp_lib_name="lib").kicad_sym.symbols[0].symbols[0].pins[0]
    assert pin.style == "inverted"


def test_symbol_pin_clock_style():
    sym = _make_test_sym(_make_test_pin(name="CLK", has_clock=True))
    pin = build_symbol(sym, fp_lib_name="lib").kicad_sym.symbols[0].symbols[0].pins[0]
    assert pin.style == "clock"


def test_symbol_pin_inverted_clock_style():
    sym = _make_test_sym(_make_test_pin(name="CLK", has_dot=True, has_clock=True))
    pin = build_symbol(sym, fp_lib_name="lib").kicad_sym.symbols[0].symbols[0].pins[0]
    assert pin.style == "inverted_clock"
