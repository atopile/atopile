# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""Single-pass EasyEDA → KiCad footprint builder.

Takes raw API JSON and produces a KiCad FootprintFile directly — no intermediate
dataclasses. Each ``_build_*`` method parses its tilde-split fields and constructs
KiCad types in one step.

Legacy Compatibility
--------------------
Several workarounds exist to match the output of the original easyeda2kicad
pipeline.  These are tagged with ``# LEGACY:`` comments.
"""

import json
import logging
import re

from faebryk.libs.easyeda._arc import (
    compute_arc,
    parse_svg_path_for_arc,
)
from faebryk.libs.easyeda._geometry import (
    KI_PAD_SIZE_MIN,
    find_anchor_position,
    is_circle_in_polygon,
)
from faebryk.libs.easyeda._parse import (
    bool_field,
    get,
    parse_float,
    parse_int,
    text_is_displayed,
)
from faebryk.libs.easyeda._types import (
    Ee3dModelInfo,
    EePadShape,
)
from faebryk.libs.easyeda._units import (
    MIN_STROKE_W,
    angle_to_ki,
    fp_xy,
    to_mm,
)
from faebryk.libs.kicad.fileformats import kicad

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

_KI_PAD_SHAPE = {
    EePadShape.ELLIPSE: kicad.pcb.E_pad_shape.CIRCLE,
    EePadShape.RECT: kicad.pcb.E_pad_shape.RECT,
    EePadShape.OVAL: kicad.pcb.E_pad_shape.OVAL,
    EePadShape.POLYGON: kicad.pcb.E_pad_shape.CUSTOM,
}

_KI_PAD_LAYERS: dict[int, list[str]] = {
    1: ["F.Cu", "F.Paste", "F.Mask"],
    2: ["B.Cu", "B.Paste", "B.Mask"],
    3: ["F.SilkS"],
    11: ["*.Cu", "*.Paste", "*.Mask"],
    13: ["F.Fab"],
    15: ["Dwgs.User"],
}

_KI_PAD_LAYERS_THT: dict[int, list[str]] = {
    1: ["F.Cu", "F.Mask"],
    2: ["B.Cu", "B.Mask"],
    3: ["F.SilkS"],
    11: ["*.Cu", "*.Mask"],
    13: ["F.Fab"],
    15: ["Dwgs.User"],
}

_KI_LAYERS: dict[int, str] = {
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


def _ki_pad(
    *,
    name: str,
    type: str,
    shape: str,
    at: kicad.pcb.Xyr,
    size: kicad.pcb.Wh,
    drill: kicad.pcb.PadDrill | None,
    layers: list[str],
    uuid: str | None = None,
    primitives: kicad.pcb.PadPrimitives | None = None,
) -> kicad.pcb.Pad:
    return kicad.pcb.Pad(
        name=name,
        type=type,
        shape=shape,
        at=at,
        size=size,
        drill=drill,
        layers=layers,
        remove_unused_layers=None,
        net=None,
        solder_mask_margin=None,
        solder_paste_margin=None,
        solder_paste_margin_ratio=None,
        clearance=None,
        zone_connect=None,
        thermal_bridge_width=None,
        thermal_gap=None,
        roundrect_rratio=None,
        chamfer_ratio=None,
        chamfer=None,
        properties=None,
        options=None,
        tenting=None,
        uuid=uuid,
        primitives=primitives,
    )


def _ki_line(
    *,
    start: kicad.pcb.Xy,
    end: kicad.pcb.Xy,
    stroke: kicad.pcb.Stroke,
    layer: str,
    uuid: str | None = None,
) -> kicad.pcb.Line:
    return kicad.pcb.Line(
        start=start,
        end=end,
        solder_mask_margin=None,
        stroke=stroke,
        fill=None,
        layer=layer,
        layers=[layer],
        locked=False,
        uuid=uuid,
    )


# ── FootprintBuilder ────────────────────────────────────────────────────────


class FootprintBuilder:
    """Build a KiCad FootprintFile directly from raw EasyEDA API data."""

    def __init__(self, cad_data: dict):
        pkg = cad_data["packageDetail"]
        data = pkg["dataStr"]
        info = data["head"]["c_para"]
        self._name = info["package"]
        self._bbox_x = to_mm(float(data["head"]["x"]))
        self._bbox_y = to_mm(float(data["head"]["y"]))
        self._is_smd = bool(cad_data.get("SMT")) and "-TH_" not in pkg.get("title", "")
        self._shapes = data["shape"]

        # Pre-scan for 3D model info (callers need it before build() to
        # compute model_path).
        self._model_3d: Ee3dModelInfo | None = None
        for raw_line in self._shapes:
            designator, *fields = raw_line.split("~")
            if designator == "SVGNODE":
                self._model_3d = self._parse_3d_model(fields)
                break

    @property
    def model_3d(self) -> Ee3dModelInfo | None:
        """3D model info extracted from the raw data.  Available immediately."""
        return self._model_3d

    # ── coordinate helpers ───────────────────────────────────────────────

    def _xy(self, x: float, y: float) -> tuple[float, float]:
        return fp_xy(x, y, self._bbox_x, self._bbox_y)

    def _layer(self, layer_id: int) -> str:
        return _KI_LAYERS.get(layer_id, "F.Fab")

    def _pad_layers(self, layer_id: int, is_tht: bool) -> list[str]:
        layer_map = _KI_PAD_LAYERS_THT if is_tht else _KI_PAD_LAYERS
        return layer_map.get(layer_id, [])

    def _track_layer(self, layer_id: int) -> str:
        if layer_id in _KI_PAD_LAYERS:
            return " ".join(_KI_PAD_LAYERS[layer_id])
        return "F.Fab"

    def _stroke(self, width: float) -> kicad.pcb.Stroke:
        return kicad.pcb.Stroke(
            width=round(max(width, MIN_STROKE_W), 2),
            type=kicad.pcb.E_stroke_type.SOLID,
        )

    @staticmethod
    def _to_ki(val: str) -> float:
        """Parse raw EE-unit string → mm, rounded to 2dp."""
        try:
            return round(to_mm(float(val)), 2)
        except (ValueError, TypeError):
            return 0.0

    # ── shape builders ───────────────────────────────────────────────────

    def _build_pad(self, f: list[str]) -> kicad.pcb.Pad:
        shape = EePadShape(get(f, 0))
        cx = to_mm(parse_float(get(f, 1)))
        cy = to_mm(parse_float(get(f, 2)))
        w = to_mm(parse_float(get(f, 3)))
        h = to_mm(parse_float(get(f, 4)))
        layer_id = parse_int(get(f, 5), default=1)
        number = get(f, 7)
        hole_radius = to_mm(parse_float(get(f, 8)))
        points_raw = get(f, 9)
        rotation = parse_float(get(f, 10))
        hole_length = to_mm(parse_float(get(f, 12)))

        is_tht = hole_radius > 0
        pad_type = (
            kicad.pcb.E_pad_type.THRU_HOLE if is_tht else kicad.pcb.E_pad_type.SMD
        )
        ki_shape = _KI_PAD_SHAPE.get(shape, kicad.pcb.E_pad_shape.CUSTOM)
        layers = self._pad_layers(layer_id, is_tht)

        pos_x, pos_y = self._xy(cx, cy)
        width = round(max(w, MIN_STROKE_W), 2)
        height = round(max(h, MIN_STROKE_W), 2)
        orientation = round(angle_to_ki(rotation), 2)

        if "(" in number and ")" in number:
            number = number.split("(")[1].split(")")[0]

        # Drill
        drill = None
        if hole_radius > 0:
            hr = round(hole_radius, 2)
            hl = round(hole_length, 2) if hole_length else 0
            if hl and hl != 0:
                max_dist_hole = max(hr * 2, hl)
                if height - max_dist_hole >= width - max_dist_hole:
                    drill = kicad.pcb.PadDrill(
                        shape=kicad.pcb.E_pad_drill_shape.OVAL,
                        size_x=round(hr * 2, 2),
                        size_y=hl,
                        offset=None,
                    )
                else:
                    drill = kicad.pcb.PadDrill(
                        shape=kicad.pcb.E_pad_drill_shape.OVAL,
                        size_x=hl,
                        size_y=round(hr * 2, 2),
                        offset=None,
                    )
            else:
                drill = kicad.pcb.PadDrill(
                    shape=None,
                    size_x=round(2 * hr, 2),
                    size_y=None,
                    offset=None,
                )

        # Custom polygon pad
        primitives = None
        if ki_shape == kicad.pcb.E_pad_shape.CUSTOM and points_raw:
            point_list = [self._to_ki(p) for p in points_raw.split()]
            width = KI_PAD_SIZE_MIN
            height = KI_PAD_SIZE_MIN
            orientation = 0

            absolute_coords = [
                (
                    point_list[i] - self._bbox_x,
                    point_list[i + 1] - self._bbox_y,
                )
                for i in range(0, len(point_list) - 1, 2)
            ]

            if not is_circle_in_polygon((pos_x, pos_y), width / 2, absolute_coords):
                new_center = find_anchor_position(absolute_coords, width / 2)
                if new_center is not None:
                    pos_x, pos_y = new_center
                else:
                    logger.warning(
                        f"Custom pad #{number}: anchor pad cannot be "
                        "contained within polygon"
                    )

            poly_pts = [
                kicad.pcb.Xy(
                    x=round(x - pos_x, 2),
                    y=round(y - pos_y, 2),
                )
                for x, y in absolute_coords
            ]
            if poly_pts:
                primitives = kicad.pcb.PadPrimitives(
                    gr_polys=[
                        kicad.pcb.Polygon(
                            pts=kicad.pcb.Pts(xys=poly_pts),
                            solder_mask_margin=None,
                            stroke=None,
                            fill=None,
                            layer=None,
                            layers=[],
                            locked=None,
                            uuid=None,
                        )
                    ]
                )

        return _ki_pad(
            name=number,
            type=pad_type,
            shape=ki_shape,
            at=kicad.pcb.Xyr(
                x=pos_x,
                y=pos_y,
                r=orientation if orientation else None,
            ),
            size=kicad.pcb.Wh(w=width, h=height),
            drill=drill,
            layers=layers,
            uuid=kicad.gen_uuid(),
            primitives=primitives,
        )

    def _build_track(self, f: list[str]) -> list[kicad.pcb.Line]:
        stroke_width = to_mm(parse_float(get(f, 0)))
        layer_id = parse_int(get(f, 1), default=1)
        points_raw = get(f, 3)

        layer_str = self._track_layer(layer_id)
        stroke = self._stroke(stroke_width)

        point_list = [self._to_ki(p) for p in points_raw.split()]
        lines = []
        for i in range(0, len(point_list) - 2, 2):
            sx, sy = self._xy(point_list[i], point_list[i + 1])
            ex, ey = self._xy(point_list[i + 2], point_list[i + 3])
            lines.append(
                _ki_line(
                    start=kicad.pcb.Xy(x=sx, y=sy),
                    end=kicad.pcb.Xy(x=ex, y=ey),
                    stroke=stroke,
                    layer=layer_str,
                    uuid=kicad.gen_uuid(),
                )
            )
        return lines

    def _build_hole(self, f: list[str]) -> kicad.pcb.Pad:
        # LEGACY: Holes are emitted as thru_hole pads (not NPTH)
        # to match old pipeline output.
        cx = to_mm(parse_float(get(f, 0)))
        cy = to_mm(parse_float(get(f, 1)))
        radius = to_mm(parse_float(get(f, 2)))

        size = round(radius * 2, 2)
        hx, hy = self._xy(cx, cy)
        return _ki_pad(
            name="",
            type=kicad.pcb.E_pad_type.THRU_HOLE,
            shape=kicad.pcb.E_pad_shape.CIRCLE,
            at=kicad.pcb.Xyr(x=hx, y=hy, r=None),
            size=kicad.pcb.Wh(w=size, h=size),
            drill=kicad.pcb.PadDrill(shape=None, size_x=size, size_y=None, offset=None),
            layers=["*.Cu", "*.Mask"],
            uuid=kicad.gen_uuid(),
        )

    def _build_via(self, f: list[str]) -> kicad.pcb.Pad:
        cx = to_mm(parse_float(get(f, 0)))
        cy = to_mm(parse_float(get(f, 1)))
        diameter = to_mm(parse_float(get(f, 2)))
        radius = to_mm(parse_float(get(f, 4)))

        drill_size = round(radius * 2, 2)
        dia = round(diameter, 2)
        vx, vy = self._xy(cx, cy)
        return _ki_pad(
            name="",
            type=kicad.pcb.E_pad_type.THRU_HOLE,
            shape=kicad.pcb.E_pad_shape.CIRCLE,
            at=kicad.pcb.Xyr(x=vx, y=vy, r=None),
            size=kicad.pcb.Wh(w=dia, h=dia),
            drill=kicad.pcb.PadDrill(
                shape=None,
                size_x=drill_size,
                size_y=None,
                offset=None,
            ),
            layers=["*.Cu", "*.Paste", "*.Mask"],
            uuid=kicad.gen_uuid(),
        )

    def _build_circle(self, f: list[str]) -> kicad.pcb.Circle:
        cx = to_mm(parse_float(get(f, 0)))
        cy = to_mm(parse_float(get(f, 1)))
        radius = to_mm(parse_float(get(f, 2)))
        stroke_width = to_mm(parse_float(get(f, 3)))
        layer_id = parse_int(get(f, 4), default=1)

        x, y = self._xy(cx, cy)
        return kicad.pcb.Circle(
            center=kicad.pcb.Xy(x=x, y=y),
            end=kicad.pcb.Xy(x=round(x + radius, 2), y=y),
            solder_mask_margin=None,
            stroke=self._stroke(stroke_width),
            fill=None,
            layer=self._layer(layer_id),
            layers=[],
            locked=False,
            uuid=kicad.gen_uuid(),
        )

    def _build_rect(self, f: list[str]) -> list[kicad.pcb.Line]:
        pos_x = to_mm(parse_float(get(f, 0)))
        pos_y = to_mm(parse_float(get(f, 1)))
        width = to_mm(parse_float(get(f, 2)))
        height = to_mm(parse_float(get(f, 3)))
        layer_id = parse_int(get(f, 4), default=1)
        stroke_width = to_mm(parse_float(get(f, 7)))

        layer = self._track_layer(layer_id)
        stroke = self._stroke(stroke_width)

        sx, sy = self._xy(pos_x, pos_y)
        w = round(width, 2)
        h = round(height, 2)

        starts_x = [sx, sx + w, sx + w, sx]
        starts_y = [sy, sy, sy + h, sy]
        ends_x = [sx + w, sx + w, sx, sx]
        ends_y = [sy, sy + h, sy + h, sy]

        return [
            _ki_line(
                start=kicad.pcb.Xy(x=starts_x[i], y=starts_y[i]),
                end=kicad.pcb.Xy(x=ends_x[i], y=ends_y[i]),
                stroke=stroke,
                layer=layer,
                uuid=kicad.gen_uuid(),
            )
            for i in range(4)
        ]

    def _build_arc(self, f: list[str]) -> kicad.pcb.Arc | None:
        stroke_width = to_mm(parse_float(get(f, 0)))
        layer_id = parse_int(get(f, 1), default=1)
        path = get(f, 3)

        try:
            parsed = parse_svg_path_for_arc(path)
            if parsed is None:
                return None
            (
                move_x,
                move_y,
                (svg_rx, svg_ry, x_rot, large_arc, sweep, end_x, end_y),
            ) = parsed

            sx = self._to_ki(str(move_x)) - self._bbox_x
            sy = self._to_ki(str(move_y)) - self._bbox_y
            ex = self._to_ki(str(end_x)) - self._bbox_x
            ey = self._to_ki(str(end_y)) - self._bbox_y
            arc_rx = self._to_ki(str(svg_rx))
            arc_ry = self._to_ki(str(svg_ry))

            if arc_ry == 0:
                return None

            center_x, center_y, extent = compute_arc(
                sx, sy, arc_rx, arc_ry, x_rot, large_arc, sweep, ex, ey
            )

            # LEGACY: Round to 2dp to match old pipeline serialization.
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

            return kicad.pcb.Arc(
                start=kicad.pcb.Xy(x=ex, y=ey),
                mid=kicad.pcb.Xy(x=mid.x, y=mid.y),
                end=kicad.pcb.Xy(x=end_pt.x, y=end_pt.y),
                solder_mask_margin=None,
                stroke=self._stroke(stroke_width),
                fill=None,
                layer=self._layer(layer_id),
                layers=[],
                locked=False,
                uuid=kicad.gen_uuid(),
            )
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse footprint arc: {e}")
            return None

    def _build_text(self, f: list[str]) -> kicad.pcb.FpText:
        text_type = get(f, 0)
        cx = to_mm(parse_float(get(f, 1)))
        cy = to_mm(parse_float(get(f, 2)))
        stroke_width = to_mm(parse_float(get(f, 3)))
        rotation = parse_float(get(f, 4))
        layer_id = parse_int(get(f, 6), default=1)
        font_size = to_mm(parse_float(get(f, 8)))
        text = get(f, 9)
        displayed = text_is_displayed(get(f, 11, "1"))
        visible = displayed and text_type != "N"

        layer = self._layer(layer_id)
        if not visible:
            layer = layer.replace(".SilkS", ".Fab")
        mirror = layer.startswith("B")
        justify = kicad.pcb.Justify(
            justify1=kicad.pcb.E_justify.LEFT,
            justify2=None,
            justify3=kicad.pcb.E_justify.MIRROR if mirror else None,
        )
        tx, ty = self._xy(cx, cy)
        return kicad.pcb.FpText(
            type=kicad.pcb.E_fp_text_type.USER,
            text=text,
            at=kicad.pcb.Xyr(
                x=tx,
                y=ty,
                r=angle_to_ki(rotation) or None,
            ),
            layer=kicad.pcb.TextLayer(layer=layer, knockout=None),
            hide=True if not visible else None,
            uuid=kicad.gen_uuid(),
            effects=_ki_effects(
                font=_ki_font(
                    size=kicad.pcb.Wh(
                        w=round(max(font_size, 1), 2),
                        h=round(max(font_size, 1), 2),
                    ),
                    thickness=round(max(stroke_width, MIN_STROKE_W), 2),
                ),
                justify=justify,
            ),
        )

    @staticmethod
    def _parse_3d_model(fields: list[str]) -> Ee3dModelInfo | None:
        """Parse SVGNODE 3D model metadata.

        Returns None when the model data is missing or malformed — this is
        expected, not an error.
        """
        if not fields:
            return None
        try:
            attrs = json.loads(fields[0])["attrs"]
        except (json.JSONDecodeError, KeyError, IndexError):
            return None

        origin = attrs.get("c_origin", "0,0").split(",")
        rotation = attrs.get("c_rotation", "0,0,0").split(",")

        return Ee3dModelInfo(
            name=attrs.get("title", ""),
            uuid=attrs.get("uuid", ""),
            translation_x=parse_float(get(origin, 0)),
            translation_y=parse_float(get(origin, 1)),
            translation_z=parse_float(attrs.get("z", "0")),
            rotation_x=parse_float(get(rotation, 0)),
            rotation_y=parse_float(get(rotation, 1)),
            rotation_z=parse_float(get(rotation, 2)),
        )

    def _convert_model(self, model_path: str) -> kicad.pcb.Model:
        m3d = self._model_3d
        assert m3d is not None
        # Convert translation to mm
        tx = to_mm(m3d.translation_x)
        ty = to_mm(m3d.translation_y)
        tz = to_mm(m3d.translation_z)

        offset_x = round(tx - self._bbox_x, 2)
        offset_y = -round(ty - self._bbox_y, 2)
        offset_z = -round(tz, 2) if self._is_smd else 0

        # LEGACY: SMD 3D model X/Y offset zeroed to match original
        # easyeda2kicad output.
        if self._is_smd or re.search(r"[cCrR]0201", self._name):
            offset_x = 0
            offset_y = 0

        rot_x = (360 - m3d.rotation_x) % 360
        rot_y = (360 - m3d.rotation_y) % 360
        rot_z = (360 - m3d.rotation_z) % 360

        return kicad.pcb.Model(
            path=f"{model_path}/{m3d.name}",
            offset=kicad.pcb.ModelXyz(
                xyz=kicad.pcb.Xyz(x=offset_x, y=offset_y, z=offset_z)
            ),
            scale=kicad.pcb.ModelXyz(xyz=kicad.pcb.Xyz(x=1, y=1, z=1)),
            rotate=kicad.pcb.ModelXyz(xyz=kicad.pcb.Xyz(x=rot_x, y=rot_y, z=rot_z)),
        )

    # ── build ────────────────────────────────────────────────────────────

    def build(self, model_path: str | None = None) -> kicad.footprint.FootprintFile:
        """Build a KiCad FootprintFile."""

        pads: list[kicad.pcb.Pad] = []
        lines: list[kicad.pcb.Line] = []
        circles: list[kicad.pcb.Circle] = []
        arcs: list[kicad.pcb.Arc] = []
        texts: list[kicad.pcb.FpText] = []

        for raw_line in self._shapes:
            designator, *fields = raw_line.split("~")
            match designator:
                case "PAD":
                    pads.append(self._build_pad(fields))
                case "TRACK":
                    lines.extend(self._build_track(fields))
                case "HOLE":
                    pads.append(self._build_hole(fields))
                case "CIRCLE":
                    circles.append(self._build_circle(fields))
                case "ARC":
                    if arc := self._build_arc(fields):
                        arcs.append(arc)
                case "RECT":
                    lines.extend(self._build_rect(fields))
                case "VIA":
                    pads.append(self._build_via(fields))
                case "TEXT":
                    texts.append(self._build_text(fields))
                case "SVGNODE":
                    pass  # already extracted in __init__
                case "SOLIDREGION":
                    pass
                case _:
                    logger.warning(f"Unknown footprint designator: {designator}")

        # Fab reference text (%R)
        texts.append(
            kicad.pcb.FpText(
                type=kicad.pcb.E_fp_text_type.USER,
                text="%R",
                at=kicad.pcb.Xyr(x=0, y=0, r=None),
                layer=kicad.pcb.TextLayer(layer="F.Fab", knockout=None),
                hide=None,
                uuid=kicad.gen_uuid(),
                effects=_ki_effects(
                    font=_ki_font(
                        size=kicad.pcb.Wh(w=1, h=1),
                        thickness=0.15,
                    ),
                ),
            )
        )

        # 3D Model
        models = []
        if self._model_3d is not None and model_path is not None:
            models.append(self._convert_model(model_path))

        # Properties
        y_low = min((p.at.y for p in pads), default=0)
        y_high = max((p.at.y for p in pads), default=0)

        fp_effects = _ki_effects(
            font=_ki_font(size=kicad.pcb.Wh(w=1, h=1), thickness=0.15),
        )

        properties = [
            kicad.pcb.Property(
                name="Reference",
                value="REF**",
                at=kicad.pcb.Xyr(x=0, y=round(y_low - 4, 2), r=None),
                unlocked=None,
                layer="F.SilkS",
                hide=None,
                uuid=kicad.gen_uuid(),
                effects=fp_effects,
            ),
            kicad.pcb.Property(
                name="Value",
                value=self._name,
                at=kicad.pcb.Xyr(x=0, y=round(y_high + 4, 2), r=None),
                unlocked=None,
                layer="F.Fab",
                hide=None,
                uuid=kicad.gen_uuid(),
                effects=fp_effects,
            ),
        ]

        return kicad.footprint.FootprintFile(
            footprint=kicad.footprint.Footprint(
                name=f"easyeda2kicad:{self._name}",
                uuid=kicad.gen_uuid(),
                path=None,
                layer="F.Cu",
                propertys=properties,
                attr=(["smd"] if self._is_smd else ["through_hole"]),
                fp_circles=circles,
                fp_lines=lines,
                fp_arcs=arcs,
                fp_rects=[],
                fp_poly=[],
                fp_texts=texts,
                pads=pads,
                models=models,
                embedded_fonts=None,
                version=20241229,
                generator="faebryk_convert",
                generator_version="v5",
                description=None,
                tags=[],
                tedit=None,
            )
        )


# ── Test fixtures ─────────────────────────────────────────────────────────────


def _resistor_cad_data() -> dict:
    """C21190 -- 0603 1k SMD resistor (2 pads, 2 tracks, 1 circle, 1 3D model)."""
    return {
        "packageDetail": {
            "title": "R0603",
            "dataStr": {
                "head": {
                    "c_para": {"package": "R0603"},
                    "x": 4000,
                    "y": 3000,
                },
                "shape": [
                    "CIRCLE~3996.85~3001.575~0.118~0.2362~101~gge1043~0~~",
                    "SOLIDREGION~100~~M 3996 3001 L 3996 2998 Z~solid~gge1000~~~~0",
                    "PAD~RECT~4002.966~3000~3.1751~3.4016~1~~2~0~4001.378 3001.7008 4001.378 2998.2992 4004.5531 2998.2992 4004.5531 3001.7008~0~gge1002~0~~Y~0~-393.7008~0.2000~4002.9655,3000",  # noqa: E501
                    "PAD~RECT~3997.034~3000~3.1751~3.4016~1~~1~0~3998.622 3001.7008 3998.622 2998.2992 3995.4469 2998.2992 3995.4469 3001.7008~0~gge1004~0~~Y~0~-393.7008~0.2000~3997.0345,3000",  # noqa: E501
                    "TRACK~0.6~3~~4001.678 3002.6008 4005.4531 3002.6008 4005.4531 2997.3992 4001.678 2997.3992~gge1006~0",  # noqa: E501
                    "TRACK~0.6~3~~3998.322 3002.6008 3994.5469 3002.6008 3994.5469 2997.3992 3998.322 2997.3992~gge1007~0",  # noqa: E501
                    (
                        'SVGNODE~{"gId":"g1_outline","nodeName":"g","nodeType":1,'
                        '"layerid":"19","attrs":{"c_width":"3.18897","c_height":"6.37794",'
                        '"c_rotation":"0,0,90","z":"0","c_origin":"4000,3000",'
                        '"uuid":"6bd5cd867e9542ebae21caaf5d2d4c4d","c_etype":"outline3D",'
                        '"id":"g1_outline","title":"R0603","layerid":"19",'
                        '"transform":"scale(1) translate(0, 0)"},"childNodes":[]}'
                    ),
                ],
            },
        },
        "SMT": True,
        "dataStr": {
            "head": {
                "c_para": {
                    "pre": "R?",
                    "name": "0603WAF1001T5E",
                    "package": "R0603",
                    "Manufacturer": "UNI-ROYAL",
                    "Supplier Part": "C21190",
                    "JLCPCB Part Class": "Basic Part",
                },
                "x": 20,
                "y": 0,
            },
            "shape": [
                "P~show~1~2~40~0~0~rep2~0^^40~0^^M 40 -0 h-10~#000000^^0~25~3~0~2~end~~~#000000^^0~35~-1~0~2~start~~~#000000^^0~33~0^^0~M 30 -3 L 27 0 L 30 3",  # noqa: E501
                "P~show~1~1~0~0~180~rep3~0^^0~0^^M 0 -0 h10~#000000^^0~15~3~0~1~start~~~#000000^^0~5~-1~0~1~end~~~#000000^^0~7~0^^0~M 10 3 L 13 0 L 10 -3",  # noqa: E501
                "R~10~-4~~~20~8~#880000~1~0~none~rep4~0",
            ],
        },
        "lcsc": {
            "number": "C21190",
            "url": "https://lcsc.com/product-detail/C21190.html",
        },
    }


def _opamp_cad_data() -> dict:
    """C7950 -- LM358 opamp (8 pins, ellipses + rectangle in symbol, arcs in FP)."""
    return {
        "packageDetail": {
            "title": "SOIC-8_L5.0-W4.0-P1.27-LS6.0-BL",
            "dataStr": {
                "head": {
                    "c_para": {"package": "SOIC-8_L5.0-W4.0-P1.27-LS6.0-BL"},
                    "x": 4000,
                    "y": 3000,
                },
                "shape": [
                    "PAD~RECT~3993.5~3003.5~2.3622~4.9213~1~~1~0~~0~gge1001~0~~Y~0~0~0.2~3993.5,3003.5",
                    "PAD~RECT~3993.5~3001~2.3622~4.9213~1~~2~0~~0~gge1002~0~~Y~0~0~0.2~3993.5,3001",
                    "ARC~1~3~~M3990.1575,3002.8605 A2.8648,2.8648 0 0 0 3990.1768,2997.1406~~gge1125~0",  # noqa: E501
                    "TRACK~0.6~3~~3993 3005 3997 3005~gge2001~0",
                    'SVGNODE~{"gId":"g1","nodeName":"g","nodeType":1,"layerid":"19","attrs":{"c_width":"5","c_height":"4","c_rotation":"0,0,0","z":"0","c_origin":"4000,3000","uuid":"abc123","c_etype":"outline3D","title":"SOIC-8","layerid":"19"},"childNodes":[]}',
                ],
            },
        },
        "SMT": True,
        "dataStr": {
            "head": {
                "c_para": {
                    "pre": "U?",
                    "name": "LM358DR2G",
                    "package": "SOIC-8_L5.0-W4.0-P1.27-LS6.0-BL",
                    "Manufacturer": "onsemi",
                    "Supplier Part": "C7950",
                    "BOM_Manufacturer": "onsemi",
                    "JLCPCB Part Class": "Basic Part",
                },
                "x": 400,
                "y": 305,
            },
            "shape": [
                "E~365~283~1.5~1.5~#880000~1~0~#880000~gge14~0",
                "R~360~278~2~2~80~54~#880000~1~0~none~gge16~0~",
                "P~show~0~1~350~290~180~gge18~0^^350~290^^M 350 290 h 10~#880000^^1~363.7~294~0~1OUT~start~~~#0000FF^^1~359.5~289~0~1~end~~~#0000FF^^0~357~290^^0~M 360 293 L 363 290 L 360 287",  # noqa: E501
                "P~show~0~2~350~300~180~gge25~0^^350~300^^M 350 300 h 10~#880000^^1~363.7~304~0~1IN-~start~~~#0000FF^^1~359.5~299~0~2~end~~~#0000FF^^0~357~300^^0~M 360 303 L 363 300 L 360 297",  # noqa: E501
                "P~show~0~3~350~310~180~gge32~0^^350~310^^M 350 310 h 10~#880000^^1~363.7~314~0~1IN+~start~~~#0000FF^^1~359.5~309~0~3~end~~~#0000FF^^0~357~310^^0~M 360 313 L 363 310 L 360 307",  # noqa: E501
                "P~show~0~4~350~320~180~gge39~0^^350~320^^M 350 320 h 10~#000000^^1~363.7~324~0~GND~start~~~#000000^^1~359.5~319~0~4~end~~~#000000^^0~357~320^^0~M 360 323 L 363 320 L 360 317",  # noqa: E501
                "P~show~0~5~450~320~0~gge46~0^^450~320^^M 450 320 h -10~#880000^^1~436.3~324~0~2IN+~end~~~#0000FF^^1~440.5~319~0~5~start~~~#0000FF^^0~443~320^^0~M 440 317 L 437 320 L 440 323",  # noqa: E501
                "P~show~0~6~450~310~0~gge53~0^^450~310^^M 450 310 h -10~#880000^^1~436.3~314~0~2IN-~end~~~#0000FF^^1~440.5~309~0~6~start~~~#0000FF^^0~443~310^^0~M 440 307 L 437 310 L 440 313",  # noqa: E501
                "P~show~0~7~450~300~0~gge60~0^^450~300^^M 450 300 h -10~#880000^^1~436.3~304~0~2OUT~end~~~#0000FF^^1~440.5~299~0~7~start~~~#0000FF^^0~443~300^^0~M 440 297 L 437 300 L 440 303",  # noqa: E501
                "P~show~0~8~450~290~0~gge67~0^^450~290^^M 450 290 h -10~#FF0000^^1~436.3~294~0~VCC~end~~~#FF0000^^1~440.5~289~0~8~start~~~#FF0000^^0~443~290^^0~M 440 287 L 437 290 L 440 293",  # noqa: E501
            ],
        },
        "lcsc": {
            "number": "C7950",
            "url": "https://lcsc.com/product-detail/C7950.html",
        },
    }


def _tht_cad_data() -> dict:
    """C46749 -- DIP-8 THT package (8 pads with holes)."""
    return {
        "packageDetail": {
            "title": "DIP-8_L9.8-W6.6-P2.54-LS7.6-BL",
            "dataStr": {
                "head": {
                    "c_para": {"package": "DIP-8_L9.8-W6.6-P2.54-LS7.6-BL"},
                    "x": 3942,
                    "y": 2966,
                },
                "shape": [
                    "PAD~RECT~3927.5~2981~5.9055~5.9055~11~~1~1.7717~3924.5472 2978.0472 3930.4528 2978.0472 3930.4528 2983.9528 3924.5472 2983.9528~0~rep12~0~~Y~0~0~0.2~3927.5,2981",  # noqa: E501
                    "PAD~ELLIPSE~3937.5~2981~5.9055~5.9055~11~~2~1.7717~~90~rep11~0~~Y~0~0~0.2~3937.5,2981",
                    "PAD~ELLIPSE~3947.5~2981~5.9055~5.9055~11~~3~1.7717~~90~rep10~0~~Y~0~0~0.2~3947.5,2981",
                    "PAD~ELLIPSE~3957.5~2981~5.9055~5.9055~11~~4~1.7717~~90~rep9~0~~Y~0~0~0.2~3957.5,2981",
                    "PAD~ELLIPSE~3927.5~2951~5.9055~5.9055~11~~8~1.7717~~90~rep8~0~~Y~0~0~0.2~3927.5,2951",
                    "PAD~ELLIPSE~3937.5~2951~5.9055~5.9055~11~~7~1.7717~~90~rep7~0~~Y~0~0~0.2~3937.5,2951",
                    "PAD~ELLIPSE~3947.5~2951~5.9055~5.9055~11~~6~1.7717~~90~rep6~0~~Y~0~0~0.2~3947.5,2951",
                    "PAD~ELLIPSE~3957.5~2951~5.9055~5.9055~11~~5~1.7717~~90~rep5~0~~Y~0~0~0.2~3957.5,2951",
                    "HOLE~3925~2966~1.5748~gge1034~0",
                    "TRACK~0.6~3~~3920.6693 2983.622 3920.6693 2948.378~gge1006~0",
                ],
            },
        },
        "SMT": False,
        "dataStr": {
            "head": {
                "c_para": {
                    "pre": "U?",
                    "name": "NE555P",
                    "package": "DIP-8_L9.8-W6.6-P2.54-LS7.6-BL",
                    "Manufacturer": "TI",
                    "Supplier Part": "C46749",
                    "BOM_Manufacturer": "TI",
                    "JLCPCB Part Class": "Extended Part",
                },
                "x": 400,
                "y": 305,
            },
            "shape": [
                "P~show~0~1~350~290~180~gge18~0^^350~290^^M 350 290 h 10~#880000^^1~363~294~0~GND~start~~~#0000FF^^1~359~289~0~1~end~~~#0000FF^^0~357~290^^0~M 360 293 L 363 290 L 360 287",  # noqa: E501
                "P~show~0~2~350~300~180~gge25~0^^350~300^^M 350 300 h 10~#880000^^1~363~304~0~TRIG~start~~~#0000FF^^1~359~299~0~2~end~~~#0000FF^^0~357~300^^0~M 360 303 L 363 300 L 360 297",  # noqa: E501
                "R~360~278~2~2~80~54~#880000~1~0~none~gge16~0~",
            ],
        },
        "lcsc": {
            "number": "C46749",
            "url": "https://lcsc.com/product-detail/C46749.html",
        },
    }


def _make_fp_data(
    *,
    shapes: list[str],
    name: str = "TEST",
    is_smd: bool = True,
    bbox_x: float = 0,
    bbox_y: float = 0,
) -> dict:
    """Minimal cad_data dict for edge-case footprint tests."""
    return {
        "packageDetail": {
            "title": name,
            "dataStr": {
                "head": {"c_para": {"package": name}, "x": bbox_x, "y": bbox_y},
                "shape": shapes,
            },
        },
        "SMT": is_smd,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

import pytest  # noqa: E402


def test_build_fp_resistor_structure():
    result = FootprintBuilder(_resistor_cad_data()).build()
    assert isinstance(result, kicad.footprint.FootprintFile)
    assert result.footprint.name == "easyeda2kicad:R0603"


def test_build_fp_resistor_attr_smd():
    result = FootprintBuilder(_resistor_cad_data()).build()
    assert "smd" in result.footprint.attr


def test_build_fp_resistor_pads():
    result = FootprintBuilder(_resistor_cad_data()).build()
    assert len(result.footprint.pads) == 2
    for pad in result.footprint.pads:
        assert pad.type == kicad.pcb.E_pad_type.SMD
        assert pad.shape == kicad.pcb.E_pad_shape.RECT
        assert pad.drill is None


def test_build_fp_resistor_pad_positions_are_relative():
    result = FootprintBuilder(_resistor_cad_data()).build()
    for pad in result.footprint.pads:
        assert abs(pad.at.x) < 10
        assert abs(pad.at.y) < 10


def test_build_fp_resistor_lines():
    result = FootprintBuilder(_resistor_cad_data()).build()
    assert len(result.footprint.fp_lines) >= 4


def test_build_fp_resistor_circles():
    result = FootprintBuilder(_resistor_cad_data()).build()
    assert len(result.footprint.fp_circles) == 1


def test_build_fp_resistor_properties():
    result = FootprintBuilder(_resistor_cad_data()).build()
    props = result.footprint.propertys
    assert len(props) == 2
    ref = next(p for p in props if p.name == "Reference")
    val = next(p for p in props if p.name == "Value")
    assert ref.value == "REF**"
    assert val.value == "R0603"


def test_build_fp_resistor_3d_model():
    builder = FootprintBuilder(_resistor_cad_data())
    assert builder.model_3d is not None
    assert builder.model_3d.name == "R0603"
    assert builder.model_3d.uuid == "6bd5cd867e9542ebae21caaf5d2d4c4d"
    assert builder.model_3d.rotation_z == 90

    result = builder.build(model_path="/models")
    assert len(result.footprint.models) == 1
    assert result.footprint.models[0].path == "/models/R0603"


def test_build_fp_3d_model_origin():
    builder = FootprintBuilder(_resistor_cad_data())
    assert builder.model_3d is not None
    assert builder.model_3d.translation_x == 4000
    assert builder.model_3d.translation_y == 3000


def test_build_fp_smd_3d_model_offset_workaround():
    result = FootprintBuilder(_resistor_cad_data()).build(model_path="/models")
    model = result.footprint.models[0]
    assert model.offset.xyz.x == 0
    assert model.offset.xyz.y == 0


def test_build_fp_no_model_without_path():
    result = FootprintBuilder(_resistor_cad_data()).build()
    assert len(result.footprint.models) == 0


def test_build_fp_tht_attr():
    result = FootprintBuilder(_tht_cad_data()).build()
    assert "through_hole" in result.footprint.attr


def test_build_fp_tht_pads_have_drill():
    result = FootprintBuilder(_tht_cad_data()).build()
    tht_pads = [
        p for p in result.footprint.pads if p.type == kicad.pcb.E_pad_type.THRU_HOLE
    ]
    # 8 signal pads + 1 hole (also thru_hole per old behavior)
    assert len(tht_pads) == 9
    for pad in tht_pads:
        assert pad.drill is not None
        assert pad.drill.size_x is not None and pad.drill.size_x > 0


def test_build_fp_tht_pad_layers():
    result = FootprintBuilder(_tht_cad_data()).build()
    for pad in result.footprint.pads:
        if pad.type == kicad.pcb.E_pad_type.THRU_HOLE:
            assert "*.Cu" in pad.layers
            assert "*.Mask" in pad.layers


def test_build_fp_opamp_arc():
    result = FootprintBuilder(_opamp_cad_data()).build()
    assert len(result.footprint.fp_arcs) == 1
    arc = result.footprint.fp_arcs[0]
    assert arc.start is not None
    assert arc.mid is not None
    assert arc.end is not None


def test_build_fp_version_and_generator():
    result = FootprintBuilder(_resistor_cad_data()).build()
    assert result.footprint.version == 20241229
    assert result.footprint.generator == "faebryk_convert"


def test_build_fp_empty_shapes():
    data = _make_fp_data(shapes=[], name="EMPTY")
    result = FootprintBuilder(data).build()
    assert result.footprint.name == "easyeda2kicad:EMPTY"
    assert len(result.footprint.pads) == 0


def test_build_fp_no_3d_model():
    data = _make_fp_data(
        shapes=["PAD~RECT~100~100~10~10~1~~1~0~~0~id1~0~~1~0"],
    )
    builder = FootprintBuilder(data)
    assert builder.model_3d is None


def test_build_fp_solidregion_skipped():
    result = FootprintBuilder(_resistor_cad_data()).build()
    # SOLIDREGION is in the fixture but should produce no shapes
    # (only pads + circle + tracks + text appear)
    assert result.footprint.fp_arcs == []
    assert result.footprint.fp_rects == []


# ── Edge cases ───────────────────────────────────────────────────────────────


def test_pad_number_with_parentheses():
    data = _make_fp_data(
        shapes=["PAD~RECT~0~0~3.937~3.937~1~~A(1)~0~~0~id1~0~~1~0"],
    )
    result = FootprintBuilder(data).build()
    assert result.footprint.pads[0].name == "1"


def test_polygon_pad():
    data = _make_fp_data(
        shapes=[
            "PAD~POLYGON~1.969~1.969~3.937~3.937~1~~1~0~0 0 100 0 100 100 0 100~0~id1~0~~1~0",
        ],
    )
    result = FootprintBuilder(data).build()
    pad = result.footprint.pads[0]
    assert pad.shape == kicad.pcb.E_pad_shape.CUSTOM
    assert pad.primitives is not None


def test_rectangle_to_lines():
    data = _make_fp_data(
        shapes=[
            # RECT: pos_x~pos_y~width~height~layer_id~id~is_locked~stroke_width
            "RECT~3.937~3.937~7.874~11.811~3~id1~0~0.394",
        ],
    )
    result = FootprintBuilder(data).build()
    assert len(result.footprint.fp_lines) == 4


def test_hole_to_thru_hole():
    data = _make_fp_data(
        shapes=["HOLE~100~100~11.811~h1~0"],
        is_smd=False,
    )
    result = FootprintBuilder(data).build()
    assert len(result.footprint.pads) == 1
    pad = result.footprint.pads[0]
    assert pad.type == kicad.pcb.E_pad_type.THRU_HOLE
    assert pad.name == ""
    assert pad.drill is not None
    assert pad.drill.size_x == pytest.approx(to_mm(11.811) * 2, abs=0.01)


def test_oval_drill():
    # PAD with hole_radius and hole_length (fields 8 and 12)
    data = _make_fp_data(
        shapes=[
            "PAD~ELLIPSE~100~100~23.228~23.228~11~~1~6.980~~90~id1~3.937~~1~0",
        ],
        is_smd=False,
    )
    result = FootprintBuilder(data).build()
    pad = result.footprint.pads[0]
    assert pad.drill is not None
    assert pad.drill.shape == kicad.pcb.E_pad_drill_shape.OVAL


# ── KiCad serialization round-trip ───────────────────────────────────────────


def test_kicad_fp_dumps():
    result = FootprintBuilder(_resistor_cad_data()).build()
    text = kicad.dumps(result)
    assert text.startswith("(footprint")
    assert "easyeda2kicad:R0603" in text
    assert "REF**" in text


def test_kicad_tht_fp_dumps():
    result = FootprintBuilder(_tht_cad_data()).build()
    text = kicad.dumps(result)
    assert "thru_hole" in text
    assert "(drill" in text


def test_kicad_opamp_fp_dumps():
    result = FootprintBuilder(_opamp_cad_data()).build()
    text = kicad.dumps(result)
    assert "(arc" in text.lower() or "(fp_arc" in text.lower()
