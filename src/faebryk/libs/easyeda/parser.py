# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""Parse EasyEDA tilde-delimited CAD data into typed dataclasses."""

import json
import logging

from faebryk.libs.easyeda.easyeda_types import (
    Ee3dModelInfo,
    EeFootprint,
    EeFpArc,
    EeFpCircle,
    EeFpHole,
    EeFpPad,
    EeFpRect,
    EeFpText,
    EeFpTrack,
    EeFpVia,
    EeSymArc,
    EeSymbol,
    EeSymbolInfo,
    EeSymbolUnit,
    EeSymCircle,
    EeSymEllipse,
    EeSymPath,
    EeSymPin,
    EeSymPolyline,
    EeSymRect,
    _to_mm,
)

logger = logging.getLogger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────


def _get(f: list[str], idx: int, default: str = "") -> str:
    """Safe index into a tilde-split field list."""
    return f[idx] if idx < len(f) else default


def _bool_field(val: str) -> bool:
    if not val:
        return False
    if val == "show":
        return True
    try:
        return bool(float(val))
    except (ValueError, TypeError):
        return bool(val)


def _float(val: str, default: float = 0.0) -> float:
    if not val:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _int(val: str, default: int = 0) -> int:
    if not val:
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _text_is_displayed(val: str) -> bool:
    """Match old Pydantic validator: empty string → True, otherwise parse as bool."""
    if val == "":
        return True
    return _bool_field(val)


def _has_fill(f: list[str], idx: int) -> bool:
    raw = _get(f, idx)
    return bool(raw and raw.lower() != "none")


# ── Footprint parser ─────────────────────────────────────────────────────────


def parse_footprint(cad_data: dict) -> EeFootprint:
    """Parse raw EasyEDA API response into an EeFootprint."""
    pkg = cad_data["packageDetail"]
    ee_data_str = pkg["dataStr"]
    ee_data_info = ee_data_str["head"]["c_para"]

    is_smd = cad_data.get("SMT") and "-TH_" not in pkg.get("title", "")

    bbox_x = _to_mm(float(ee_data_str["head"]["x"]))
    bbox_y = _to_mm(float(ee_data_str["head"]["y"]))

    fp = EeFootprint(
        name=ee_data_info["package"],
        fp_type="smd" if is_smd else "tht",
        bbox_x=bbox_x,
        bbox_y=bbox_y,
    )

    for line in ee_data_str["shape"]:
        designator = line.split("~")[0]
        fields = line.split("~")[1:]

        if designator == "PAD":
            fp.pads.append(_parse_pad(fields))
        elif designator == "TRACK":
            fp.tracks.append(_parse_track(fields))
        elif designator == "HOLE":
            fp.holes.append(_parse_hole(fields))
        elif designator == "CIRCLE":
            fp.circles.append(_parse_circle(fields))
        elif designator == "ARC":
            fp.arcs.append(_parse_arc(fields))
        elif designator == "RECT":
            fp.rects.append(_parse_rect(fields))
        elif designator == "VIA":
            fp.vias.append(_parse_via(fields))
        elif designator == "TEXT":
            fp.texts.append(_parse_text(fields))
        elif designator == "SVGNODE":
            fp.model_3d = _parse_3d_model(fields)
        elif designator == "SOLIDREGION":
            pass  # skip
        else:
            logger.warning(f"Unknown footprint designator: {designator}")

    return fp


def _parse_pad(f: list[str]) -> EeFpPad:
    return EeFpPad(
        shape=_get(f, 0),
        center_x=_to_mm(_float(_get(f, 1))),
        center_y=_to_mm(_float(_get(f, 2))),
        width=_to_mm(_float(_get(f, 3))),
        height=_to_mm(_float(_get(f, 4))),
        layer_id=_int(_get(f, 5), default=1),
        net=_get(f, 6),
        number=_get(f, 7),
        hole_radius=_to_mm(_float(_get(f, 8))),
        points=_get(f, 9),
        rotation=_float(_get(f, 10)),
        id=_get(f, 11),
        hole_length=_to_mm(_float(_get(f, 12))),
        hole_point=_get(f, 13),
        is_plated=_bool_field(_get(f, 14, "1")),
        is_locked=_bool_field(_get(f, 15)),
    )


