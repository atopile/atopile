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

    RESOLUTION_VALUE = 1000

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
            },
            layers=[
                {"id": layer.name, "type": str(getattr(layer, "type", "signal")).lower(), "keepouts": []}
                for layer in copper_layers
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
        for net in pcb.nets:
            name = str(net.name or "").strip()
            net_id = name if name else str(net.number)
            net_id_by_number[int(net.number)] = net_id

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
                            "rotation": int(round(float(getattr(pad.at, "r", 0.0) or 0.0))),
                        }
                    )

                component_definitions[definition_id] = {
                    "id": definition_id,
                    "outline": cls._footprint_outline(fp),
                    "pins": definition_pins,
                    "keepouts": [],
                }

            component_id = cls._component_id(fp)
            components.append(
                {
                    "id": component_id,
                    "definition": definition_id,
                    "position": cls._xy_to_point(fp.at),
                    "rotation": int(round(float(getattr(fp.at, "r", 0.0) or 0.0))),
                    "side": "BACK" if str(fp.layer).startswith("B.") else "FRONT",
                    "partNumber": str(fp.name),
                    "protected": bool(getattr(fp, "locked", False)),
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
                "pins": sorted(set(pins_by_net.get(net_id, []))),
            }
            for net_id in sorted(net_id_by_number.values())
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
                    "layer": copper_layer_index.get(layer_name, 0),
                    "shape": {"type": "polygon", "points": points},
                }
            )

        if include_lossless_source:
            board.metadata["kicad_pcb_sexp"] = kicad.dumps(kicad.pcb.PcbFile(kicad_pcb=pcb))

        return board

    @classmethod
    def to_kicad_file(
        cls,
        board_file: C_deeppcb_board_file,
    ):
        return kicad.pcb.PcbFile(kicad_pcb=cls.to_kicad_pcb(board_file))

    @classmethod
    def to_kicad_pcb(
        cls,
        board_file: C_deeppcb_board_file,
    ):
        metadata = board_file.metadata if isinstance(board_file.metadata, dict) else {}
        raw = metadata.get("kicad_pcb_sexp")
        if isinstance(raw, str) and raw.strip():
            return kicad.loads(kicad.pcb.PcbFile, raw).kicad_pcb

        raise RuntimeError(
            "DeepPCB -> KiCad currently requires lossless metadata. "
            "Export with include_lossless_source=True."
        )

    @staticmethod
    def loads(path_or_content):
        return deeppcb.loads(deeppcb.board.BoardFile, path_or_content)

    @staticmethod
    def dumps(board_file: C_deeppcb_board_file, path=None) -> str:
        return deeppcb.dumps(board_file, path)

    @classmethod
    def _to_unit(cls, mm: float) -> int:
        return int(round(mm * cls.RESOLUTION_VALUE))

    @classmethod
    def _xy_to_point(cls, xy: Any) -> list[int]:
        return [cls._to_unit(float(xy.x)), cls._to_unit(float(xy.y))]

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
        size_w = float(getattr(pad.size, "w", 0.0) or 0.0)
        size_h = float(getattr(pad.size, "h", size_w) or size_w)
        layers = cls._layer_indices(getattr(pad, "layers", []), copper_layer_index)

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

        padstack_id = f"Padstack_{shape}_{cls._to_unit(size_w)}x{cls._to_unit(size_h)}_L{','.join(map(str,layers))}"
        return padstack_id, {
            "id": padstack_id,
            "shape": geom,
            "layers": layers,
            "allowVia": False,
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
        return f"{fp.name}__{'BACK' if str(fp.layer).startswith('B.') else 'FRONT'}"

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
                    "center": cls._xy_to_point(circle.center),
                    "radius": cls._to_unit(radius),
                }
            )

        for arc in getattr(fp, "fp_arcs", []):
            shapes.append(
                {
                    "type": "polyline",
                    "points": [
                        cls._xy_to_point(arc.start),
                        cls._xy_to_point(arc.mid),
                        cls._xy_to_point(arc.end),
                    ],
                }
            )

        for poly in getattr(fp, "fp_poly", []):
            points = [cls._xy_to_point(xy) for xy in poly.pts.xys]
            shapes.append({"type": "polyline", "points": points})

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
