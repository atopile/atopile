from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from faebryk.libs.deeppcb_fileformats import C_deeppcb_board_file, deeppcb
from faebryk.libs.kicad.fileformats import Property, kicad


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
    ) -> C_deeppcb_board_file:
        return cls.from_kicad_pcb(
            pcb_file.kicad_pcb,
            include_lossless_source=include_lossless_source,
        )

    @classmethod
    def from_kicad_pcb(
        cls,
        pcb: Any,
        *,
        include_lossless_source: bool = False,
    ) -> C_deeppcb_board_file:
        copper_layers = [layer for layer in pcb.layers if str(layer.name).endswith(".Cu")]
        copper_layer_index = {layer.name: idx for idx, layer in enumerate(copper_layers)}

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
            via_id = cls._via_definition_id(via)
            if via_id not in via_definitions:
                via_definitions.append(via_id)
            padstack_id, padstack = cls._padstack_from_via(via, copper_layer_index)
            padstacks.setdefault(padstack_id, padstack)

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

        for fp in pcb.footprints:
            definition_id = cls._definition_id(fp)
            if definition_id not in component_definitions:
                definition_pins = []
                for pad in fp.pads:
                    padstack_id, padstack = cls._padstack_from_pad(pad, copper_layer_index)
                    padstacks.setdefault(padstack_id, padstack)
                    definition_pins.append(
                        {
                            "id": str(pad.name),
                            "padstack": padstack_id,
                            "position": cls._xy_to_point(pad.at),
                            "rotation": (
                                float(getattr(pad.at, "r"))
                                if getattr(pad.at, "r", None) is not None
                                else None
                            ),
                        }
                    )

                component_definitions[definition_id] = {
                    "id": definition_id,
                    "outline": cls._footprint_outline(fp),
                    "pins": definition_pins,
                    "keepouts": [],
                }

            component_id = cls._component_id(fp)
            reference_property = None
            for prop in getattr(fp, "propertys", []):
                if str(getattr(prop, "name", "")) != "Reference":
                    continue
                reference_property = {
                    "value": str(getattr(prop, "value", component_id)),
                    "at": cls._xy_to_point(getattr(prop, "at", kicad.pcb.Xyr(x=0.0, y=0.0, r=0.0))),
                    "rotation": (
                        float(getattr(getattr(prop, "at", None), "r"))
                        if getattr(getattr(prop, "at", None), "r", None) is not None
                        else None
                    ),
                    "layer": str(getattr(prop, "layer", "F.SilkS")),
                    "hide": getattr(prop, "hide", None),
                    "unlocked": getattr(prop, "unlocked", None),
                    "effects": (
                        {
                            "font": (
                                {
                                    "size": [
                                        float(getattr(getattr(getattr(prop.effects, "font", None), "size", None), "w", 1.0) or 1.0),
                                        float(getattr(getattr(getattr(prop.effects, "font", None), "size", None), "h", 1.0) or 1.0),
                                    ],
                                    "thickness": float(getattr(getattr(prop.effects, "font", None), "thickness", 0.15) or 0.15),
                                    "bold": getattr(getattr(prop.effects, "font", None), "bold", None),
                                    "italic": getattr(getattr(prop.effects, "font", None), "italic", None),
                                }
                                if getattr(prop.effects, "font", None) is not None
                                else None
                            ),
                            "hide": getattr(prop.effects, "hide", None),
                            "justify": (
                                {
                                    "justify1": getattr(prop.effects.justify, "justify1", None),
                                    "justify2": getattr(prop.effects.justify, "justify2", None),
                                    "justify3": getattr(prop.effects.justify, "justify3", None),
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
                    "rotation": (
                        float(getattr(fp.at, "r"))
                        if getattr(fp.at, "r", None) is not None
                        else None
                    ),
                    "side": "BACK" if str(fp.layer).startswith("B.") else "FRONT",
                    "partNumber": str(fp.name),
                    "protected": bool(getattr(fp, "locked", False)),
                    "embeddedFonts": getattr(fp, "embedded_fonts", None),
                    "referenceProperty": reference_property,
                }
            )

            for pad in fp.pads:
                if pad.net is None:
                    continue
                net_number = int(getattr(pad.net, "number", 0) or 0)
                net_id = net_id_by_number.get(net_number)
                if not net_id:
                    continue
                pins_by_net.setdefault(net_id, []).append(f"{component_id}-{pad.name}")

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
            for number, net_id in sorted(net_id_by_number.items(), key=lambda item: item[0])
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
                "padstack": cls._via_definition_id(via),
                "free": getattr(via, "free", None),
            }
            for via in pcb.vias
        ]

        board.planes = []
        for zone in pcb.zones:
            poly = getattr(zone, "polygon", None)
            pts = getattr(getattr(poly, "pts", None), "xys", None)
            if pts is None:
                continue
            points = [cls._xy_to_point(xy) for xy in pts]
            if not points:
                continue

            zone_layers = list(getattr(zone, "layers", []) or [])
            layer_name = str(zone_layers[0]) if zone_layers else str(getattr(zone, "layer", "F.Cu"))
            board.planes.append(
                {
                    "netId": net_id_by_number.get(int(getattr(zone, "net", 0) or 0), str(int(getattr(zone, "net", 0) or 0))),
                    "netName": getattr(zone, "net_name", None),
                    "zoneLayer": getattr(zone, "layer", None),
                    "name": getattr(zone, "name", None),
                    "priority": getattr(zone, "priority", None),
                    "layer": copper_layer_index.get(layer_name, 0),
                    "shape": {"type": "polygon", "points": points},
                    "connectPads": (
                        {
                            "mode": getattr(zone.connect_pads, "mode", None),
                            "clearance": getattr(zone.connect_pads, "clearance", None),
                        }
                        if getattr(zone, "connect_pads", None) is not None
                        else None
                    ),
                    "minThickness": getattr(zone, "min_thickness", None),
                    "filledAreasThickness": getattr(zone, "filled_areas_thickness", None),
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
                            "sourceType": getattr(zone.placement, "source_type", None),
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
                            "thermalBridgeWidth": getattr(zone.fill, "thermal_bridge_width", None),
                        }
                        if getattr(zone, "fill", None) is not None
                        else None
                    ),
                }
            )

        if include_lossless_source:
            board.metadata["kicad_pcb_sexp"] = kicad.dumps(kicad.pcb.PcbFile(kicad_pcb=pcb))
        if getattr(pcb, "embedded_fonts", None) is not None:
            board.metadata["kicad_embedded_fonts"] = getattr(pcb, "embedded_fonts", None)

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
            drill_radius = float(padstack.get("drill", max(radius / 2.0, 150)))
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
            points = shape.get("points")
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
                            xys=[cls._point_to_xy(point, resolution) for point in points]
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
            definition_id = str(component.get("definition", ""))
            definition = definition_by_id.get(definition_id, {})
            position = component.get("position", [0, 0])
            component_rotation = component.get("rotation")
            rotation = float(component_rotation) if component_rotation is not None else None
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
                if isinstance(stored_layers, list) and stored_layers:
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
                pad_shape = str(padstack.get("kicadShape") or cls._pad_shape(padstack.get("shape")))
                pad_type = str(
                    padstack.get("kicadPadType")
                    or (
                        "thru_hole"
                        if "F.Cu" in pad_layers and "B.Cu" in pad_layers
                        else "smd"
                    )
                )

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
                            x=cls._from_unit(float(pin.get("position", [0, 0])[0]), resolution),
                            y=cls._from_unit(float(pin.get("position", [0, 0])[1]), resolution),
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
                ref_value = str(reference_prop.get("value", component_id))
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
                ref_value = component_id
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
                    name=str(component.get("partNumber", definition_id or component_id)),
                    layer=layer,
                    uuid=kicad.gen_uuid(),
                    at=kicad.pcb.Xyr(
                        x=cls._from_unit(float(position[0]), resolution),
                        y=cls._from_unit(float(position[1]), resolution),
                        r=rotation,
                    ),
                    path=None,
                    propertys=[
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
                    ],
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
        if isinstance(board_file.metadata, dict) and "kicad_embedded_fonts" in board_file.metadata:
            pcb.embedded_fonts = board_file.metadata.get("kicad_embedded_fonts")
        return pcb

    @staticmethod
    def loads(path_or_content):
        return deeppcb.loads(deeppcb.board.BoardFile, path_or_content)

    @staticmethod
    def dumps(board_file: C_deeppcb_board_file, path=None) -> str:
        return deeppcb.dumps(board_file, path)

    @classmethod
    def _to_unit(cls, mm: float) -> int:
        return int(round(mm * cls.RESOLUTION_VALUE))

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
        parsed = [point for point in points if isinstance(point, list) and len(point) >= 2]
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
                xs = [float(p[0]) for p in points if isinstance(p, list) and len(p) >= 2]
                ys = [float(p[1]) for p in points if isinstance(p, list) and len(p) >= 2]
                if xs and ys:
                    return max(max(xs) - min(xs), max(ys) - min(ys)) / 2.0
        return default

    @staticmethod
    def _shape_size(shape: Any, default: float) -> tuple[float, float]:
        if not isinstance(shape, dict):
            return default, default
        if shape.get("type") == "circle":
            radius = shape.get("radius")
            if isinstance(radius, (int, float)):
                diameter = float(radius) * 2.0
                return diameter, diameter
            return default, default
        if shape.get("type") == "polyline":
            points = shape.get("points", [])
            if isinstance(points, list):
                xs = [float(p[0]) for p in points if isinstance(p, list) and len(p) >= 2]
                ys = [float(p[1]) for p in points if isinstance(p, list) and len(p) >= 2]
                if xs and ys:
                    return max(xs) - min(xs), max(ys) - min(ys)
        return default, default

    @staticmethod
    def _pad_shape(shape: Any) -> str:
        if isinstance(shape, dict):
            shape_type = str(shape.get("type", "")).lower()
            if shape_type == "circle":
                return "circle"
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
            xy_points = [cls._point_to_xy(point, resolution) for point in points if isinstance(point, list) and len(point) >= 2]
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
    def _layer_indices(cls, layers: Iterable[str], copper_layer_index: dict[str, int]) -> list[int]:
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

        if shape in {"circle", "oval"}:
            radius = max(size_w, size_h) / 2.0
            geom = {
                "type": "circle",
                "center": [0, 0],
                "radius": cls._to_unit(radius),
            }
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

        raw_layers_id = ",".join(raw_layers)
        drill_id = ""
        if isinstance(drill_payload, dict):
            drill_id = (
                f"_D{drill_payload.get('shape')}:{drill_payload.get('sizeX')}:{drill_payload.get('sizeY')}"
            )
        padstack_id = (
            f"Padstack_{shape}_{pad_type}_{cls._to_unit(size_w)}x{cls._to_unit(size_h)}"
            f"_L{','.join(map(str,layers))}_RAW{raw_layers_id}{drill_id}"
        )
        return padstack_id, {
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

    @classmethod
    def _padstack_from_via(
        cls,
        via: Any,
        copper_layer_index: dict[str, int],
    ) -> tuple[str, dict[str, Any]]:
        size = float(getattr(via, "size", 0.0) or 0.0)
        drill = float(getattr(via, "drill", 0.0) or 0.0)
        layers = cls._layer_indices(getattr(via, "layers", []), copper_layer_index)
        via_id = cls._via_definition_id(via)
        return via_id, {
            "id": via_id,
            "shape": {
                "type": "circle",
                "center": [0, 0],
                "radius": cls._to_unit(size / 2.0),
            },
            "layers": layers,
            "allowVia": True,
            "drill": cls._to_unit(drill / 2.0),
        }

    @classmethod
    def _via_definition_id(cls, via: Any) -> str:
        size = cls._to_unit(float(getattr(via, "size", 0.0) or 0.0))
        drill = cls._to_unit(float(getattr(via, "drill", 0.0) or 0.0))
        return f"Via_{size}:{drill}"

    @staticmethod
    def _definition_id(fp: Any) -> str:
        return f"{fp.name}__{'BACK' if str(fp.layer).startswith('B.') else 'FRONT'}__{fp.uuid}"

    @staticmethod
    def _component_id(fp: Any) -> str:
        ref = Property.try_get_property(fp.propertys, "Reference")
        if isinstance(ref, str) and ref.strip():
            return ref.strip()
        return str(fp.uuid)

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
            radius = ((float(circle.end.x) - float(circle.center.x)) ** 2 + (float(circle.end.y) - float(circle.center.y)) ** 2) ** 0.5
            shapes.append(
                {
                    "type": "circle",
                    "layer": circle.layer,
                    "strokeWidth": float(circle.stroke.width) if circle.stroke else None,
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
        points: list[list[int]] = []

        for line in getattr(pcb, "gr_lines", []):
            if str(getattr(line, "layer", "")) != "Edge.Cuts":
                continue
            points.append(cls._xy_to_point(line.start))
            points.append(cls._xy_to_point(line.end))

        for arc in getattr(pcb, "gr_arcs", []):
            if str(getattr(arc, "layer", "")) != "Edge.Cuts":
                continue
            points.append(cls._xy_to_point(arc.start))
            points.append(cls._xy_to_point(arc.mid))
            points.append(cls._xy_to_point(arc.end))

        for poly in getattr(pcb, "gr_polys", []):
            if str(getattr(poly, "layer", "")) != "Edge.Cuts":
                continue
            for xy in poly.pts.xys:
                points.append(cls._xy_to_point(xy))

        if points and points[0] != points[-1]:
            points.append(points[0])
        return points

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