def _parse_track(f: list[str]) -> EeFpTrack:
    return EeFpTrack(
        stroke_width=_to_mm(_float(_get(f, 0))),
        layer_id=_int(_get(f, 1), default=1),
        net=_get(f, 2),
        points=_get(f, 3),
        id=_get(f, 4),
        is_locked=_bool_field(_get(f, 5)),
    )


def _parse_hole(f: list[str]) -> EeFpHole:
    return EeFpHole(
        center_x=_to_mm(_float(_get(f, 0))),
        center_y=_to_mm(_float(_get(f, 1))),
        radius=_to_mm(_float(_get(f, 2))),
        id=_get(f, 3),
        is_locked=_bool_field(_get(f, 4)),
    )


def _parse_circle(f: list[str]) -> EeFpCircle:
    return EeFpCircle(
        cx=_to_mm(_float(_get(f, 0))),
        cy=_to_mm(_float(_get(f, 1))),
        radius=_to_mm(_float(_get(f, 2))),
        stroke_width=_to_mm(_float(_get(f, 3))),
        layer_id=_int(_get(f, 4), default=1),
        id=_get(f, 5),
        is_locked=_bool_field(_get(f, 6)),
    )


def _parse_arc(f: list[str]) -> EeFpArc:
    return EeFpArc(
        stroke_width=_float(_get(f, 0)),
        layer_id=_int(_get(f, 1), default=1),
        net=_get(f, 2),
        path=_get(f, 3),
        helper_dots=_get(f, 4),
        id=_get(f, 5),
        is_locked=_bool_field(_get(f, 6)),
    )


def _parse_rect(f: list[str]) -> EeFpRect:
    return EeFpRect(
        x=_to_mm(_float(_get(f, 0))),
        y=_to_mm(_float(_get(f, 1))),
        width=_to_mm(_float(_get(f, 2))),
        height=_to_mm(_float(_get(f, 3))),
        layer_id=_int(_get(f, 4), default=1),
        id=_get(f, 5),
        is_locked=_bool_field(_get(f, 6)),
        stroke_width=_to_mm(_float(_get(f, 7))),
    )


def _parse_via(f: list[str]) -> EeFpVia:
    return EeFpVia(
        center_x=_to_mm(_float(_get(f, 0))),
        center_y=_to_mm(_float(_get(f, 1))),
        diameter=_to_mm(_float(_get(f, 2))),
        net=_get(f, 3),
        radius=_to_mm(_float(_get(f, 4))),
        id=_get(f, 5),
        is_locked=_bool_field(_get(f, 6)),
    )


def _parse_text(f: list[str]) -> EeFpText:
    return EeFpText(
        type=_get(f, 0),
        center_x=_to_mm(_float(_get(f, 1))),
        center_y=_to_mm(_float(_get(f, 2))),
        stroke_width=_to_mm(_float(_get(f, 3))),
        rotation=_float(_get(f, 4)),
        mirror=_get(f, 5),
        layer_id=_int(_get(f, 6), default=1),
        net=_get(f, 7),
        font_size=_to_mm(_float(_get(f, 8))),
        text=_get(f, 9),
        text_path=_get(f, 10),
        is_displayed=_text_is_displayed(_get(f, 11, "1")),
        id=_get(f, 12),
        is_locked=_bool_field(_get(f, 13)),
    )


def _parse_3d_model(fields: list[str]) -> Ee3dModelInfo | None:
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
        translation_x=_float(_get(origin, 0)),
        translation_y=_float(_get(origin, 1)),
        translation_z=_float(attrs.get("z", "0")),
        rotation_x=_float(_get(rotation, 0)),
        rotation_y=_float(_get(rotation, 1)),
        rotation_z=_float(_get(rotation, 2)),
    )


# ── Symbol parser ────────────────────────────────────────────────────────────


