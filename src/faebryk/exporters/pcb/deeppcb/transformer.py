from __future__ import annotations

import logging
import math
from collections.abc import Iterable
from itertools import chain
from pathlib import Path
from typing import Any

from faebryk.libs.deeppcb_fileformats import C_deeppcb_board_file, deeppcb
from faebryk.libs.kicad.fileformats import Property, kicad

# Lazy imports for expand_reuse_blocks to avoid circular dependency at module level.
_PCB_Transformer = None
_get_all_geos = None


def _lazy_kicad_transformer():
    global _PCB_Transformer, _get_all_geos
    if _PCB_Transformer is None:
        from faebryk.exporters.pcb.kicad.transformer import (
            PCB_Transformer,
            get_all_geos,
        )

        _PCB_Transformer = PCB_Transformer
        _get_all_geos = get_all_geos
    return _PCB_Transformer, _get_all_geos


log = logging.getLogger(__name__)


class DeepPCB_Transformer:
    """Convert between KiCad PCB objects and DeepPCB JSON board objects.

    This mirrors the KiCad-side transformer architecture by operating directly
    on parsed fileformat objects instead of ad-hoc dicts.
    """

    RESOLUTION_VALUE = 1_000_000
    _BLANK_PCB_TEMPLATE = """(kicad_pcb
\t(version 20241229)
\t(generator "atopile")
\t(generator_version "0.0.0")
\t(general
\t\t(thickness 1.6)
\t\t(legacy_teardrops no)
\t)
\t(layers
\t\t(0 "F.Cu" signal)
\t\t(31 "B.Cu" signal)
\t\t(32 "B.Adhes" user "B.Adhesive")
\t\t(33 "F.Adhes" user "F.Adhesive")
\t\t(34 "B.Paste" user)
\t\t(35 "F.Paste" user)
\t\t(36 "B.SilkS" user "B.Silkscreen")
\t\t(37 "F.SilkS" user "F.Silkscreen")
\t\t(38 "B.Mask" user)
\t\t(39 "F.Mask" user)
\t\t(40 "Dwgs.User" user "User.Drawings")
\t\t(41 "Cmts.User" user "User.Comments")
\t\t(42 "Eco1.User" user "User.Eco1")
\t\t(43 "Eco2.User" user "User.Eco2")
\t\t(44 "Edge.Cuts" user)
\t\t(45 "Margin" user)
\t\t(46 "B.CrtYd" user "B.Courtyard")
\t\t(47 "F.CrtYd" user "F.Courtyard")
\t\t(48 "B.Fab" user)
\t\t(49 "F.Fab" user)
\t\t(50 "User.1" user)
\t\t(51 "User.2" user)
\t\t(52 "User.3" user)
\t\t(53 "User.4" user)
\t\t(54 "User.5" user)
\t\t(55 "User.6" user)
\t\t(56 "User.7" user)
\t\t(57 "User.8" user)
\t\t(58 "User.9" user)
\t)
\t(setup
\t\t(pad_to_mask_clearance 0)
\t\t(allow_soldermask_bridges_in_footprints no)
\t\t(pcbplotparams
\t\t\t(layerselection 0x00010fc_ffffffff)
\t\t\t(plot_on_all_layers_selection 0x0000000_00000000)
\t\t\t(dashed_line_dash_ratio 12)
\t\t\t(dashed_line_gap_ratio 3)
\t\t\t(svgprecision 4)
\t\t\t(mode 1)
\t\t\t(hpglpennumber 1)
\t\t\t(hpglpenspeed 20)
\t\t\t(hpglpendiameter 15)
\t\t\t(outputformat 1)
\t\t\t(drillshape 1)
\t\t\t(scaleselection 1)
\t\t\t(outputdirectory "")
\t\t)
\t)
)"""

    @classmethod
    def from_kicad_file(
        cls,
        pcb_file: Any,
        *,
        include_lossless_source: bool = False,
        provider_strict: bool = False,
        project_root: Path | None = None,
        reuse_block_metadata_out: dict[str, Any] | None = None,
    ) -> C_deeppcb_board_file:
        return cls.from_kicad_pcb(
            pcb_file.kicad_pcb,
            include_lossless_source=include_lossless_source,
            provider_strict=provider_strict,
            project_root=project_root,
            reuse_block_metadata_out=reuse_block_metadata_out,
        )

    @classmethod
    def from_kicad_pcb(
        cls,
        pcb: Any,
        *,
        include_lossless_source: bool = False,
        provider_strict: bool = False,
        project_root: Path | None = None,
        reuse_block_metadata_out: dict[str, Any] | None = None,
    ) -> C_deeppcb_board_file:
        copper_layers = [
            layer for layer in pcb.layers if str(layer.name).endswith(".Cu")
        ]
        copper_layer_index = {
            layer.name: idx for idx, layer in enumerate(copper_layers)
        }

        board = C_deeppcb_board_file(
            name="",
            rules=[],
            resolution={"unit": "mm", "value": cls.RESOLUTION_VALUE},
            boundary={
                "shape": {"type": "polyline", "points": cls._edge_cuts_points(pcb)},
                "clearance": 0,
                "segments": cls._edge_cuts_segments(pcb),
            },
            layers=[
                {
                    "id": layer.name,
                    "number": int(layer.number),
                    "type": str(getattr(layer, "type", "signal")).lower(),
                    "alias": layer.alias,
                    "keepouts": [],
                }
                for layer in pcb.layers
            ],
        )

        # padstacks are shared by vias and pins
        padstacks: dict[str, dict[str, Any]] = {}

        via_definitions: list[str] = []
        for via in pcb.vias:
            via_id, via_padstack = cls._padstack_from_via(
                via, copper_layer_index, provider_strict=provider_strict
            )
            padstacks.setdefault(via_id, via_padstack)
            if via_id not in via_definitions:
                via_definitions.append(via_id)

        # Server requires at least one via definition even for placement-only.
        if not via_definitions:
            default_via_id = (
                "Via[0-1]_0.6:0.3mm" if provider_strict else "Via_600000:300000"
            )
            via_definitions.append(default_via_id)

        component_definitions: dict[str, dict[str, Any]] = {}
        components: list[dict[str, Any]] = []

        # net id mapping
        net_id_by_number: dict[int, str] = {}
        net_name_by_number: dict[int, str] = {}
        for net in pcb.nets:
            name = str(net.name) if net.name is not None else ""
            net_id = name if name else str(net.number)
            number = int(net.number)
            net_id_by_number[number] = net_id
            net_name_by_number[number] = name

        pins_by_net: dict[str, list[str]] = {}

        # ── Reuse block pre-processing ──
        grouped_fp_uuids: set[str] = set()

        if project_root is not None:
            block_result = cls._collapse_reuse_blocks(
                pcb,
                project_root,
                copper_layer_index=copper_layer_index,
                net_id_by_number=net_id_by_number,
                provider_strict=provider_strict,
            )
            if block_result is not None:
                grouped_fp_uuids = block_result["grouped_fp_uuids"]
                component_definitions.update(block_result["definitions"])
                components.extend(block_result["components"])
                padstacks.update(block_result["padstacks"])
                for net_id, pin_list in block_result["pins_by_net"].items():
                    pins_by_net.setdefault(net_id, []).extend(pin_list)
                if reuse_block_metadata_out is not None:
                    reuse_block_metadata_out.update(block_result["metadata"])

        for fp in pcb.footprints:
            if fp.uuid in grouped_fp_uuids:
                continue
            definition_id = cls._definition_id(fp, provider_strict=provider_strict)
            if definition_id not in component_definitions:
                definition_pins = []
                seen_pin_ids: dict[str, int] = {}
                dedup_pin_map: dict[int, str] = {}  # pad_index -> deduped pin_id
                for pad_index, pad in enumerate(fp.pads):
                    pin_id = cls._pin_id(
                        pad,
                        pad_index,
                        provider_strict=provider_strict,
                    )
                    # Deduplicate pin IDs for provider output (e.g. ESP32
                    # has 9 pads named "41" which DeepPCB rejects).
                    if provider_strict:
                        if pin_id in seen_pin_ids:
                            seen_pin_ids[pin_id] += 1
                            pin_id = f"{pin_id}_{seen_pin_ids[pin_id]}"
                        else:
                            seen_pin_ids[pin_id] = 0
                    dedup_pin_map[pad_index] = pin_id
                    padstack_id, padstack = cls._padstack_from_pad(
                        pad,
                        copper_layer_index,
                        provider_strict=provider_strict,
                        strict_scope=definition_id if provider_strict else None,
                    )
                    padstacks.setdefault(padstack_id, padstack)
                    definition_pins.append(
                        {
                            "id": pin_id,
                            "padstack": padstack_id,
                            "position": cls._xy_to_point(pad.at),
                            "rotation": cls._export_rotation(
                                getattr(pad.at, "r", None),
                                provider_strict=provider_strict,
                            ),
                        }
                    )

                component_definitions[definition_id] = {
                    "id": definition_id,
                    "outline": cls._footprint_outline(fp),
                    "pins": definition_pins,
                    "keepouts": [],
                    "_dedup_pin_map": dedup_pin_map,
                }

            component_id = cls._component_id(fp, provider_strict=provider_strict)
            reference_property = None
            for prop in getattr(fp, "propertys", []):
                if str(getattr(prop, "name", "")) != "Reference":
                    continue
                reference_property = {
                    "value": str(getattr(prop, "value", component_id)),
                    "at": cls._xy_to_point(
                        getattr(prop, "at", kicad.pcb.Xyr(x=0.0, y=0.0, r=0.0))
                    ),
                    "rotation": cls._export_rotation(
                        getattr(getattr(prop, "at", None), "r", None),
                        provider_strict=provider_strict,
                    ),
                    "layer": str(getattr(prop, "layer", "F.SilkS")),
                    "hide": getattr(prop, "hide", None),
                    "unlocked": getattr(prop, "unlocked", None),
                    "effects": (
                        {
                            "font": (
                                {
                                    "size": [
                                        float(
                                            getattr(
                                                getattr(
                                                    getattr(prop.effects, "font", None),
                                                    "size",
                                                    None,
                                                ),
                                                "w",
                                                1.0,
                                            )
                                            or 1.0
                                        ),
                                        float(
                                            getattr(
                                                getattr(
                                                    getattr(prop.effects, "font", None),
                                                    "size",
                                                    None,
                                                ),
                                                "h",
                                                1.0,
                                            )
                                            or 1.0
                                        ),
                                    ],
                                    "thickness": float(
                                        getattr(
                                            getattr(prop.effects, "font", None),
                                            "thickness",
                                            0.15,
                                        )
                                        or 0.15
                                    ),
                                    "bold": getattr(
                                        getattr(prop.effects, "font", None),
                                        "bold",
                                        None,
                                    ),
                                    "italic": getattr(
                                        getattr(prop.effects, "font", None),
                                        "italic",
                                        None,
                                    ),
                                }
                                if getattr(prop.effects, "font", None) is not None
                                else None
                            ),
                            "hide": getattr(prop.effects, "hide", None),
                            "justify": (
                                {
                                    "justify1": getattr(
                                        prop.effects.justify, "justify1", None
                                    ),
                                    "justify2": getattr(
                                        prop.effects.justify, "justify2", None
                                    ),
                                    "justify3": getattr(
                                        prop.effects.justify, "justify3", None
                                    ),
                                }
                                if getattr(prop.effects, "justify", None) is not None
                                else None
                            ),
                        }
                        if getattr(prop, "effects", None) is not None
                        else None
                    ),
                }
                break
            components.append(
                {
                    "id": component_id,
                    "definition": definition_id,
                    "position": cls._xy_to_point(fp.at),
                    "rotation": cls._export_rotation(
                        getattr(fp.at, "r", None),
                        provider_strict=provider_strict,
                    ),
                    "side": "BACK" if str(fp.layer).startswith("B.") else "FRONT",
                    "partNumber": str(fp.name),
                    "protected": bool(getattr(fp, "locked", False)),
                    "embeddedFonts": getattr(fp, "embedded_fonts", None),
                    "referenceProperty": reference_property,
                }
            )

            defn_dedup = component_definitions[definition_id].get("_dedup_pin_map", {})
            for pad_index, pad in enumerate(fp.pads):
                if pad.net is None:
                    continue
                net_number = int(getattr(pad.net, "number", 0) or 0)
                net_id = net_id_by_number.get(net_number)
                if not net_id:
                    continue
                pin_id = defn_dedup.get(
                    pad_index,
                    cls._pin_id(pad, pad_index, provider_strict=provider_strict),
                )
                pins_by_net.setdefault(net_id, []).append(f"{component_id}-{pin_id}")

        # Clean up internal bookkeeping before storing definitions.
        for defn in component_definitions.values():
            defn.pop("_dedup_pin_map", None)
        board.componentDefinitions = sorted(
            component_definitions.values(),
            key=lambda d: str(d["id"]),
        )
        board.components = components
        board.padstacks = sorted(padstacks.values(), key=lambda ps: str(ps["id"]))
        board.viaDefinitions = via_definitions

        board.netClasses = [
            {
                "id": "__default__",
                "trackWidth": cls._to_unit(0.2),
                "clearance": cls._to_unit(0.2),
                "viaDefinition": via_definitions[0] if via_definitions else "",
                "nets": sorted(pins_by_net.keys()),
                "viaPriority": [[via_definitions[0]]] if via_definitions else [],
            }
        ]

        board.nets = [
            {
                "id": net_id,
                "number": number,
                "name": net_name_by_number.get(number, ""),
                "pins": sorted(set(pins_by_net.get(net_id, []))),
            }
            for number, net_id in sorted(
                net_id_by_number.items(), key=lambda item: item[0]
            )
        ]

        board.wires = [
            {
                "type": "segment",
                "netId": net_id_by_number.get(int(seg.net), str(int(seg.net))),
                "layer": copper_layer_index.get(str(seg.layer), 0),
                "start": cls._xy_to_point(seg.start),
                "end": cls._xy_to_point(seg.end),
                "width": cls._to_unit(float(seg.width)),
            }
            for seg in pcb.segments
        ]

        board.vias = [
            {
                "position": cls._xy_to_point(via.at),
                "netId": net_id_by_number.get(int(via.net), str(int(via.net))),
                "padstack": cls._via_definition_id(
                    via, provider_strict=provider_strict
                ),
                "free": getattr(via, "free", None),
            }
            for via in pcb.vias
        ]

        board.planes = []
        for zone in pcb.zones:
            if provider_strict and getattr(zone, "keepout", None) is not None:
                continue
            poly = getattr(zone, "polygon", None)
            pts = getattr(getattr(poly, "pts", None), "xys", None)
            if pts is None:
                filled = list(getattr(zone, "filled_polygon", []) or [])
                if filled:
                    pts = getattr(getattr(filled[0], "pts", None), "xys", None)
            if pts is None:
                continue
            points = [cls._xy_to_point(xy) for xy in pts]
            if not points:
                continue

            zone_layers = list(getattr(zone, "layers", []) or [])
            if provider_strict:
                layer_names = (
                    [str(layer_name) for layer_name in zone_layers]
                    if zone_layers
                    else [str(getattr(zone, "layer", "F.Cu"))]
                )
            else:
                layer_names = [
                    str(zone_layers[0])
                    if zone_layers
                    else str(getattr(zone, "layer", "F.Cu"))
                ]
            for layer_name in layer_names:
                board.planes.append(
                    {
                        "netId": net_id_by_number.get(
                            int(getattr(zone, "net", 0) or 0),
                            str(int(getattr(zone, "net", 0) or 0)),
                        ),
                        "netName": getattr(zone, "net_name", None),
                        "zoneLayer": (
                            layer_name
                            if provider_strict
                            else getattr(zone, "layer", None)
                        ),
                        "name": getattr(zone, "name", None),
                        "priority": getattr(zone, "priority", None),
                        "layer": copper_layer_index.get(layer_name, 0),
                        "shape": {
                            "type": "polygonWithHoles",
                            "outline": points,
                            "holes": [],
                        },
                        "connectPads": (
                            {
                                "mode": getattr(zone.connect_pads, "mode", None),
                                "clearance": getattr(
                                    zone.connect_pads, "clearance", None
                                ),
                            }
                            if getattr(zone, "connect_pads", None) is not None
                            else None
                        ),
                        "minThickness": getattr(zone, "min_thickness", None),
                        "filledAreasThickness": getattr(
                            zone, "filled_areas_thickness", None
                        ),
                        "keepout": (
                            {
                                "tracks": getattr(zone.keepout, "tracks", None),
                                "vias": getattr(zone.keepout, "vias", None),
                                "pads": getattr(zone.keepout, "pads", None),
                                "copperpour": getattr(zone.keepout, "copperpour", None),
                                "footprints": getattr(zone.keepout, "footprints", None),
                            }
                            if getattr(zone, "keepout", None) is not None
                            else None
                        ),
                        "placement": (
                            {
                                "sourceType": getattr(
                                    zone.placement, "source_type", None
                                ),
                                "source": getattr(zone.placement, "source", None),
                                "enabled": getattr(zone.placement, "enabled", None),
                                "sheetname": getattr(zone.placement, "sheetname", None),
                            }
                            if getattr(zone, "placement", None) is not None
                            else None
                        ),
                        "fill": (
                            {
                                "enable": getattr(zone.fill, "enable", None),
                                "thermalGap": getattr(zone.fill, "thermal_gap", None),
                                "thermalBridgeWidth": getattr(
                                    zone.fill, "thermal_bridge_width", None
                                ),
                            }
                            if getattr(zone, "fill", None) is not None
                            else None
                        ),
                    }
                )

        if include_lossless_source:
            board.metadata["kicad_pcb_sexp"] = kicad.dumps(
                kicad.pcb.PcbFile(kicad_pcb=pcb)
            )
        if getattr(pcb, "embedded_fonts", None) is not None:
            board.metadata["kicad_embedded_fonts"] = getattr(
                pcb, "embedded_fonts", None
            )
        if provider_strict:
            cls._normalize_provider_board(board)

        return board

    @classmethod
    def to_kicad_file(
        cls,
        board_file: C_deeppcb_board_file,
    ):
        return kicad.pcb.PcbFile(kicad_pcb=cls.to_internal_pcb(board_file))

    @classmethod
    def to_internal_pcb(
        cls,
        board_file: C_deeppcb_board_file,
    ):
        resolution = cls._resolution_value(board_file)
        if resolution == 1000:
            cls._reverse_provider_coordinates(board_file)
        pcb = kicad.loads(kicad.pcb.PcbFile, cls._BLANK_PCB_TEMPLATE).kicad_pcb
        resolution = cls._resolution_value(board_file)

        # Layers
        copper_layers = board_file.layers or []
        index_to_layer: dict[int, str] = {}
        reconstructed_layers = []
        if copper_layers:
            for idx, layer in enumerate(copper_layers):
                layer_id = str(layer.get("id", f"L{idx}"))
                index_to_layer[idx] = layer_id
                reconstructed_layers.append(
                    kicad.pcb.Layer(
                        number=int(layer.get("number", idx)),
                        name=layer_id,
                        type=str(layer.get("type", "signal")),
                        alias=layer.get("alias"),
                    )
                )
        if reconstructed_layers:
            pcb.layers = reconstructed_layers

        # Nets
        net_number_by_id: dict[str, int] = {}
        net_name_by_id: dict[str, str] = {}
        nets = []
        for idx, net in enumerate(board_file.nets, start=1):
            net_id = str(net.get("id", f"NET-{idx}"))
            number = int(net.get("number", idx))
            name = net.get("name")
            if name is None:
                name = net_id if net_id != str(number) else None
            if isinstance(name, str):
                net_name_by_id[net_id] = name
            net_number_by_id[net_id] = number
            nets.append(kicad.pcb.Net(number=number, name=name))
        pcb.nets = nets

        # Boundary -> Edge.Cuts lines
        pcb.gr_lines = []
        boundary = board_file.boundary if isinstance(board_file.boundary, dict) else {}
        boundary_segments = boundary.get("segments")
        if isinstance(boundary_segments, list) and boundary_segments:
            for segment in boundary_segments:
                if not isinstance(segment, dict) or segment.get("type") != "line":
                    continue
                start = segment.get("start")
                end = segment.get("end")
                if not (isinstance(start, list) and isinstance(end, list)):
                    continue
                pcb.gr_lines.append(
                    kicad.pcb.Line(
                        start=cls._point_to_xy(start, resolution),
                        end=cls._point_to_xy(end, resolution),
                        solder_mask_margin=None,
                        stroke=kicad.pcb.Stroke(
                            width=float(segment.get("strokeWidth", 0.2)),
                            type=str(segment.get("strokeType", "default")),
                        ),
                        fill=segment.get("fill"),
                        layer="Edge.Cuts",
                        layers=[],
                        locked=segment.get("locked"),
                        uuid=kicad.gen_uuid(),
                    )
                )
        else:
            boundary_points = cls._boundary_points(board_file)
            for start, end in zip(boundary_points, boundary_points[1:]):
                pcb.gr_lines.append(
                    kicad.pcb.Line(
                        start=cls._point_to_xy(start, resolution),
                        end=cls._point_to_xy(end, resolution),
                        solder_mask_margin=None,
                        stroke=kicad.pcb.Stroke(width=0.2, type="default"),
                        fill=None,
                        layer="Edge.Cuts",
                        layers=[],
                        locked=None,
                        uuid=kicad.gen_uuid(),
                    )
                )

        # Segments
        pcb.segments = []
        for wire in board_file.wires:
            start = wire.get("start")
            end = wire.get("end")
            if not (isinstance(start, list) and isinstance(end, list)):
                continue
            layer_id = index_to_layer.get(int(wire.get("layer", 0)), "F.Cu")
            net_id = str(wire.get("netId", ""))
            pcb.segments.append(
                kicad.pcb.Segment(
                    start=cls._point_to_xy(start, resolution),
                    end=cls._point_to_xy(end, resolution),
                    width=cls._from_unit(float(wire.get("width", 200)), resolution),
                    layer=layer_id,
                    net=net_number_by_id.get(net_id, 0),
                    uuid=kicad.gen_uuid(),
                )
            )

        # Vias
        padstack_by_id = {
            str(padstack.get("id", "")): padstack for padstack in board_file.padstacks
        }
        pcb.vias = []
        for via in board_file.vias:
            pos = via.get("position")
            if not isinstance(pos, list):
                continue
            padstack_id = str(via.get("padstack", ""))
            padstack = padstack_by_id.get(padstack_id, {})
            radius = cls._shape_radius(padstack.get("shape"), default=300)
            drill_raw = padstack.get("drill")
            if drill_raw is not None:
                drill_radius = float(drill_raw)
            else:
                # Strict-mode boards store drill geometry in the hole field
                # rather than a separate drill scalar.
                hole = padstack.get("hole")
                if isinstance(hole, dict):
                    hole_shape = hole.get("shape", {})
                    hole_r = hole_shape.get("radius")
                    if not isinstance(hole_r, (int, float)):
                        raise ValueError(
                            f"Via padstack {padstack_id!r} has no drill or "
                            f"hole radius"
                        )
                    drill_radius = float(hole_r)
                else:
                    raise ValueError(
                        f"Via padstack {padstack_id!r} has no drill or hole "
                        f"field"
                    )
            layer_ids = [
                index_to_layer.get(int(i), "F.Cu")
                for i in padstack.get("layers", [0, 1])
                if isinstance(i, int)
            ]
            if not layer_ids:
                layer_ids = ["F.Cu", "B.Cu"]
            net_id = str(via.get("netId", ""))
            pcb.vias.append(
                kicad.pcb.Via(
                    at=cls._point_to_xy(pos, resolution),
                    size=cls._from_unit(radius * 2.0, resolution),
                    drill=cls._from_unit(drill_radius * 2.0, resolution),
                    layers=layer_ids,
                    net=net_number_by_id.get(net_id, 0),
                    remove_unused_layers=None,
                    keep_end_layers=None,
                    zone_layer_connections=[],
                    padstack=None,
                    teardrops=None,
                    tenting=None,
                    free=via.get("free"),
                    locked=None,
                    uuid=kicad.gen_uuid(),
                )
            )

        # Planes -> zones
        pcb.zones = []
        for plane in board_file.planes:
            shape = plane.get("shape")
            if not isinstance(shape, dict):
                continue
            points = shape.get("outline") or shape.get("points")
            if not isinstance(points, list) or not points:
                continue
            layer_id = index_to_layer.get(int(plane.get("layer", 0)), "F.Cu")
            net_id = str(plane.get("netId", ""))
            net_no = net_number_by_id.get(net_id, 0)
            connect_pads_payload = plane.get("connectPads")
            connect_pads = (
                kicad.pcb.ConnectPads(
                    mode=connect_pads_payload.get("mode"),
                    clearance=connect_pads_payload.get("clearance"),
                )
                if isinstance(connect_pads_payload, dict)
                else None
            )
            keepout_payload = plane.get("keepout")
            keepout = (
                kicad.pcb.ZoneKeepout(
                    tracks=keepout_payload.get("tracks"),
                    vias=keepout_payload.get("vias"),
                    pads=keepout_payload.get("pads"),
                    copperpour=keepout_payload.get("copperpour"),
                    footprints=keepout_payload.get("footprints"),
                )
                if isinstance(keepout_payload, dict)
                else None
            )
            placement_payload = plane.get("placement")
            placement = (
                kicad.pcb.ZonePlacement(
                    source_type=placement_payload.get("sourceType"),
                    source=placement_payload.get("source"),
                    enabled=placement_payload.get("enabled"),
                    sheetname=placement_payload.get("sheetname"),
                )
                if isinstance(placement_payload, dict)
                else None
            )
            fill_payload = plane.get("fill")
            fill = (
                kicad.pcb.ZoneFill(
                    enable=fill_payload.get("enable"),
                    mode=None,
                    hatch_thickness=None,
                    hatch_gap=None,
                    hatch_orientation=None,
                    hatch_smoothing_level=None,
                    hatch_smoothing_value=None,
                    hatch_border_algorithm=None,
                    hatch_min_hole_area=None,
                    arc_segments=None,
                    thermal_gap=fill_payload.get("thermalGap"),
                    thermal_bridge_width=fill_payload.get("thermalBridgeWidth"),
                    smoothing=None,
                    radius=None,
                    island_removal_mode=None,
                    island_area_min=None,
                )
                if isinstance(fill_payload, dict)
                else None
            )
            pcb.zones.append(
                kicad.pcb.Zone(
                    net=net_no,
                    net_name=plane.get("netName", net_id),
                    layer=plane.get("zoneLayer"),
                    layers=[layer_id],
                    uuid=kicad.gen_uuid(),
                    name=plane.get("name"),
                    hatch=kicad.pcb.Hatch(mode="edge", pitch=0.5),
                    priority=plane.get("priority"),
                    attr=None,
                    connect_pads=connect_pads,
                    min_thickness=float(plane.get("minThickness", 0.2) or 0.2),
                    filled_areas_thickness=plane.get("filledAreasThickness"),
                    keepout=keepout,
                    placement=placement,
                    fill=fill,
                    polygon=kicad.pcb.Polygon(
                        pts=kicad.pcb.Pts(
                            xys=[
                                cls._point_to_xy(point, resolution) for point in points
                            ]
                        ),
                        solder_mask_margin=None,
                        stroke=None,
                        fill=None,
                        layer=None,
                        layers=[],
                        locked=None,
                        uuid=None,
                    ),
                    filled_polygon=[],
                )
            )

        # Components/definitions/pads
        definition_by_id = {
            str(definition.get("id", "")): definition
            for definition in board_file.componentDefinitions
        }
        pins_by_net: dict[str, set[str]] = {
            str(net.get("id", "")): set(
                str(pin) for pin in net.get("pins", []) if isinstance(pin, str)
            )
            for net in board_file.nets
        }

        pcb.footprints = []
        for component in board_file.components:
            component_id = str(component.get("id", ""))
            decoded_reference, decoded_atopile_address = cls._decode_component_id(
                component_id
            )
            definition_id = str(component.get("definition", ""))
            definition = definition_by_id.get(definition_id, {})
            position = component.get("position", [0, 0])
            component_rotation = component.get("rotation")
            rotation = (
                float(component_rotation) if component_rotation is not None else None
            )
            side = str(component.get("side", "FRONT")).upper()
            layer = "B.Cu" if side == "BACK" else "F.Cu"

            pads = []
            for pin in definition.get("pins", []):
                pin_id = str(pin.get("id", ""))
                padstack_id = str(pin.get("padstack", ""))
                padstack = padstack_by_id.get(padstack_id, {})
                layers_idx = [
                    int(layer_idx)
                    for layer_idx in padstack.get("layers", [0, 1])
                    if isinstance(layer_idx, int)
                ]
                pad_layers = [index_to_layer.get(idx, "F.Cu") for idx in layers_idx]
                stored_layers = padstack.get("kicadLayers")
                has_kicad_layers = isinstance(stored_layers, list) and bool(
                    stored_layers
                )
                if has_kicad_layers:
                    pad_layers = [str(layer) for layer in stored_layers]
                if not pad_layers:
                    pad_layers = ["F.Cu", "B.Cu"]

                net_ref = None
                for net_id, pins in pins_by_net.items():
                    if f"{component_id}-{pin_id}" in pins:
                        net_name = net_name_by_id.get(net_id, net_id)
                        net_ref = kicad.pcb.Net(
                            number=net_number_by_id.get(net_id, 0),
                            name=net_name,
                        )
                        break

                size_w, size_h = cls._shape_size(padstack.get("shape"), default=850)
                stored_size = padstack.get("kicadSize")
                if (
                    isinstance(stored_size, list)
                    and len(stored_size) >= 2
                    and all(isinstance(v, (int, float)) for v in stored_size[:2])
                ):
                    size_w = float(stored_size[0])
                    size_h = float(stored_size[1])
                pad_shape = str(
                    padstack.get("kicadShape") or cls._pad_shape(padstack.get("shape"))
                )
                has_hole = padstack.get("hole") is not None
                pad_type = str(
                    padstack.get("kicadPadType")
                    or (
                        (
                            "np_thru_hole"
                            if has_hole and net_ref is None
                            else "thru_hole"
                        )
                        if "F.Cu" in pad_layers and "B.Cu" in pad_layers
                        else "smd"
                    )
                )

                # Infer non-copper layers when kicadLayers hint was stripped
                if not has_kicad_layers:
                    pad_layers = cls._infer_non_copper_layers(pad_layers, pad_type)

                drill_payload = padstack.get("kicadDrill")
                pad_drill = None
                if isinstance(drill_payload, dict):
                    drill_offset = drill_payload.get("offset")
                    pad_drill = kicad.pcb.PadDrill(
                        shape=drill_payload.get("shape"),
                        size_x=float(drill_payload.get("sizeX", 0.0) or 0.0),
                        size_y=(
                            float(drill_payload.get("sizeY"))
                            if drill_payload.get("sizeY") is not None
                            else None
                        ),
                        offset=(
                            kicad.pcb.Xy(
                                x=float(drill_offset[0]),
                                y=float(drill_offset[1]),
                            )
                            if isinstance(drill_offset, list) and len(drill_offset) >= 2
                            else None
                        ),
                    )
                elif padstack.get("hole") is not None:
                    # Strict-mode boards store drill geometry in the hole field
                    # rather than kicadDrill.
                    hole_shape = padstack["hole"].get("shape", {})
                    hole_type = str(hole_shape.get("type", ""))
                    if hole_type == "circle":
                        hole_r = hole_shape.get("radius")
                        if isinstance(hole_r, (int, float)):
                            pad_drill = kicad.pcb.PadDrill(
                                shape=None,
                                size_x=cls._from_unit(float(hole_r) * 2.0, resolution),
                                size_y=None,
                                offset=None,
                            )
                    elif hole_type == "path":
                        hole_width = hole_shape.get("width")
                        hole_pts = hole_shape.get("points", [])
                        if isinstance(hole_width, (int, float)):
                            minor_mm = cls._from_unit(float(hole_width), resolution)
                            pt_dist = 0.0
                            if (
                                isinstance(hole_pts, list)
                                and len(hole_pts) >= 2
                                and isinstance(hole_pts[0], list)
                                and isinstance(hole_pts[1], list)
                            ):
                                dx = float(hole_pts[1][0]) - float(hole_pts[0][0])
                                dy = float(hole_pts[1][1]) - float(hole_pts[0][1])
                                pt_dist = math.sqrt(dx * dx + dy * dy)
                            major_mm = minor_mm + cls._from_unit(pt_dist, resolution)
                            # Determine axis from point direction
                            if (
                                isinstance(hole_pts, list)
                                and len(hole_pts) >= 2
                                and isinstance(hole_pts[0], list)
                                and isinstance(hole_pts[1], list)
                            ):
                                adx = abs(float(hole_pts[1][0]) - float(hole_pts[0][0]))
                                ady = abs(float(hole_pts[1][1]) - float(hole_pts[0][1]))
                                if adx > ady:
                                    size_x, size_y = major_mm, minor_mm
                                else:
                                    size_x, size_y = minor_mm, major_mm
                            else:
                                size_x, size_y = minor_mm, major_mm
                            pad_drill = kicad.pcb.PadDrill(
                                shape="oval",
                                size_x=size_x,
                                size_y=size_y,
                                offset=None,
                            )

                options_payload = padstack.get("kicadOptions")
                pad_options = None
                if isinstance(options_payload, dict):
                    clearance = options_payload.get("clearance")
                    anchor = options_payload.get("anchor")
                    if clearance is not None or anchor is not None:
                        pad_options = kicad.pcb.PadOptions(
                            clearance=clearance,
                            anchor=anchor,
                        )

                pads.append(
                    kicad.pcb.Pad(
                        name=pin_id,
                        type=pad_type,
                        shape=pad_shape,
                        at=kicad.pcb.Xyr(
                            x=cls._from_unit(
                                float(pin.get("position", [0, 0])[0]), resolution
                            ),
                            y=cls._from_unit(
                                float(pin.get("position", [0, 0])[1]), resolution
                            ),
                            r=(
                                float(pin.get("rotation"))
                                if pin.get("rotation") is not None
                                else None
                            ),
                        ),
                        size=kicad.pcb.Wh(
                            w=cls._from_unit(size_w, resolution),
                            h=cls._from_unit(size_h, resolution),
                        ),
                        drill=pad_drill,
                        layers=pad_layers,
                        remove_unused_layers=padstack.get("kicadRemoveUnusedLayers"),
                        net=net_ref,
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
                        options=pad_options,
                        tenting=None,
                        uuid=kicad.gen_uuid(),
                        primitives=None,
                    )
                )

            fp_lines, fp_arcs, fp_circles, fp_polys = cls._outline_to_fp_shapes(
                definition.get("outline"),
                resolution,
            )

            reference_prop = component.get("referenceProperty")
            if isinstance(reference_prop, dict):
                ref_value = str(reference_prop.get("value", decoded_reference))
                ref_value, inline_addr = cls._decode_component_id(ref_value)
                if not decoded_atopile_address and inline_addr:
                    decoded_atopile_address = inline_addr
                ref_point = reference_prop.get("at", [0, 0])
                if not isinstance(ref_point, list) or len(ref_point) < 2:
                    ref_point = [0, 0]
                ref_rotation = (
                    float(reference_prop.get("rotation"))
                    if reference_prop.get("rotation") is not None
                    else None
                )
                ref_layer = str(reference_prop.get("layer", "F.SilkS"))
                ref_hide = reference_prop.get("hide")
                ref_unlocked = reference_prop.get("unlocked")
                effects_payload = reference_prop.get("effects")
            else:
                ref_value = decoded_reference
                ref_point = [0, 0]
                ref_rotation = None
                ref_layer = "F.SilkS"
                ref_hide = None
                ref_unlocked = None
                effects_payload = None
            embedded_fonts = component.get("embeddedFonts")

            effects = None
            if isinstance(effects_payload, dict):
                font_payload = effects_payload.get("font")
                font = None
                if isinstance(font_payload, dict):
                    size_payload = font_payload.get("size", [1.0, 1.0])
                    if not isinstance(size_payload, list) or len(size_payload) < 2:
                        size_payload = [1.0, 1.0]
                    font = kicad.pcb.Font(
                        size=kicad.pcb.Wh(
                            w=float(size_payload[0]),
                            h=float(size_payload[1]),
                        ),
                        thickness=float(font_payload.get("thickness", 0.15) or 0.15),
                        bold=font_payload.get("bold"),
                        italic=font_payload.get("italic"),
                    )
                justify_payload = effects_payload.get("justify")
                justify = (
                    kicad.pcb.Justify(
                        justify1=justify_payload.get("justify1"),
                        justify2=justify_payload.get("justify2"),
                        justify3=justify_payload.get("justify3"),
                    )
                    if isinstance(justify_payload, dict)
                    else None
                )
                effects = kicad.pcb.Effects(
                    font=font,
                    hide=effects_payload.get("hide"),
                    justify=justify,
                )

            pcb.footprints.append(
                kicad.pcb.Footprint(
                    name=str(
                        component.get("partNumber", definition_id or component_id)
                    ),
                    layer=layer,
                    uuid=kicad.gen_uuid(),
                    at=kicad.pcb.Xyr(
                        x=cls._from_unit(float(position[0]), resolution),
                        y=cls._from_unit(float(position[1]), resolution),
                        r=rotation,
                    ),
                    path=None,
                    propertys=cls._component_properties(
                        ref_value=ref_value,
                        ref_point=ref_point,
                        ref_rotation=ref_rotation,
                        ref_unlocked=ref_unlocked,
                        ref_layer=ref_layer,
                        ref_hide=ref_hide,
                        effects=effects,
                        resolution=resolution,
                        atopile_address=decoded_atopile_address,
                    ),
                    attr=[],
                    fp_lines=fp_lines,
                    fp_arcs=fp_arcs,
                    fp_circles=fp_circles,
                    fp_rects=[],
                    fp_poly=fp_polys,
                    fp_texts=[],
                    pads=pads,
                    embedded_fonts=embedded_fonts,
                    models=[],
                )
            )

        # Clear unsupported primitives for now.
        pcb.arcs = []
        pcb.gr_arcs = []
        pcb.gr_curves = []
        pcb.gr_circles = []
        pcb.gr_rects = []
        pcb.gr_polys = []
        pcb.gr_texts = []
        pcb.gr_text_boxes = []
        pcb.images = []
        pcb.dimensions = []
        pcb.groups = []
        pcb.targets = []
        pcb.tables = []
        pcb.generateds = []
        if (
            isinstance(board_file.metadata, dict)
            and "kicad_embedded_fonts" in board_file.metadata
        ):
            pcb.embedded_fonts = board_file.metadata.get("kicad_embedded_fonts")
        return pcb

    @staticmethod
    def loads(path_or_content):
        return deeppcb.loads(deeppcb.board.BoardFile, path_or_content)

    @staticmethod
    def dumps(board_file: C_deeppcb_board_file, path=None) -> str:
        return deeppcb.dumps(board_file, path)

    @staticmethod
    def _infer_non_copper_layers(copper_layers: list[str], pad_type: str) -> list[str]:
        """Add standard non-copper layers when kicadLayers hint is absent."""
        layers = list(copper_layers)
        if pad_type in {"thru_hole", "np_thru_hole"}:
            if "*.Cu" not in layers:
                # Ensure all-copper wildcard
                layers = ["*.Cu"] + [ly for ly in layers if not ly.endswith(".Cu")]
            if "F.Mask" not in layers:
                layers.append("F.Mask")
            if "B.Mask" not in layers:
                layers.append("B.Mask")
        elif pad_type == "smd":
            if "F.Cu" in layers and "B.Cu" not in layers:
                if "F.Paste" not in layers:
                    layers.append("F.Paste")
                if "F.Mask" not in layers:
                    layers.append("F.Mask")
            elif "B.Cu" in layers and "F.Cu" not in layers:
                if "B.Paste" not in layers:
                    layers.append("B.Paste")
                if "B.Mask" not in layers:
                    layers.append("B.Mask")
        return layers

    @classmethod
    def _to_unit(cls, mm: float) -> int:
        return int(round(mm * cls.RESOLUTION_VALUE))

    @staticmethod
    def _export_rotation(value: Any, *, provider_strict: bool) -> int | float | None:
        if value is None:
            return 0 if provider_strict else None
        as_float = float(value)
        if provider_strict:
            return int(round(as_float))
        return as_float

    @staticmethod
    def _from_unit(value: float, resolution: int) -> float:
        return float(value) / float(resolution)

    @classmethod
    def _xy_to_point(cls, xy: Any) -> list[int]:
        return [cls._to_unit(float(xy.x)), cls._to_unit(float(xy.y))]

    @staticmethod
    def _point_to_xy(point: list[Any], resolution: int):
        return kicad.pcb.Xy(
            x=float(point[0]) / float(resolution),
            y=float(point[1]) / float(resolution),
        )

    @staticmethod
    def _resolution_value(board_file: C_deeppcb_board_file) -> int:
        value = board_file.resolution.get("value")
        if isinstance(value, int) and value > 0:
            return value
        if isinstance(value, float) and value > 0:
            return int(value)
        return DeepPCB_Transformer.RESOLUTION_VALUE

    @staticmethod
    def _boundary_points(board_file: C_deeppcb_board_file) -> list[list[Any]]:
        boundary = board_file.boundary if isinstance(board_file.boundary, dict) else {}
        shape = boundary.get("shape")
        if not isinstance(shape, dict):
            return []
        points = shape.get("points")
        if not isinstance(points, list):
            return []
        parsed = [
            point for point in points if isinstance(point, list) and len(point) >= 2
        ]
        if parsed and parsed[0] != parsed[-1]:
            parsed.append(parsed[0])
        return parsed

    @staticmethod
    def _shape_radius(shape: Any, default: float) -> float:
        if not isinstance(shape, dict):
            return default
        radius = shape.get("radius")
        if isinstance(radius, (int, float)):
            return float(radius)
        if shape.get("type") == "polyline":
            points = shape.get("points", [])
            if isinstance(points, list) and len(points) >= 2:
                xs = [
                    float(p[0]) for p in points if isinstance(p, list) and len(p) >= 2
                ]
                ys = [
                    float(p[1]) for p in points if isinstance(p, list) and len(p) >= 2
                ]
                if xs and ys:
                    return max(max(xs) - min(xs), max(ys) - min(ys)) / 2.0
        return default

    @staticmethod
    def _shape_size(shape: Any, default: float) -> tuple[float, float]:
        if not isinstance(shape, dict):
            return default, default
        shape_type = shape.get("type")
        if shape_type == "circle":
            radius = shape.get("radius")
            if isinstance(radius, (int, float)):
                diameter = float(radius) * 2.0
                return diameter, diameter
            return default, default
        if shape_type == "rectangle":
            lower_left = shape.get("lowerLeft")
            upper_right = shape.get("upperRight")
            if (
                isinstance(lower_left, list)
                and isinstance(upper_right, list)
                and len(lower_left) >= 2
                and len(upper_right) >= 2
            ):
                w = abs(float(upper_right[0]) - float(lower_left[0]))
                h = abs(float(upper_right[1]) - float(lower_left[1]))
                return w, h
        if shape_type == "path":
            # Oval pad: minor dimension = width, major = width + distance between
            # the two path endpoints.  The forward path sets
            # travel = (max_dim - min_dim) / 2 and points [[0, travel], [0, -travel]]
            # so point_distance = 2*travel and major = minor + point_distance.
            width = shape.get("width")
            if isinstance(width, (int, float)):
                minor = float(width)
                points = shape.get("points", [])
                point_dist = 0.0
                if isinstance(points, list) and len(points) >= 2:
                    p0 = points[0]
                    p1 = points[1]
                    if (
                        isinstance(p0, list)
                        and isinstance(p1, list)
                        and len(p0) >= 2
                        and len(p1) >= 2
                    ):
                        dx = float(p1[0]) - float(p0[0])
                        dy = float(p1[1]) - float(p0[1])
                        point_dist = math.sqrt(dx * dx + dy * dy)
                major = minor + point_dist
                # Determine axis orientation from point direction
                if isinstance(points, list) and len(points) >= 2:
                    p0, p1 = points[0], points[1]
                    if (
                        isinstance(p0, list)
                        and isinstance(p1, list)
                        and len(p0) >= 2
                        and len(p1) >= 2
                    ):
                        dx = abs(float(p1[0]) - float(p0[0]))
                        dy = abs(float(p1[1]) - float(p0[1]))
                        if dx > dy:
                            return major, minor  # major axis is X
                return minor, major  # major axis is Y (default)
        if shape_type == "polyline":
            points = shape.get("points", [])
            if isinstance(points, list):
                xs = [
                    float(p[0]) for p in points if isinstance(p, list) and len(p) >= 2
                ]
                ys = [
                    float(p[1]) for p in points if isinstance(p, list) and len(p) >= 2
                ]
                if xs and ys:
                    return max(xs) - min(xs), max(ys) - min(ys)
        return default, default

    @staticmethod
    def _pad_shape(shape: Any) -> str:
        if isinstance(shape, dict):
            shape_type = str(shape.get("type", "")).lower()
            if shape_type == "circle":
                return "circle"
            if shape_type == "path":
                return "oval"
            if shape_type in {"rect", "rectangle", "polyline", "polygon"}:
                return "rect"
        return "circle"

    @classmethod
    def _outline_to_fp_shapes(
        cls,
        outline: Any,
        resolution: int,
    ) -> tuple[list[Any], list[Any], list[Any], list[Any]]:
        fp_lines = []
        fp_arcs = []
        fp_circles = []
        fp_polys = []

        if not isinstance(outline, dict):
            return fp_lines, fp_arcs, fp_circles, fp_polys

        shapes = []
        if outline.get("type") == "multi":
            raw_shapes = outline.get("shapes", [])
            if isinstance(raw_shapes, list):
                shapes = [shape for shape in raw_shapes if isinstance(shape, dict)]
        else:
            shapes = [outline]

        for shape in shapes:
            shape_type = str(shape.get("type", "")).lower()
            layer = str(shape.get("layer") or "F.Fab")
            stroke_width = float(shape.get("strokeWidth", 0.12))
            stroke_type = str(shape.get("strokeType") or "solid")
            stroke = kicad.pcb.Stroke(width=stroke_width, type=stroke_type)
            fill = shape.get("fill")
            locked = shape.get("locked")
            if shape_type == "circle":
                center = shape.get("center", [0, 0])
                radius = float(shape.get("radius", 0.0))
                if not (isinstance(center, list) and len(center) >= 2):
                    continue
                center_xy = cls._point_to_xy(center, resolution)
                end_xy = kicad.pcb.Xy(
                    x=center_xy.x + cls._from_unit(radius, resolution),
                    y=center_xy.y,
                )
                fp_circles.append(
                    kicad.pcb.Circle(
                        center=center_xy,
                        end=end_xy,
                        solder_mask_margin=None,
                        stroke=stroke,
                        fill=fill,
                        layer=layer,
                        layers=[],
                        locked=locked,
                        uuid=kicad.gen_uuid(),
                    )
                )
                continue

            points = shape.get("points", [])
            if not isinstance(points, list) or len(points) < 2:
                continue
            xy_points = [
                cls._point_to_xy(point, resolution)
                for point in points
                if isinstance(point, list) and len(point) >= 2
            ]
            if len(xy_points) < 2:
                continue

            if len(xy_points) > 2:
                fp_polys.append(
                    kicad.pcb.Polygon(
                        pts=kicad.pcb.Pts(xys=xy_points),
                        solder_mask_margin=None,
                        stroke=stroke,
                        fill=fill,
                        layer=layer,
                        layers=[],
                        locked=locked,
                        uuid=kicad.gen_uuid(),
                    )
                )
            else:
                fp_lines.append(
                    kicad.pcb.Line(
                        start=xy_points[0],
                        end=xy_points[1],
                        solder_mask_margin=None,
                        stroke=stroke,
                        fill=fill,
                        layer=layer,
                        layers=[],
                        locked=locked,
                        uuid=kicad.gen_uuid(),
                    )
                )

        return fp_lines, fp_arcs, fp_circles, fp_polys

    @classmethod
    def _layer_indices(
        cls, layers: Iterable[str], copper_layer_index: dict[str, int]
    ) -> list[int]:
        indices: list[int] = []
        for layer in layers:
            if layer in copper_layer_index:
                indices.append(copper_layer_index[layer])
            elif layer == "*.Cu":
                indices.extend(sorted(copper_layer_index.values()))
        if not indices:
            indices = sorted(copper_layer_index.values())
        # preserve order but deduplicate
        seen: set[int] = set()
        out: list[int] = []
        for idx in indices:
            if idx in seen:
                continue
            seen.add(idx)
            out.append(idx)
        return out

    @classmethod
    def _padstack_from_pad(
        cls,
        pad: Any,
        copper_layer_index: dict[str, int],
        *,
        provider_strict: bool = False,
        strict_scope: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        shape = str(getattr(pad, "shape", "circle")).lower()
        pad_type = str(getattr(pad, "type", "smd"))
        size_w = float(getattr(pad.size, "w", 0.0) or 0.0)
        size_h = float(getattr(pad.size, "h", size_w) or size_w)
        raw_layers = [str(layer) for layer in getattr(pad, "layers", [])]
        layers = cls._layer_indices(raw_layers, copper_layer_index)
        remove_unused_layers = getattr(pad, "remove_unused_layers", None)

        drill = getattr(pad, "drill", None)
        drill_payload = None
        if drill is not None:
            drill_offset = getattr(drill, "offset", None)
            drill_payload = {
                "shape": getattr(drill, "shape", None),
                "sizeX": float(getattr(drill, "size_x", 0.0) or 0.0),
                "sizeY": (
                    float(getattr(drill, "size_y"))
                    if getattr(drill, "size_y", None) is not None
                    else None
                ),
                "offset": (
                    [
                        float(getattr(drill_offset, "x", 0.0) or 0.0),
                        float(getattr(drill_offset, "y", 0.0) or 0.0),
                    ]
                    if drill_offset is not None
                    else None
                ),
            }

        pad_options = getattr(pad, "options", None)
        options_payload = None
        if pad_options is not None:
            options_payload = {
                "clearance": getattr(pad_options, "clearance", None),
                "anchor": getattr(pad_options, "anchor", None),
            }

        raw_layers_id = ",".join(raw_layers)
        drill_id = ""
        if isinstance(drill_payload, dict):
            drill_id = (
                f"_D{drill_payload.get('shape')}"
                f":{drill_payload.get('sizeX')}"
                f":{drill_payload.get('sizeY')}"
            )

        if provider_strict and shape == "custom":
            layer_suffix = "0_1" if len(layers) > 1 else "0"
            size_w_i = cls._to_unit(size_w) // 1000
            size_h_i = cls._to_unit(size_h) // 1000
            pad_name = str(getattr(pad, "name", "0"))
            padstack_id = (
                f"Padstack_Pad_{pad_name}_{size_w_i}_{size_h_i}_L{layer_suffix}"
            )
            width = cls._to_unit(min(size_w, size_h))
            travel = max(0.0, (max(size_w, size_h) - min(size_w, size_h)) / 2.0)
            geom = {
                "type": "path",
                "points": [[0, cls._to_unit(travel)], [0, -cls._to_unit(travel)]],
                "width": width,
            }
        elif provider_strict and shape in {"rect", "rectangle"}:
            half_w = cls._to_unit(size_w / 2.0) // 1000
            half_h = cls._to_unit(size_h / 2.0) // 1000
            layer_suffix = "0_1" if len(layers) > 1 else "0"
            padstack_id = (
                f"Padstack_Rectangle_{-half_w}_{-half_h}"
                f"_{half_w}_{half_h}_L{layer_suffix}"
            )
            geom = {
                "type": "rectangle",
                "lowerLeft": [-cls._to_unit(size_w / 2.0), -cls._to_unit(size_h / 2.0)],
                "upperRight": [cls._to_unit(size_w / 2.0), cls._to_unit(size_h / 2.0)],
            }
        elif provider_strict and shape in {"oval"}:
            width = cls._to_unit(min(size_w, size_h))
            travel = max(0.0, (max(size_w, size_h) - min(size_w, size_h)) / 2.0)
            geom = {
                "type": "path",
                "points": [[0, cls._to_unit(travel)], [0, -cls._to_unit(travel)]],
                "width": width,
            }
            layer_suffix = "0_1" if len(layers) > 1 else "0"
            padstack_id = (
                f"Padstack_Pad_{str(getattr(pad, 'name', '0'))}_L{layer_suffix}"
            )
        elif (
            provider_strict
            and shape == "circle"
            and drill_payload is not None
            and len(layers) > 1
        ):
            radius = max(size_w, size_h) / 2.0
            geom = {
                "type": "circle",
                "center": [0, 0],
                "radius": cls._to_unit(radius),
            }
            radius = int(round(max(size_w, size_h) * 500))
            drill_x = drill_payload.get("sizeX")
            drill_y = drill_payload.get("sizeY")
            padstack_id = (
                f"Padstack_Circle_0_0_{radius}_D{drill_x}_{drill_y}"
                f"_P{str(getattr(pad, 'name', '0'))}_L0_1"
            )
        elif shape in {"circle", "oval"}:
            radius = max(size_w, size_h) / 2.0
            geom = {
                "type": "circle",
                "center": [0, 0],
                "radius": cls._to_unit(radius),
            }
            padstack_id = (
                f"Padstack_{shape}_{pad_type}_{cls._to_unit(size_w)}x{cls._to_unit(size_h)}"
                f"_L{','.join(map(str, layers))}_RAW{raw_layers_id}{drill_id}"
            )
        else:
            half_w = cls._to_unit(size_w / 2.0)
            half_h = cls._to_unit(size_h / 2.0)
            geom = {
                "type": "polyline",
                "points": [
                    [-half_w, -half_h],
                    [half_w, -half_h],
                    [half_w, half_h],
                    [-half_w, half_h],
                    [-half_w, -half_h],
                ],
            }
            padstack_id = (
                f"Padstack_{shape}_{pad_type}_{cls._to_unit(size_w)}x{cls._to_unit(size_h)}"
                f"_L{','.join(map(str, layers))}_RAW{raw_layers_id}{drill_id}"
            )
        if (
            provider_strict
            and strict_scope
            and shape not in {"rect", "rectangle", "custom", "oval"}
        ):
            padstack_id = f"{padstack_id}_{strict_scope}"
        padstack: dict[str, Any] = {
            "id": padstack_id,
            "shape": geom,
            "layers": layers,
            "allowVia": False,
            "kicadShape": shape,
            "kicadPadType": pad_type,
            "kicadSize": [cls._to_unit(size_w), cls._to_unit(size_h)],
            "kicadLayers": raw_layers,
            "kicadRemoveUnusedLayers": remove_unused_layers,
            "kicadDrill": drill_payload,
            "kicadOptions": options_payload,
        }
        # Through-hole pads need hole + pads fields for DeepPCB.
        if provider_strict and len(layers) > 1 and drill_payload is not None:
            drill_x = float(drill_payload.get("sizeX", 0.0) or 0.0)
            drill_y_raw = drill_payload.get("sizeY")
            drill_y = float(drill_y_raw) if drill_y_raw is not None else drill_x
            if drill_x > 0 or drill_y > 0:
                padstack["pads"] = [
                    {
                        "shape": dict(geom),
                        "layerFrom": layers[0],
                        "layerTo": layers[-1],
                    }
                ]
                drill_shape_str = str(drill_payload.get("shape", "") or "")
                if "oval" in drill_shape_str or (
                    drill_y > 0 and abs(drill_x - drill_y) > 0.001
                ):
                    # Oval/slot drill hole.
                    minor = min(drill_x, drill_y)
                    travel = max(0.0, (max(drill_x, drill_y) - minor) / 2.0)
                    if drill_x < drill_y:
                        pts = [[0, cls._to_unit(travel)], [0, -cls._to_unit(travel)]]
                    else:
                        pts = [[cls._to_unit(travel), 0], [-cls._to_unit(travel), 0]]
                    padstack["hole"] = {
                        "shape": {
                            "type": "path",
                            "points": pts,
                            "width": cls._to_unit(minor),
                        },
                    }
                else:
                    drill_r = cls._to_unit(max(drill_x, drill_y) / 2.0)
                    padstack["hole"] = {
                        "shape": {
                            "type": "circle",
                            "center": [0, 0],
                            "radius": drill_r,
                        },
                    }
        return padstack_id, padstack

    @classmethod
    def _padstack_from_via(
        cls,
        via: Any,
        copper_layer_index: dict[str, int],
        *,
        provider_strict: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        size = float(getattr(via, "size", 0.0) or 0.0)
        drill = float(getattr(via, "drill", 0.0) or 0.0)
        layers = cls._layer_indices(getattr(via, "layers", []), copper_layer_index)
        via_id = cls._via_definition_id(via, provider_strict=provider_strict)
        radius = cls._to_unit(size / 2.0)
        shape = {"type": "circle", "center": [0, 0], "radius": radius}
        padstack: dict[str, Any] = {
            "id": via_id,
            "shape": shape,
            "layers": layers,
            "allowVia": False if provider_strict else True,
        }
        if provider_strict:
            # DeepPCB format requires hole + pads for via padstacks.
            # hole uses drill radius; pads use outer pad radius.
            drill_radius = cls._to_unit(drill / 2.0) if drill else radius
            padstack["pads"] = [
                {
                    "shape": {"type": "circle", "center": [0, 0], "radius": radius},
                    "layerFrom": layers[0] if layers else 0,
                    "layerTo": layers[-1] if layers else 1,
                }
            ]
            padstack["hole"] = {
                "shape": {"type": "circle", "center": [0, 0], "radius": drill_radius},
            }
        else:
            padstack["drill"] = cls._to_unit(drill / 2.0)
        return via_id, padstack

    @classmethod
    def _via_definition_id(cls, via: Any, *, provider_strict: bool = False) -> str:
        size_mm = float(getattr(via, "size", 0.0) or 0.0)
        drill_mm = float(getattr(via, "drill", 0.0) or 0.0)
        if provider_strict:
            layers = list(getattr(via, "layers", []) or ["F.Cu", "B.Cu"])
            layer_suffix = "0-1" if len(layers) > 1 else "0"
            return f"Via[{layer_suffix}]_{size_mm:.4g}:{drill_mm:.4g}mm"
        size = cls._to_unit(size_mm)
        drill = cls._to_unit(drill_mm)
        return f"Via_{size}:{drill}"

    @staticmethod
    def _definition_id(fp: Any, *, provider_strict: bool = False) -> str:
        if provider_strict:
            return f"{fp.name}__{'BACK' if str(fp.layer).startswith('B.') else 'FRONT'}"
        side = "BACK" if str(fp.layer).startswith("B.") else "FRONT"
        return f"{fp.name}__{side}__{fp.uuid}"

    @staticmethod
    def _component_id(fp: Any, *, provider_strict: bool = False) -> str:
        ref = Property.try_get_property(fp.propertys, "Reference")
        component_ref = str(ref).strip() if isinstance(ref, str) else ""
        if not component_ref:
            component_ref = str(fp.uuid)
        if provider_strict:
            atopile_address = Property.try_get_property(fp.propertys, "atopile_address")
            if isinstance(atopile_address, str) and atopile_address.strip():
                return f"{component_ref}@@{atopile_address.strip()}"
        return component_ref

    @staticmethod
    def _decode_component_id(component_id: str) -> tuple[str, str | None]:
        if "@@" not in component_id:
            return component_id, None
        ref, _, addr = component_id.partition("@@")
        ref = ref.strip() or component_id
        addr = addr.strip()
        return ref, (addr or None)

    @classmethod
    def _component_properties(
        cls,
        *,
        ref_value: str,
        ref_point: list[Any],
        ref_rotation: float | None,
        ref_unlocked: Any,
        ref_layer: str,
        ref_hide: Any,
        effects: Any,
        resolution: int,
        atopile_address: str | None,
    ) -> list[Any]:
        properties = [
            kicad.pcb.Property(
                name="Reference",
                value=ref_value,
                at=kicad.pcb.Xyr(
                    x=cls._from_unit(float(ref_point[0]), resolution),
                    y=cls._from_unit(float(ref_point[1]), resolution),
                    r=ref_rotation,
                ),
                unlocked=ref_unlocked,
                layer=ref_layer,
                hide=ref_hide,
                uuid=kicad.gen_uuid(),
                effects=effects,
            )
        ]
        if atopile_address:
            properties.append(
                kicad.pcb.Property(
                    name="atopile_address",
                    value=atopile_address,
                    at=kicad.pcb.Xyr(x=0.0, y=0.0, r=0.0),
                    unlocked=True,
                    layer="F.Fab",
                    hide=True,
                    uuid=kicad.gen_uuid(),
                    effects=None,
                )
            )
        return properties

    @staticmethod
    def _pin_id(pad: Any, index: int, *, provider_strict: bool = False) -> str:
        raw = str(getattr(pad, "name", "") or "").strip()
        if raw:
            if provider_strict and len(raw) < 2:
                return f"P{raw}"
            return raw
        if not provider_strict:
            return ""
        return f"PAD_{index + 1}"

    @classmethod
    def _footprint_outline(cls, fp: Any) -> dict[str, Any]:
        shapes: list[dict[str, Any]] = []

        for line in getattr(fp, "fp_lines", []):
            shapes.append(
                {
                    "type": "polyline",
                    "layer": line.layer,
                    "strokeWidth": float(line.stroke.width) if line.stroke else None,
                    "strokeType": str(line.stroke.type) if line.stroke else None,
                    "fill": line.fill,
                    "locked": line.locked,
                    "points": [
                        cls._xy_to_point(line.start),
                        cls._xy_to_point(line.end),
                    ],
                }
            )

        for circle in getattr(fp, "fp_circles", []):
            radius = (
                (float(circle.end.x) - float(circle.center.x)) ** 2
                + (float(circle.end.y) - float(circle.center.y)) ** 2
            ) ** 0.5
            shapes.append(
                {
                    "type": "circle",
                    "layer": circle.layer,
                    "strokeWidth": float(circle.stroke.width)
                    if circle.stroke
                    else None,
                    "strokeType": str(circle.stroke.type) if circle.stroke else None,
                    "fill": circle.fill,
                    "locked": circle.locked,
                    "center": cls._xy_to_point(circle.center),
                    "radius": cls._to_unit(radius),
                }
            )

        for arc in getattr(fp, "fp_arcs", []):
            shapes.append(
                {
                    "type": "polyline",
                    "layer": arc.layer,
                    "strokeWidth": float(arc.stroke.width) if arc.stroke else None,
                    "strokeType": str(arc.stroke.type) if arc.stroke else None,
                    "fill": arc.fill,
                    "locked": arc.locked,
                    "points": [
                        cls._xy_to_point(arc.start),
                        cls._xy_to_point(arc.mid),
                        cls._xy_to_point(arc.end),
                    ],
                }
            )

        for poly in getattr(fp, "fp_poly", []):
            points = [cls._xy_to_point(xy) for xy in poly.pts.xys]
            shapes.append(
                {
                    "type": "polyline",
                    "layer": poly.layer,
                    "strokeWidth": float(poly.stroke.width) if poly.stroke else None,
                    "strokeType": str(poly.stroke.type) if poly.stroke else None,
                    "fill": poly.fill,
                    "locked": poly.locked,
                    "points": points,
                }
            )

        return {"type": "multi", "shapes": shapes}

    @classmethod
    def _edge_cuts_points(cls, pcb: Any) -> list[list[int]]:
        """Build an ordered polyline from Edge.Cuts geometry.

        Collects lines and arcs, chains them end-to-end, and samples
        arcs into polyline segments so the boundary is a proper polygon.
        """
        import math

        # Collect segments as (start_pt, end_pt, interior_pts) tuples.
        # interior_pts are extra points along arcs.
        segments: list[tuple[list[int], list[int], list[list[int]]]] = []

        for line in getattr(pcb, "gr_lines", []):
            if str(getattr(line, "layer", "")) != "Edge.Cuts":
                continue
            segments.append(
                (cls._xy_to_point(line.start), cls._xy_to_point(line.end), [])
            )

        for arc in getattr(pcb, "gr_arcs", []):
            if str(getattr(arc, "layer", "")) != "Edge.Cuts":
                continue
            # Compute arc center from start, mid, end using circumcircle.
            sx, sy = float(arc.start.x), float(arc.start.y)
            mx, my = float(arc.mid.x), float(arc.mid.y)
            ex, ey = float(arc.end.x), float(arc.end.y)

            arc_pts: list[list[int]] = []
            D = 2.0 * (sx * (my - ey) + mx * (ey - sy) + ex * (sy - my))
            if abs(D) > 1e-9:
                cx = (
                    (sx**2 + sy**2) * (my - ey)
                    + (mx**2 + my**2) * (ey - sy)
                    + (ex**2 + ey**2) * (sy - my)
                ) / D
                cy = (
                    (sx**2 + sy**2) * (ex - mx)
                    + (mx**2 + my**2) * (sx - ex)
                    + (ex**2 + ey**2) * (mx - sx)
                ) / D
                r = math.hypot(sx - cx, sy - cy)
                a_start = math.atan2(sy - cy, sx - cx)
                a_mid = math.atan2(my - cy, mx - cx)
                a_end = math.atan2(ey - cy, ex - cx)

                # Determine sweep direction via the mid-point.
                def _norm(a: float) -> float:
                    return a % (2.0 * math.pi)

                ccw_sweep = (_norm(a_end - a_start)) % (2.0 * math.pi)
                cw_sweep = (2.0 * math.pi - ccw_sweep) % (2.0 * math.pi)
                mid_ccw = (_norm(a_mid - a_start)) % (2.0 * math.pi)
                if mid_ccw <= ccw_sweep:
                    sweep = ccw_sweep
                    direction = 1.0
                else:
                    sweep = cw_sweep
                    direction = -1.0
                # Sample arc into ~16 segments per full circle.
                n_samples = max(4, int(abs(sweep) / (2.0 * math.pi) * 16))
                for i in range(1, n_samples):
                    t = a_start + direction * sweep * i / n_samples
                    px = cx + r * math.cos(t)
                    py = cy + r * math.sin(t)
                    arc_pts.append(cls._xy_to_point_raw(px, py))
            else:
                # Degenerate arc (collinear points) — just use midpoint.
                arc_pts.append(cls._xy_to_point(arc.mid))

            segments.append(
                (cls._xy_to_point(arc.start), cls._xy_to_point(arc.end), arc_pts)
            )

        for poly in getattr(pcb, "gr_polys", []):
            if str(getattr(poly, "layer", "")) != "Edge.Cuts":
                continue
            poly_pts = [cls._xy_to_point(xy) for xy in poly.pts.xys]
            for i in range(len(poly_pts) - 1):
                segments.append((poly_pts[i], poly_pts[i + 1], []))
            if len(poly_pts) > 1:
                segments.append((poly_pts[-1], poly_pts[0], []))

        if not segments:
            return []

        # Chain segments end-to-end to form an ordered polygon.
        EPS = cls._to_unit(0.01)  # 0.01mm tolerance

        def _close(a: list[int], b: list[int]) -> bool:
            return abs(a[0] - b[0]) <= EPS and abs(a[1] - b[1]) <= EPS

        ordered: list[list[int]] = []
        remaining = list(segments)
        # Start with first segment.
        seg = remaining.pop(0)
        ordered.append(seg[0])
        ordered.extend(seg[2])
        ordered.append(seg[1])

        while remaining:
            tail = ordered[-1]
            found = False
            for i, seg in enumerate(remaining):
                if _close(tail, seg[0]):
                    remaining.pop(i)
                    ordered.extend(seg[2])
                    ordered.append(seg[1])
                    found = True
                    break
                if _close(tail, seg[1]):
                    # Reverse this segment.
                    remaining.pop(i)
                    ordered.extend(reversed(seg[2]))
                    ordered.append(seg[0])
                    found = True
                    break
            if not found:
                # Disconnected — append remaining segments as-is.
                seg = remaining.pop(0)
                ordered.append(seg[0])
                ordered.extend(seg[2])
                ordered.append(seg[1])

        # Close the polygon.
        if ordered and not _close(ordered[0], ordered[-1]):
            ordered.append(ordered[0])
        return ordered

    @classmethod
    def _xy_to_point_raw(cls, x: float, y: float) -> list[int]:
        return [cls._to_unit(x), cls._to_unit(y)]

    @classmethod
    def _edge_cuts_segments(cls, pcb: Any) -> list[dict[str, Any]]:
        segments: list[dict[str, Any]] = []
        for line in getattr(pcb, "gr_lines", []):
            if str(getattr(line, "layer", "")) != "Edge.Cuts":
                continue
            stroke = getattr(line, "stroke", None)
            segments.append(
                {
                    "type": "line",
                    "start": cls._xy_to_point(line.start),
                    "end": cls._xy_to_point(line.end),
                    "strokeWidth": float(getattr(stroke, "width", 0.2) or 0.2),
                    "strokeType": str(getattr(stroke, "type", "default") or "default"),
                    "fill": getattr(line, "fill", None),
                    "locked": getattr(line, "locked", None),
                }
            )
        return segments

    @classmethod
    def _normalize_provider_board(cls, board: C_deeppcb_board_file) -> None:
        # Match converter defaults/shape used by DeepPCB convert-to-json.
        board.rules = [
            {"subjects": [], "type": "rotateFirst", "value": False},
            {"subjects": [], "type": "allowViaAtSmd", "value": False},
            {"subjects": [], "type": "pinConnectionPoint", "value": "centroid"},
        ]
        board.resolution = {"unit": "mm", "value": 1000}
        board.unknown["metaData"] = {}
        board.unknown["ratsnest"] = []
        board.metadata = {}
        if isinstance(board.boundary, dict):
            board.boundary["clearance"] = 200
            board.boundary.pop("segments", None)

        board.layers = [
            {
                "id": str(layer.get("id", "")),
                "type": str(layer.get("type", "signal")),
                "keepouts": list(layer.get("keepouts", [])),
            }
            for layer in board.layers
            if str(layer.get("id", "")).endswith(".Cu")
        ]

        board.nets = [
            {"id": str(net.get("id", "")), "pins": list(net.get("pins", []))}
            for net in board.nets
            if str(net.get("id", "")) != "0"
        ]
        board.netClasses = [
            {
                "id": "__default__",
                "trackWidth": 200,
                "clearance": 200,
                "viaDefinition": (
                    board.viaDefinitions[0]
                    if board.viaDefinitions
                    else "Via[0-1]_0.6:0.3mm"
                ),
                "nets": [str(net.get("id", "")) for net in board.nets],
            }
        ]
        if not board.viaDefinitions:
            board.viaDefinitions = ["Via[0-1]_0.6:0.3mm"]
        board.planes = [
            {
                "layer": int(plane.get("layer", 0)),
                "netId": str(plane.get("netId", "")),
                "shape": plane.get("shape", {}),
            }
            for plane in board.planes
        ]

        for comp in board.components:
            comp.pop("embeddedFonts", None)
            # Provider canonical output does not include component reference property.
            comp.pop("referenceProperty", None)

        # Strip non-DeepPCB fields from outline shapes in component definitions.
        _extra_shape_keys = {"layer", "strokeWidth", "strokeType", "fill", "locked"}
        for defn in board.componentDefinitions:
            outline = defn.get("outline")
            if isinstance(outline, dict):
                shapes = (
                    outline.get("shapes", [])
                    if outline.get("type") == "multi"
                    else [outline]
                )
                for shape in shapes:
                    if isinstance(shape, dict):
                        for k in _extra_shape_keys:
                            shape.pop(k, None)

        via_def_ids = set(board.viaDefinitions) if board.viaDefinitions else set()
        for padstack in board.padstacks:
            padstack["allowVia"] = str(padstack.get("id", "")) in via_def_ids
            # Internal reconstruction hints are non-canonical for provider JSON.
            for key in list(padstack.keys()):
                if key.startswith("kicad"):
                    padstack.pop(key, None)

        # Strip null/non-canonical fields from vias.
        for via in board.vias:
            for key in list(via.keys()):
                if via[key] is None:
                    via.pop(key)

        cls._provider_scale_flip_coordinates(board)

    @classmethod
    def _provider_scale_flip_coordinates(cls, board: C_deeppcb_board_file) -> None:
        # Internal export uses 1e6 units; provider converter uses 1e3 and Y-down.
        def pxy(point: Any) -> Any:
            if not (isinstance(point, list) and len(point) >= 2):
                return point
            x = int(round(float(point[0]) / 1000.0))
            y = -int(round(float(point[1]) / 1000.0))
            return [x, y]

        def points_in_shape(shape: Any) -> None:
            if not isinstance(shape, dict):
                return
            pts = shape.get("points")
            if isinstance(pts, list):
                shape["points"] = [pxy(p) for p in pts]
            center = shape.get("center")
            if isinstance(center, list):
                shape["center"] = pxy(center)
            if isinstance(shape.get("radius"), (int, float)):
                shape["radius"] = int(round(float(shape["radius"]) / 1000.0))
            if isinstance(shape.get("width"), (int, float)):
                shape["width"] = int(round(float(shape["width"]) / 1000.0))
            lower_left = shape.get("lowerLeft")
            upper_right = shape.get("upperRight")
            if isinstance(lower_left, list) and isinstance(upper_right, list):
                ll = pxy(lower_left)
                ur = pxy(upper_right)
                # Y-flip can swap lowerLeft/upperRight; normalise so ll.y < ur.y
                shape["lowerLeft"] = [min(ll[0], ur[0]), min(ll[1], ur[1])]
                shape["upperRight"] = [max(ll[0], ur[0]), max(ll[1], ur[1])]
            elif isinstance(lower_left, list):
                shape["lowerLeft"] = pxy(lower_left)
            elif isinstance(upper_right, list):
                shape["upperRight"] = pxy(upper_right)

        boundary = board.boundary if isinstance(board.boundary, dict) else {}
        bshape = boundary.get("shape")
        if isinstance(bshape, dict):
            points_in_shape(bshape)
        segs = boundary.get("segments")
        if isinstance(segs, list):
            for seg in segs:
                if not isinstance(seg, dict):
                    continue
                if isinstance(seg.get("start"), list):
                    seg["start"] = pxy(seg["start"])
                if isinstance(seg.get("end"), list):
                    seg["end"] = pxy(seg["end"])

        for padstack in board.padstacks:
            points_in_shape(padstack.get("shape"))
            if isinstance(padstack.get("drill"), (int, float)):
                padstack["drill"] = int(round(float(padstack["drill"]) / 1000.0))
            # Scale nested hole/pads shapes (used by via padstacks)
            hole = padstack.get("hole")
            if isinstance(hole, dict):
                points_in_shape(hole.get("shape"))
            for pad_entry in padstack.get("pads", []):
                if isinstance(pad_entry, dict):
                    points_in_shape(pad_entry.get("shape"))

        for definition in board.componentDefinitions:
            for pin in definition.get("pins", []):
                if isinstance(pin, dict) and isinstance(pin.get("position"), list):
                    pin["position"] = pxy(pin["position"])
            outline = definition.get("outline")
            if isinstance(outline, dict):
                if outline.get("type") == "multi":
                    for shape in outline.get("shapes", []):
                        points_in_shape(shape)
                else:
                    points_in_shape(outline)

        for comp in board.components:
            if isinstance(comp.get("position"), list):
                comp["position"] = pxy(comp["position"])
            rp = comp.get("referenceProperty")
            if isinstance(rp, dict) and isinstance(rp.get("at"), list):
                rp["at"] = pxy(rp["at"])

        for wire in board.wires:
            if isinstance(wire.get("start"), list):
                wire["start"] = pxy(wire["start"])
            if isinstance(wire.get("end"), list):
                wire["end"] = pxy(wire["end"])
            if isinstance(wire.get("width"), (int, float)):
                wire["width"] = int(round(float(wire["width"]) / 1000.0))

        for via in board.vias:
            if isinstance(via.get("position"), list):
                via["position"] = pxy(via["position"])

        for plane in board.planes:
            shape = plane.get("shape")
            if isinstance(shape, dict):
                # polygonWithHoles uses "outline" and "holes" instead of "points"
                outline = shape.get("outline")
                if isinstance(outline, list):
                    shape["outline"] = [pxy(p) for p in outline]
                holes = shape.get("holes")
                if isinstance(holes, list):
                    shape["holes"] = [
                        [pxy(p) for p in hole] if isinstance(hole, list) else hole
                        for hole in holes
                    ]
                points_in_shape(shape)

    @classmethod
    def _reverse_provider_coordinates(cls, board: C_deeppcb_board_file) -> None:
        """Reverse the provider scale+flip applied by _provider_scale_flip_coordinates.

        Converts resolution-1000 / Y-negated provider data back to resolution-1e6
        / Y-as-is internal representation so that to_internal_pcb can process it.
        """

        def pxy(point: Any) -> Any:
            if not (isinstance(point, list) and len(point) >= 2):
                return point
            return [
                int(round(float(point[0]) * 1000.0)),
                -int(round(float(point[1]) * 1000.0)),
            ]

        def scale_scalar(v: Any) -> Any:
            if isinstance(v, (int, float)):
                return int(round(float(v) * 1000.0))
            return v

        def points_in_shape(shape: Any) -> None:
            if not isinstance(shape, dict):
                return
            pts = shape.get("points")
            if isinstance(pts, list):
                shape["points"] = [pxy(p) for p in pts]
            center = shape.get("center")
            if isinstance(center, list):
                shape["center"] = pxy(center)
            if isinstance(shape.get("radius"), (int, float)):
                shape["radius"] = scale_scalar(shape["radius"])
            if isinstance(shape.get("width"), (int, float)):
                shape["width"] = scale_scalar(shape["width"])
            lower_left = shape.get("lowerLeft")
            upper_right = shape.get("upperRight")
            if isinstance(lower_left, list) and isinstance(upper_right, list):
                ll = pxy(lower_left)
                ur = pxy(upper_right)
                shape["lowerLeft"] = [min(ll[0], ur[0]), min(ll[1], ur[1])]
                shape["upperRight"] = [max(ll[0], ur[0]), max(ll[1], ur[1])]

        # Boundary
        boundary = board.boundary if isinstance(board.boundary, dict) else {}
        bshape = boundary.get("shape")
        if isinstance(bshape, dict):
            points_in_shape(bshape)
        segs = boundary.get("segments")
        if isinstance(segs, list):
            for seg in segs:
                if isinstance(seg, dict):
                    if isinstance(seg.get("start"), list):
                        seg["start"] = pxy(seg["start"])
                    if isinstance(seg.get("end"), list):
                        seg["end"] = pxy(seg["end"])

        # Padstacks
        for padstack in board.padstacks:
            points_in_shape(padstack.get("shape"))
            if isinstance(padstack.get("drill"), (int, float)):
                padstack["drill"] = scale_scalar(padstack["drill"])
            hole = padstack.get("hole")
            if isinstance(hole, dict):
                points_in_shape(hole.get("shape"))
            for pad_entry in padstack.get("pads", []):
                if isinstance(pad_entry, dict):
                    points_in_shape(pad_entry.get("shape"))

        # Component definitions
        for definition in board.componentDefinitions:
            for pin in definition.get("pins", []):
                if isinstance(pin, dict) and isinstance(pin.get("position"), list):
                    pin["position"] = pxy(pin["position"])
            outline = definition.get("outline")
            if isinstance(outline, dict):
                if outline.get("type") == "multi":
                    for shape in outline.get("shapes", []):
                        points_in_shape(shape)
                else:
                    points_in_shape(outline)

        # Components
        for comp in board.components:
            if isinstance(comp.get("position"), list):
                comp["position"] = pxy(comp["position"])

        # Wires
        for wire in board.wires:
            if isinstance(wire.get("start"), list):
                wire["start"] = pxy(wire["start"])
            if isinstance(wire.get("end"), list):
                wire["end"] = pxy(wire["end"])
            if isinstance(wire.get("width"), (int, float)):
                wire["width"] = scale_scalar(wire["width"])

        # Vias
        for via in board.vias:
            if isinstance(via.get("position"), list):
                via["position"] = pxy(via["position"])

        # Planes
        for plane in board.planes:
            shape = plane.get("shape")
            if isinstance(shape, dict):
                outline = shape.get("outline")
                if isinstance(outline, list):
                    shape["outline"] = [pxy(p) for p in outline]
                holes = shape.get("holes")
                if isinstance(holes, list):
                    shape["holes"] = [
                        [pxy(p) for p in h] if isinstance(h, list) else h for h in holes
                    ]
                points_in_shape(shape)

        # Update resolution to internal value
        board.resolution = {"unit": "mm", "value": 1000000}

    # ── Reuse block support ─────────────────────────────────────────────

    @staticmethod
    def _pad_absolute_position(fp: Any, pad: Any) -> tuple[float, float]:
        """Compute the absolute board position of a pad (accounting for fp rotation)."""
        fp_x = float(fp.at.x)
        fp_y = float(fp.at.y)
        fp_r = float(getattr(fp.at, "r", 0.0) or 0.0)

        pad_x = float(pad.at.x)
        pad_y = float(pad.at.y)

        if fp_r:
            angle = math.radians(-fp_r)
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            pad_x, pad_y = (
                pad_x * cos_a - pad_y * sin_a,
                pad_x * sin_a + pad_y * cos_a,
            )

        return fp_x + pad_x, fp_y + pad_y

    @classmethod
    def _collapse_reuse_blocks(
        cls,
        pcb: Any,
        project_root: Path,
        *,
        copper_layer_index: dict[str, int],
        net_id_by_number: dict[int, str],
        provider_strict: bool = False,
    ) -> dict[str, Any] | None:
        """Collapse reuse blocks into synthetic components.

        Scans footprints for ``atopile_subaddresses``, groups them by reuse
        block, classifies nets as internal/external, and produces synthetic
        deeppcb component definitions + instances that represent each block
        as a single placeable unit.

        Returns ``None`` when no reuse blocks are found.
        """
        # Step 1 – Parse sub-addresses and group footprints ───────────
        sub_pcb_cache: dict[str, Any] = {}
        fp_to_group: dict[str, str] = {}
        fp_to_sub_addr: dict[
            str, tuple[str, str]
        ] = {}  # uuid -> (pcb_addr, module_addr)
        groups: dict[str, list[Any]] = {}  # group_name -> [fp, ...]

        for fp in pcb.footprints:
            raw = Property.try_get_property(fp.propertys, "atopile_subaddresses")
            if not raw:
                continue

            sub_entries: list[tuple[str, str]] = []
            for addr_str in raw.removeprefix("[").removesuffix("]").split(", "):
                addr_str = addr_str.strip()
                if not addr_str or ":" not in addr_str:
                    continue
                pcb_addr, module_addr = addr_str.split(":", 1)
                sub_entries.append((pcb_addr, module_addr))

            if not sub_entries:
                continue

            # Load sub-PCBs into cache
            loaded: dict[tuple[str, str], Any] = {}
            for pcb_addr, module_addr in sub_entries:
                if pcb_addr not in sub_pcb_cache:
                    path = project_root / pcb_addr
                    if not path.exists():
                        continue
                    try:
                        sub_pcb_cache[pcb_addr] = kicad.loads(
                            kicad.pcb.PcbFile, path
                        ).kicad_pcb
                    except Exception:
                        log.debug("Failed to load sub-PCB %s", pcb_addr)
                        continue
                if pcb_addr in sub_pcb_cache:
                    loaded[(pcb_addr, module_addr)] = sub_pcb_cache[pcb_addr]

            if not loaded:
                continue

            # Prefer sub-PCBs with tracks, then higher-level modules
            candidates = loaded
            if any(sub.segments for sub in candidates.values()):
                candidates = {k: v for k, v in loaded.items() if v.segments}
            chosen_key = max(
                candidates,
                key=lambda k: len(k[1].split(".")),
            )
            chosen_pcb_addr, chosen_module_addr = chosen_key

            ato_addr = Property.try_get_property(fp.propertys, "atopile_address")
            if not ato_addr:
                continue

            suffix = "." + chosen_module_addr
            if not ato_addr.endswith(suffix):
                continue
            group_name = ato_addr[: -len(suffix)]

            fp_to_group[fp.uuid] = group_name
            fp_to_sub_addr[fp.uuid] = (chosen_pcb_addr, chosen_module_addr)
            groups.setdefault(group_name, []).append(fp)

        if not groups:
            return None

        # Step 2 – Classify nets ──────────────────────────────────────
        grouped_fp_uuids: set[str] = set(fp_to_group.keys())

        # For each net, track connections inside/outside each group.
        net_group_membership: dict[int, set[str]] = {}
        net_has_ungrouped: set[int] = set()

        for fp in pcb.footprints:
            group = fp_to_group.get(fp.uuid)
            for pad in fp.pads:
                if pad.net is None:
                    continue
                net_num = int(getattr(pad.net, "number", 0) or 0)
                if net_num == 0:
                    continue
                if group is not None:
                    net_group_membership.setdefault(net_num, set()).add(group)
                else:
                    net_has_ungrouped.add(net_num)

        # Step 3 – Build synthetic components per group ───────────────
        all_internal_nets: set[int] = set()
        definitions: dict[str, dict[str, Any]] = {}
        synthetic_components: list[dict[str, Any]] = []
        synthetic_padstacks: dict[str, dict[str, Any]] = {}
        synthetic_pins_by_net: dict[str, list[str]] = {}
        metadata: dict[str, Any] = {}

        for group_name, group_fps in groups.items():
            pcb_addr = fp_to_sub_addr[group_fps[0].uuid][0]
            sub_pcb = sub_pcb_cache[pcb_addr]

            # Classify nets for this group
            group_internal_nets: set[int] = set()
            group_external_nets: set[int] = set()
            for net_num, groups_set in net_group_membership.items():
                if group_name not in groups_set:
                    continue
                if groups_set == {group_name} and net_num not in net_has_ungrouped:
                    group_internal_nets.add(net_num)
                else:
                    group_external_nets.add(net_num)
            all_internal_nets |= group_internal_nets

            # Anchor footprint (largest by pad count)
            anchor_fp = max(group_fps, key=lambda fp: len(fp.pads))
            anchor_x = float(anchor_fp.at.x)
            anchor_y = float(anchor_fp.at.y)

            definition_id = f"REUSE_BLOCK__{group_name}"
            component_id = f"REUSE_BLK@@__block__.{group_name}"

            # Build synthetic pins from ALL pads (for collision geometry)
            # but only add net references for external-net pads.
            synthetic_pins: list[dict[str, Any]] = []
            external_pin_map: dict[str, dict[str, Any]] = {}
            pin_counter = 0

            for fp in group_fps:
                orig_component_id = cls._component_id(
                    fp, provider_strict=provider_strict
                )
                for pad_index, pad in enumerate(fp.pads):
                    pin_counter += 1
                    pin_id = f"EP{pin_counter}"

                    abs_x, abs_y = cls._pad_absolute_position(fp, pad)
                    pin_x = cls._to_unit(abs_x - anchor_x)
                    pin_y = cls._to_unit(abs_y - anchor_y)

                    padstack_id, padstack_data = cls._padstack_from_pad(
                        pad,
                        copper_layer_index,
                        provider_strict=provider_strict,
                        strict_scope=definition_id if provider_strict else None,
                    )
                    synthetic_padstacks.setdefault(padstack_id, padstack_data)

                    orig_pin_id = cls._pin_id(
                        pad, pad_index, provider_strict=provider_strict
                    )

                    synthetic_pins.append(
                        {
                            "id": pin_id,
                            "padstack": padstack_id,
                            "position": [pin_x, pin_y],
                            "rotation": cls._export_rotation(
                                getattr(pad.at, "r", None),
                                provider_strict=provider_strict,
                            ),
                        }
                    )

                    # Only add net references for pads with external nets.
                    net_num = int(getattr(pad.net, "number", 0) or 0) if pad.net else 0
                    is_external = net_num in group_external_nets and net_num != 0
                    is_internal = net_num in group_internal_nets and net_num != 0
                    if is_external or is_internal:
                        net_id = net_id_by_number.get(net_num)
                        if net_id:
                            synthetic_pins_by_net.setdefault(net_id, []).append(
                                f"{component_id}-{pin_id}"
                            )

                    external_pin_map[pin_id] = {
                        "component_id": orig_component_id,
                        "pin_id": orig_pin_id,
                        "net_number": net_num if is_external else 0,
                    }

            # Bounding-box outline
            all_x = [float(fp.at.x) for fp in group_fps]
            all_y = [float(fp.at.y) for fp in group_fps]
            margin = 2.0
            outline = {
                "type": "polyline",
                "points": [
                    [
                        cls._to_unit(min(all_x) - anchor_x - margin),
                        cls._to_unit(min(all_y) - anchor_y - margin),
                    ],
                    [
                        cls._to_unit(max(all_x) - anchor_x + margin),
                        cls._to_unit(min(all_y) - anchor_y - margin),
                    ],
                    [
                        cls._to_unit(max(all_x) - anchor_x + margin),
                        cls._to_unit(max(all_y) - anchor_y + margin),
                    ],
                    [
                        cls._to_unit(min(all_x) - anchor_x - margin),
                        cls._to_unit(max(all_y) - anchor_y + margin),
                    ],
                    [
                        cls._to_unit(min(all_x) - anchor_x - margin),
                        cls._to_unit(min(all_y) - anchor_y - margin),
                    ],
                ],
            }

            definitions[definition_id] = {
                "id": definition_id,
                "outline": outline,
                "pins": synthetic_pins,
                "keepouts": [],
            }

            synthetic_components.append(
                {
                    "id": component_id,
                    "definition": definition_id,
                    "position": [cls._to_unit(anchor_x), cls._to_unit(anchor_y)],
                    "rotation": cls._export_rotation(
                        getattr(anchor_fp.at, "r", None),
                        provider_strict=provider_strict,
                    ),
                    "side": (
                        "BACK" if str(anchor_fp.layer).startswith("B.") else "FRONT"
                    ),
                    "partNumber": f"REUSE_BLOCK:{group_name}",
                    "protected": True,
                }
            )

            # Address map: module_address → parent atopile_address
            addr_map: dict[str, str] = {}
            for fp in group_fps:
                ato_addr = Property.try_get_property(fp.propertys, "atopile_address")
                _, module_addr = fp_to_sub_addr[fp.uuid]
                if ato_addr:
                    addr_map[module_addr] = ato_addr

            # Net map: sub-PCB net name → parent net name
            sub_net_map = cls._build_sub_net_map(
                sub_pcb, pcb, addr_map, group_external_nets
            )

            _, anchor_module_addr = fp_to_sub_addr.get(anchor_fp.uuid, (None, None))
            # Look up anchor position in the sub-PCB.
            sub_anchor_x, sub_anchor_y = 0.0, 0.0
            if anchor_module_addr:
                for sfp in sub_pcb.footprints:
                    saddr = Property.try_get_property(sfp.propertys, "atopile_address")
                    if saddr == anchor_module_addr:
                        sub_anchor_x = float(sfp.at.x)
                        sub_anchor_y = float(sfp.at.y)
                        break

            metadata[group_name] = {
                "group_name": group_name,
                "component_id": component_id,
                "definition_id": definition_id,
                "pcb_address": pcb_addr,
                "anchor_position": [
                    cls._to_unit(anchor_x),
                    cls._to_unit(anchor_y),
                ],
                "sub_anchor_position": [
                    cls._to_unit(sub_anchor_x),
                    cls._to_unit(sub_anchor_y),
                ],
                "footprint_addr_map": addr_map,
                "external_pin_map": external_pin_map,
                "internal_net_ids": [
                    net_id_by_number.get(n, str(n)) for n in group_internal_nets
                ],
                "sub_net_map": sub_net_map,
            }

        # Step 4 – Preserve padstacks from ALL pads of collapsed footprints.
        # The loop above only collects padstacks for external (exported) pins.
        # Internal pads (e.g. USB connector through-hole pins that are only
        # connected within the reuse block) also contribute padstack definitions
        # that the DeepPCB API may reference internally (e.g. for via templates).
        # Without these, the API silently rejects the board during ingestion.
        for group_fps in groups.values():
            for fp in group_fps:
                scope = (
                    cls._definition_id(fp, provider_strict=provider_strict)
                    if provider_strict
                    else None
                )
                for pad in fp.pads:
                    padstack_id, padstack_data = cls._padstack_from_pad(
                        pad,
                        copper_layer_index,
                        provider_strict=provider_strict,
                        strict_scope=scope,
                    )
                    synthetic_padstacks.setdefault(padstack_id, padstack_data)

        log.info(
            "Collapsed %d reuse block(s): %s",
            len(groups),
            ", ".join(sorted(groups.keys())),
        )

        return {
            "grouped_fp_uuids": grouped_fp_uuids,
            "internal_net_numbers": all_internal_nets,
            "definitions": definitions,
            "components": synthetic_components,
            "padstacks": synthetic_padstacks,
            "pins_by_net": synthetic_pins_by_net,
            "metadata": metadata,
        }

    @classmethod
    def _build_sub_net_map(
        cls,
        sub_pcb: Any,
        parent_pcb: Any,
        addr_map: dict[str, str],
        external_net_numbers: set[int],
    ) -> dict[str, str]:
        """Build mapping from sub-PCB net names → parent net names.

        Matches footprints by address, then pads by name, to discover
        which sub-PCB net corresponds to which parent net.
        """
        net_map: dict[str, str] = {}

        sub_fps: dict[str, Any] = {}
        for fp in sub_pcb.footprints:
            addr = Property.try_get_property(fp.propertys, "atopile_address")
            if addr:
                sub_fps[addr] = fp

        parent_fps: dict[str, Any] = {}
        for fp in parent_pcb.footprints:
            addr = Property.try_get_property(fp.propertys, "atopile_address")
            if addr:
                parent_fps[addr] = fp

        for sub_addr, parent_addr in addr_map.items():
            sub_fp = sub_fps.get(sub_addr)
            parent_fp = parent_fps.get(parent_addr)
            if not sub_fp or not parent_fp:
                continue

            for sub_pad in sub_fp.pads:
                if not sub_pad.net or not sub_pad.net.name:
                    continue
                for p_pad in parent_fp.pads:
                    if p_pad.name != sub_pad.name:
                        continue
                    if not p_pad.net or not p_pad.net.name:
                        continue
                    p_net_num = int(getattr(p_pad.net, "number", 0) or 0)
                    if p_net_num in external_net_numbers:
                        net_map[sub_pad.net.name] = p_pad.net.name
                    break

        return net_map

    @classmethod
    def expand_reuse_blocks(
        cls,
        pcb: Any,
        metadata: dict[str, Any],
        project_root: Path,
    ) -> None:
        """Expand synthetic reuse-block footprints back into real components.

        After DeepPCB places the synthetic block at a new position, this
        method loads the sub-PCB, applies the position offset, remaps nets,
        and inserts the real footprints + routing into *pcb*.

        Modifies *pcb* in-place.
        """
        if not metadata:
            return

        # Index metadata by partNumber → group_name
        blocks_by_group: dict[str, dict[str, Any]] = {}
        for group_name, block_info in metadata.items():
            blocks_by_group[group_name] = block_info

        # Find synthetic footprints
        synthetic_fps: list[Any] = []
        for fp in pcb.footprints:
            if str(fp.name).startswith("REUSE_BLOCK:"):
                synthetic_fps.append(fp)

        if not synthetic_fps:
            return

        # Parent net name → number lookup
        parent_net_numbers: dict[str, int] = {}
        for net in pcb.nets:
            if net.name:
                parent_net_numbers[net.name] = net.number

        # Track the highest net number for creating new internal nets
        max_net_number = max((net.number for net in pcb.nets), default=0)

        for synth_fp in synthetic_fps:
            group_name = str(synth_fp.name).removeprefix("REUSE_BLOCK:")
            block_info = blocks_by_group.get(group_name)
            if block_info is None:
                log.warning(
                    "No metadata for reuse block '%s', skipping expansion",
                    group_name,
                )
                continue

            # Compute offset: map sub-PCB coordinates to parent board.
            # offset = new_parent_position - sub_pcb_anchor_position
            new_x = float(synth_fp.at.x)
            new_y = float(synth_fp.at.y)
            resolution = cls.RESOLUTION_VALUE
            sub_anchor = block_info["sub_anchor_position"]
            sub_ax = float(sub_anchor[0]) / resolution
            sub_ay = float(sub_anchor[1]) / resolution
            offset = kicad.pcb.Xy(x=new_x - sub_ax, y=new_y - sub_ay)

            # Load sub-PCB
            sub_pcb_path = project_root / block_info["pcb_address"]
            try:
                sub_pcb = kicad.loads(kicad.pcb.PcbFile, sub_pcb_path).kicad_pcb
            except Exception:
                log.error("Failed to load sub-PCB %s", sub_pcb_path)
                continue

            sub_net_map: dict[str, str] = block_info.get("sub_net_map", {})
            addr_map: dict[str, str] = block_info.get("footprint_addr_map", {})

            # Build sub-PCB internal net map (name → number in sub-PCB)
            sub_net_names: dict[int, str] = {}
            for net in sub_pcb.nets:
                if net.name:
                    sub_net_names[net.number] = net.name

            # Create parent nets for internal sub-PCB nets and build
            # a full remapping: sub-PCB net name → parent net number
            full_net_remap: dict[str, int] = {}
            for sub_net_name, parent_net_name in sub_net_map.items():
                full_net_remap[sub_net_name] = parent_net_numbers.get(
                    parent_net_name, 0
                )

            # Internal nets: create new nets in parent PCB
            for sub_net_num, sub_net_name in sub_net_names.items():
                if sub_net_name in full_net_remap:
                    continue
                # This is an internal net — create it in the parent
                max_net_number += 1
                internal_name = f"__block_{group_name}__{sub_net_name}"
                pcb.nets.append(
                    kicad.pcb.Net(number=max_net_number, name=internal_name)
                )
                parent_net_numbers[internal_name] = max_net_number
                full_net_remap[sub_net_name] = max_net_number

            # Copy footprints from sub-PCB
            for sub_fp in sub_pcb.footprints:
                sub_addr = Property.try_get_property(
                    sub_fp.propertys, "atopile_address"
                )
                if not sub_addr or sub_addr not in addr_map:
                    continue

                new_fp = kicad.copy(sub_fp)
                new_fp.uuid = kicad.gen_uuid()

                # Update atopile_address to parent address
                parent_addr = addr_map[sub_addr]
                for prop in new_fp.propertys:
                    if str(getattr(prop, "name", "")) == "atopile_address":
                        prop.value = parent_addr
                        break

                # Apply offset
                new_fp.at = kicad.pcb.Xyr(
                    x=float(sub_fp.at.x) + offset.x,
                    y=float(sub_fp.at.y) + offset.y,
                    r=getattr(sub_fp.at, "r", None),
                )

                # Remap nets on pads
                for pad in new_fp.pads:
                    pad.uuid = kicad.gen_uuid()
                    if pad.net and pad.net.name:
                        new_net_num = full_net_remap.get(pad.net.name)
                        if new_net_num is not None:
                            # Find the parent net name
                            parent_name = sub_net_map.get(pad.net.name)
                            if parent_name is None:
                                parent_name = f"__block_{group_name}__{pad.net.name}"
                            pad.net = kicad.pcb.Net(
                                number=new_net_num,
                                name=parent_name,
                            )
                        else:
                            pad.net = None

                pcb.footprints.append(new_fp)

            # Remove board-level internal routing before inserting sub-PCB
            # copies.  During collapse we now preserve internal wires/vias/zones
            # so DeepPCB can see existing copper.  Before expansion we must
            # strip them to avoid duplicates with the sub-PCB routing.
            current_net_by_name: dict[str, int] = {
                net.name: net.number for net in pcb.nets if net.name
            }
            internal_net_ids = set(block_info.get("internal_net_ids", []))
            internal_parent_nets: set[int] = set()
            for net_id in internal_net_ids:
                net_num = current_net_by_name.get(net_id, 0)
                if net_num:
                    internal_parent_nets.add(net_num)

            if internal_parent_nets:
                pcb.segments = [
                    s for s in pcb.segments if s.net not in internal_parent_nets
                ]
                pcb.arcs = [a for a in pcb.arcs if a.net not in internal_parent_nets]
                pcb.vias = [v for v in pcb.vias if v.net not in internal_parent_nets]
                pcb.zones = [
                    z
                    for z in pcb.zones
                    if int(getattr(z, "net", 0) or 0) not in internal_parent_nets
                ]

            # Copy all routing elements (segments, arcs, zones, vias)
            PCB_Transformer, get_all_geos = _lazy_kicad_transformer()
            for track in chain(
                sub_pcb.segments, sub_pcb.arcs, sub_pcb.zones, sub_pcb.vias
            ):
                sub_net_name = sub_net_names.get(track.net, "")
                new_net_num = full_net_remap.get(sub_net_name)
                if new_net_num is None:
                    continue
                new_track = kicad.copy(track)
                new_track.uuid = kicad.gen_uuid()
                new_track.net = new_net_num
                if isinstance(new_track, kicad.pcb.Zone):
                    parent_name = sub_net_map.get(sub_net_name)
                    if parent_name is None:
                        parent_name = f"__block_{group_name}__{sub_net_name}"
                    new_track.net_name = parent_name
                PCB_Transformer.move_object(new_track, offset)

                if isinstance(new_track, kicad.pcb.Segment):
                    pcb.segments.append(new_track)
                elif isinstance(new_track, kicad.pcb.ArcSegment):
                    pcb.arcs.append(new_track)
                elif isinstance(new_track, kicad.pcb.Zone):
                    pcb.zones.append(new_track)
                elif isinstance(new_track, kicad.pcb.Via):
                    pcb.vias.append(new_track)

            # Copy graphics (lines, arcs, polygons, text, images, etc.)
            # get_all_geos already includes gr_lines/arcs/circles/rects/curves/polys.
            # We additionally chain gr_text_boxes, gr_texts, and images.
            _GR_DISPATCH = {
                kicad.pcb.Line: "gr_lines",
                kicad.pcb.Arc: "gr_arcs",
                kicad.pcb.Polygon: "gr_polys",
                kicad.pcb.Circle: "gr_circles",
                kicad.pcb.Rect: "gr_rects",
                kicad.pcb.Curve: "gr_curves",
                kicad.pcb.TextBox: "gr_text_boxes",
                kicad.pcb.Text: "gr_texts",
                kicad.pcb.Image: "images",
            }
            for gr in chain(
                get_all_geos(sub_pcb),
                sub_pcb.gr_text_boxes,
                sub_pcb.gr_texts,
                sub_pcb.images,
            ):
                new_gr = kicad.copy(gr)
                new_gr.uuid = kicad.gen_uuid()
                PCB_Transformer.move_object(new_gr, offset)

                target_attr = _GR_DISPATCH.get(type(new_gr))
                if target_attr is not None:
                    getattr(pcb, target_attr).append(new_gr)

            # Remove synthetic footprint
            pcb.footprints.remove(synth_fp)
            log.info(
                "Expanded reuse block '%s' at offset (%.2f, %.2f)",
                group_name,
                offset.x,
                offset.y,
            )