def parse_symbol(cad_data: dict) -> EeSymbol:
    """Parse raw EasyEDA API response into an EeSymbol."""
    ee_data_info = cad_data["dataStr"]["head"]["c_para"]

    sym = EeSymbol(
        info=EeSymbolInfo(
            name=ee_data_info["name"],
            prefix=ee_data_info["pre"],
            package=ee_data_info.get("package", None),
            manufacturer=ee_data_info.get("BOM_Manufacturer", None),
            datasheet=cad_data["lcsc"].get("url", None),
            lcsc_id=cad_data["lcsc"].get("number", None),
            jlc_id=ee_data_info.get("BOM_JLCPCB Part Class", None),
        ),
    )

    bbox_x = float(cad_data["dataStr"]["head"]["x"])
    bbox_y = float(cad_data["dataStr"]["head"]["y"])

    if cad_data.get("subparts"):
        for unit_data in cad_data["subparts"]:
            unit = EeSymbolUnit(bbox_x=bbox_x, bbox_y=bbox_y)
            _parse_symbol_shapes(unit_data["dataStr"]["shape"], unit)
            sym.units.append(unit)
    else:
        unit = EeSymbolUnit(bbox_x=bbox_x, bbox_y=bbox_y)
        _parse_symbol_shapes(cad_data["dataStr"]["shape"], unit)
        sym.units.append(unit)

    return sym


def _parse_symbol_shapes(shapes: list[str], unit: EeSymbolUnit) -> None:
    for line in shapes:
        designator = line.split("~")[0]

        if designator == "P":
            pin = _parse_sym_pin(line, unit.bbox_x, unit.bbox_y)
            if pin:
                unit.pins.append(pin)
        elif designator == "R":
            unit.rectangles.append(_parse_sym_rect(line))
        elif designator == "C":
            unit.circles.append(_parse_sym_circle(line))
        elif designator == "E":
            unit.ellipses.append(_parse_sym_ellipse(line))
        elif designator == "A":
            unit.arcs.append(_parse_sym_arc(line))
        elif designator == "PL":
            unit.polylines.append(_parse_sym_polyline(line, is_polygon=False))
        elif designator == "PG":
            unit.polylines.append(_parse_sym_polyline(line, is_polygon=True))
        elif designator == "PT":
            unit.paths.append(_parse_sym_path(line))
        elif designator == "T":
            pass  # text, not implemented
        else:
            logger.warning(f"Unknown symbol designator: {designator}")


def _parse_sym_pin(line: str, bbox_x: float, bbox_y: float) -> EeSymPin | None:
    segments = line.split("^^")
    if len(segments) < 7:
        return None

    settings = segments[0].split("~")[1:]  # skip "P" designator
    if len(settings) < 7:
        return None

    # Pin path segment (index 2) contains the path like "M -5 3 L -2 0 L -5 -3"
    # which is used for pin shape (the "h" path gives length)
    pin_path_seg = segments[2].split("~")
    path_str = pin_path_seg[0] if pin_path_seg else ""
    # easyeda replaces 'v' with 'h' in the path
    path_str = path_str.replace("v", "h")

    # Extract pin length from path
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
    has_dot = _bool_field(dot_seg[0]) if dot_seg else False

    # Clock segment (index 6)
    clock_seg = segments[6].split("~")
    has_clock = _bool_field(clock_seg[0]) if clock_seg else False

    # Pin number from spice_pin_number (settings[2])
    number = settings[2].replace(" ", "") if len(settings) > 2 else ""

    # Pin type
    pin_type_raw = settings[1] if len(settings) > 1 else "0"
    pin_type = _int(pin_type_raw)
    if pin_type not in (0, 1, 2, 3, 4):
        pin_type = 0

    return EeSymPin(
        name=pin_name,
        number=number,
        pos_x=_float(settings[3]),
        pos_y=_float(settings[4]),
        rotation=_int(settings[5]),
        pin_type=pin_type,
        has_dot=has_dot,
        has_clock=has_clock,
        length=pin_length,
    )


def _parse_sym_rect(line: str) -> EeSymRect:
    f = line.split("~")[1:]
    return EeSymRect(
        pos_x=_float(_get(f, 0)),
        pos_y=_float(_get(f, 1)),
        width=_float(_get(f, 4)),
        height=_float(_get(f, 5)),
    )


def _parse_sym_circle(line: str) -> EeSymCircle:
    f = line.split("~")[1:]
    return EeSymCircle(
        center_x=_float(_get(f, 0)),
        center_y=_float(_get(f, 1)),
        radius=_float(_get(f, 2)),
        fill=_has_fill(f, 5),
    )


def _parse_sym_ellipse(line: str) -> EeSymEllipse:
    f = line.split("~")[1:]
    return EeSymEllipse(
        center_x=_float(_get(f, 0)),
        center_y=_float(_get(f, 1)),
        radius_x=_float(_get(f, 2)),
        radius_y=_float(_get(f, 3)),
        fill=_has_fill(f, 6),
    )


def _parse_sym_arc(line: str) -> EeSymArc:
    f = line.split("~")[1:]
    return EeSymArc(path=_get(f, 0), fill=_has_fill(f, 5))


def _parse_sym_polyline(line: str, is_polygon: bool) -> EeSymPolyline:
    f = line.split("~")[1:]
    return EeSymPolyline(points=_get(f, 0), fill=_has_fill(f, 4), is_polygon=is_polygon)


def _parse_sym_path(line: str) -> EeSymPath:
    f = line.split("~")[1:]
    return EeSymPath(paths=_get(f, 0), fill=_has_fill(f, 4))


# ── Test fixtures ─────────────────────────────────────────────────────────────


def _resistor_cad_data() -> dict:
    """C21190 — 0603 1kΩ SMD resistor (2 pads, 2 tracks, 1 circle, 1 3D model)."""
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
    """C7950 — LM358 opamp (8 pins, ellipses + rectangle in symbol, arcs in FP)."""
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
    """C46749 — DIP-8 THT package (8 pads with holes)."""
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


# ── Tests ─────────────────────────────────────────────────────────────────────

import pytest  # noqa: E402


def test_bool_field():
    assert _bool_field("") is False
    assert _bool_field("show") is True
    assert _bool_field("1") is True
    assert _bool_field("0") is False
    assert _bool_field("Y") is True


def test_float_helper():
    assert _float("3.14") == pytest.approx(3.14)
    assert _float("") == 0.0
    assert _float("", default=5.0) == 5.0
    assert _float("invalid") == 0.0


def test_int_helper():
    assert _int("42") == 42
    assert _int("3.7") == 3
    assert _int("") == 0
    assert _int("invalid") == 0


def test_parse_fp_resistor_basic_structure():
    fp = parse_footprint(_resistor_cad_data())
    assert fp.name == "R0603"
    assert fp.fp_type == "smd"
    assert fp.bbox_x == pytest.approx(_to_mm(4000), abs=0.01)
    assert fp.bbox_y == pytest.approx(_to_mm(3000), abs=0.01)


def test_parse_fp_resistor_pad_count():
    fp = parse_footprint(_resistor_cad_data())
    assert len(fp.pads) == 2


def test_parse_fp_resistor_pad_properties():
    fp = parse_footprint(_resistor_cad_data())
    pad1 = next(p for p in fp.pads if p.number == "1")
    pad2 = next(p for p in fp.pads if p.number == "2")
    assert pad1.shape == "RECT"
    assert pad2.shape == "RECT"
    assert pad1.layer_id == 1
    assert pad1.hole_radius == 0
    assert pad2.hole_radius == 0


def test_parse_fp_resistor_tracks():
    fp = parse_footprint(_resistor_cad_data())
    assert len(fp.tracks) == 2
    assert fp.tracks[0].stroke_width == pytest.approx(_to_mm(0.6), abs=0.01)
    assert fp.tracks[0].layer_id == 3


def test_parse_fp_resistor_circle():
    fp = parse_footprint(_resistor_cad_data())
    assert len(fp.circles) == 1


def test_parse_fp_resistor_3d_model():
    fp = parse_footprint(_resistor_cad_data())
    assert fp.model_3d is not None
    assert fp.model_3d.name == "R0603"
    assert fp.model_3d.uuid == "6bd5cd867e9542ebae21caaf5d2d4c4d"
    assert fp.model_3d.rotation_z == 90


def test_parse_fp_3d_model_origin():
    fp = parse_footprint(_resistor_cad_data())
    assert fp.model_3d.translation_x == 4000
    assert fp.model_3d.translation_y == 3000


def test_parse_fp_solidregion_skipped():
    fp = parse_footprint(_resistor_cad_data())
    assert len(fp.holes) == 0
    assert len(fp.arcs) == 0
    assert len(fp.rects) == 0


def test_parse_fp_tht_pads():
    fp = parse_footprint(_tht_cad_data())
    assert fp.fp_type == "tht"
    assert len(fp.pads) == 8
    for pad in fp.pads:
        assert pad.hole_radius > 0, f"THT pad {pad.number} should have hole"


def test_parse_fp_tht_hole():
    fp = parse_footprint(_tht_cad_data())
    assert len(fp.holes) == 1
    assert fp.holes[0].radius > 0


def test_parse_fp_opamp_arc():
    fp = parse_footprint(_opamp_cad_data())
    assert len(fp.arcs) == 1
    assert "A" in fp.arcs[0].path
    assert "M" in fp.arcs[0].path


def test_parse_fp_empty_shapes():
    data = {
        "packageDetail": {
            "title": "EMPTY",
            "dataStr": {
                "head": {"c_para": {"package": "EMPTY"}, "x": 0, "y": 0},
                "shape": [],
            },
        },
        "SMT": True,
    }
    fp = parse_footprint(data)
    assert fp.name == "EMPTY"
    assert len(fp.pads) == 0
    assert len(fp.tracks) == 0


def test_parse_fp_no_3d_model():
    data = {
        "packageDetail": {
            "title": "NOMODEL",
            "dataStr": {
                "head": {"c_para": {"package": "NOMODEL"}, "x": 0, "y": 0},
                "shape": [
                    "PAD~RECT~100~100~10~10~1~~1~0~~0~id1~0~~Y~0~0~0.2~100,100",
                ],
            },
        },
        "SMT": True,
    }
    fp = parse_footprint(data)
    assert fp.model_3d is None


def test_parse_sym_resistor_structure():
    sym = parse_symbol(_resistor_cad_data())
    assert sym.info.name == "0603WAF1001T5E"
    assert sym.info.prefix == "R?"
    assert sym.info.package == "R0603"
    assert sym.info.lcsc_id == "C21190"


def test_parse_sym_resistor_pins():
    sym = parse_symbol(_resistor_cad_data())
    assert len(sym.units) == 1
    unit = sym.units[0]
    assert len(unit.pins) == 2
    assert {p.number for p in unit.pins} == {"1", "2"}


def test_parse_sym_resistor_rectangle():
    sym = parse_symbol(_resistor_cad_data())
    unit = sym.units[0]
    assert len(unit.rectangles) == 1
    assert unit.rectangles[0].width == 20
    assert unit.rectangles[0].height == 8


def test_parse_sym_opamp_pins():
    sym = parse_symbol(_opamp_cad_data())
    unit = sym.units[0]
    assert len(unit.pins) == 8
    pin_names = {p.name for p in unit.pins}
    assert "1OUT" in pin_names
    assert "VCC" in pin_names
    assert "GND" in pin_names
    assert "1IN+" in pin_names
    assert "2OUT" in pin_names


def test_parse_sym_opamp_ellipses():
    sym = parse_symbol(_opamp_cad_data())
    unit = sym.units[0]
    assert len(unit.ellipses) >= 1
    assert unit.ellipses[0].radius_x == unit.ellipses[0].radius_y


def test_parse_sym_opamp_rectangle():
    sym = parse_symbol(_opamp_cad_data())
    assert len(sym.units[0].rectangles) == 1


def test_parse_sym_opamp_pin_rotation():
    sym = parse_symbol(_opamp_cad_data())
    unit = sym.units[0]
    assert len([p for p in unit.pins if p.rotation == 180]) == 4
    assert len([p for p in unit.pins if p.rotation == 0]) == 4


def test_parse_sym_opamp_info():
    sym = parse_symbol(_opamp_cad_data())
    assert "C7950" in sym.info.datasheet
    assert sym.units[0].bbox_x == 400
    assert sym.units[0].bbox_y == 305
