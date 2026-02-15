"""Manages loading, extracting render models, and editing a KiCad PCB file."""

from __future__ import annotations

from pathlib import Path

from faebryk.libs.kicad.fileformats import kicad


class PcbManager:
    def __init__(self) -> None:
        self._path: Path | None = None
        self._pcb_file: kicad.pcb.PcbFile | None = None

    @property
    def pcb(self) -> kicad.pcb.KicadPcb:
        assert self._pcb_file is not None
        return self._pcb_file.kicad_pcb

    def load(self, path: Path) -> None:
        self._path = path.resolve()
        # Bypass cache by reading string directly
        text = self._path.read_text()
        self._pcb_file = kicad.loads(kicad.pcb.PcbFile, text)

    def get_render_model(self) -> dict:
        pcb = self.pcb
        return {
            "board": self._extract_board(pcb),
            "footprints": [self._extract_footprint(fp) for fp in pcb.footprints],
            "tracks": [self._extract_segment(seg) for seg in pcb.segments],
            "arcs": [self._extract_arc_segment(arc) for arc in pcb.arcs],
            "vias": [self._extract_via(via) for via in pcb.vias],
            "zones": [self._extract_zone(zone) for zone in pcb.zones],
            "nets": [{"number": n.number, "name": n.name} for n in pcb.nets],
        }

    def get_footprints(self) -> list[dict]:
        result = []
        for fp in self.pcb.footprints:
            ref = _get_property(fp, "Reference")
            value = _get_property(fp, "Value")
            result.append(
                {
                    "uuid": fp.uuid,
                    "reference": ref,
                    "value": value,
                    "x": fp.at.x,
                    "y": fp.at.y,
                    "r": fp.at.r or 0,
                    "layer": fp.layer,
                }
            )
        return result

    def move_footprint(
        self, uuid: str, x: float, y: float, r: float | None = None
    ) -> None:
        for fp in self.pcb.footprints:
            if fp.uuid == uuid:
                fp.at.x = x
                fp.at.y = y
                if r is not None:
                    fp.at.r = r
                return
        raise ValueError(f"Footprint with uuid {uuid!r} not found")

    def save(self) -> None:
        assert self._path is not None and self._pcb_file is not None
        kicad.dumps(self._pcb_file, self._path)

    # --- private extraction helpers ---

    def _extract_board(self, pcb: kicad.pcb.KicadPcb) -> dict:
        edges: list[dict] = []
        for line in pcb.gr_lines:
            if _on_layer(line, "Edge.Cuts"):
                edges.append(
                    {
                        "type": "line",
                        "start": [line.start.x, line.start.y],
                        "end": [line.end.x, line.end.y],
                    }
                )
        for arc in pcb.gr_arcs:
            if _on_layer(arc, "Edge.Cuts"):
                edges.append(
                    {
                        "type": "arc",
                        "start": [arc.start.x, arc.start.y],
                        "mid": [arc.mid.x, arc.mid.y],
                        "end": [arc.end.x, arc.end.y],
                    }
                )
        for circle in pcb.gr_circles:
            if _on_layer(circle, "Edge.Cuts"):
                edges.append(
                    {
                        "type": "circle",
                        "center": [circle.center.x, circle.center.y],
                        "end": [circle.end.x, circle.end.y],
                    }
                )
        for rect in pcb.gr_rects:
            if _on_layer(rect, "Edge.Cuts"):
                edges.append(
                    {
                        "type": "rect",
                        "start": [rect.start.x, rect.start.y],
                        "end": [rect.end.x, rect.end.y],
                    }
                )

        # Compute bounding box from edges
        all_x: list[float] = []
        all_y: list[float] = []
        for e in edges:
            for key in ("start", "end", "mid", "center"):
                if key in e:
                    all_x.append(e[key][0])
                    all_y.append(e[key][1])

        width = (max(all_x) - min(all_x)) if all_x else 0
        height = (max(all_y) - min(all_y)) if all_y else 0
        origin_x = min(all_x) if all_x else 0
        origin_y = min(all_y) if all_y else 0

        return {
            "edges": edges,
            "width": width,
            "height": height,
            "origin": [origin_x, origin_y],
        }

    def _extract_footprint(self, fp) -> dict:
        ref = _get_property(fp, "Reference")
        value = _get_property(fp, "Value")

        pads = []
        for pad in fp.pads:
            pad_h = pad.size.h if pad.size.h is not None else pad.size.w
            pads.append(
                {
                    "name": pad.name,
                    "at": [pad.at.x, pad.at.y, pad.at.r or 0],
                    "size": [pad.size.w, pad_h],
                    "shape": pad.shape,
                    "type": pad.type,
                    "layers": list(pad.layers),
                    "net": pad.net.number if pad.net else 0,
                    "roundrect_rratio": pad.roundrect_rratio,
                    "drill": self._extract_drill(pad.drill) if pad.drill else None,
                }
            )

        drawings: list[dict] = []
        for line in fp.fp_lines:
            layer = _get_layer(line)
            stroke_width = line.stroke.width if line.stroke else 0.12
            drawings.append(
                {
                    "type": "line",
                    "start": [line.start.x, line.start.y],
                    "end": [line.end.x, line.end.y],
                    "width": stroke_width,
                    "layer": layer,
                }
            )
        for arc in fp.fp_arcs:
            layer = _get_layer(arc)
            stroke_width = arc.stroke.width if arc.stroke else 0.12
            drawings.append(
                {
                    "type": "arc",
                    "start": [arc.start.x, arc.start.y],
                    "mid": [arc.mid.x, arc.mid.y],
                    "end": [arc.end.x, arc.end.y],
                    "width": stroke_width,
                    "layer": layer,
                }
            )
        for circle in fp.fp_circles:
            layer = _get_layer(circle)
            stroke_width = circle.stroke.width if circle.stroke else 0.12
            drawings.append(
                {
                    "type": "circle",
                    "center": [circle.center.x, circle.center.y],
                    "end": [circle.end.x, circle.end.y],
                    "width": stroke_width,
                    "layer": layer,
                }
            )
        for rect in fp.fp_rects:
            layer = _get_layer(rect)
            stroke_width = rect.stroke.width if rect.stroke else 0.12
            drawings.append(
                {
                    "type": "rect",
                    "start": [rect.start.x, rect.start.y],
                    "end": [rect.end.x, rect.end.y],
                    "width": stroke_width,
                    "layer": layer,
                }
            )
        for poly in fp.fp_poly:
            layer = _get_layer(poly)
            stroke_width = poly.stroke.width if poly.stroke else 0.12
            pts = [[p.x, p.y] for p in poly.pts.xys]
            drawings.append(
                {
                    "type": "polygon",
                    "points": pts,
                    "width": stroke_width,
                    "layer": layer,
                }
            )

        return {
            "uuid": fp.uuid,
            "name": fp.name,
            "reference": ref,
            "value": value,
            "at": [fp.at.x, fp.at.y, fp.at.r or 0],
            "layer": fp.layer,
            "pads": pads,
            "drawings": drawings,
        }

    def _extract_drill(self, drill) -> dict:
        return {
            "shape": getattr(drill, "shape", None),
            "size_x": drill.size_x if hasattr(drill, "size_x") else None,
            "size_y": drill.size_y if hasattr(drill, "size_y") else None,
        }

    def _extract_segment(self, seg) -> dict:
        return {
            "start": [seg.start.x, seg.start.y],
            "end": [seg.end.x, seg.end.y],
            "width": seg.width,
            "layer": seg.layer,
            "net": seg.net,
            "uuid": seg.uuid,
        }

    def _extract_arc_segment(self, arc) -> dict:
        return {
            "start": [arc.start.x, arc.start.y],
            "mid": [arc.mid.x, arc.mid.y],
            "end": [arc.end.x, arc.end.y],
            "width": arc.width,
            "layer": arc.layer,
            "net": arc.net,
            "uuid": arc.uuid,
        }

    def _extract_via(self, via) -> dict:
        return {
            "at": [via.at.x, via.at.y],
            "size": via.size,
            "drill": via.drill,
            "layers": list(via.layers),
            "net": via.net,
            "uuid": via.uuid,
        }

    def _extract_zone(self, zone) -> dict:
        layers = (
            list(zone.layers) if zone.layers else ([zone.layer] if zone.layer else [])
        )
        pts = [[p.x, p.y] for p in zone.polygon.pts.xys] if zone.polygon else []
        filled: list[dict] = []
        for fp in zone.filled_polygon:
            filled.append(
                {
                    "layer": fp.layer,
                    "points": [[p.x, p.y] for p in fp.pts.xys],
                }
            )
        return {
            "net": zone.net,
            "net_name": zone.net_name,
            "layers": layers,
            "name": zone.name,
            "uuid": zone.uuid,
            "outline": pts,
            "filled_polygons": filled,
        }


def _get_property(fp, name: str) -> str | None:
    for prop in fp.propertys:
        if prop.name == name:
            return prop.value
    return None


def _on_layer(obj, layer_name: str) -> bool:
    if hasattr(obj, "layer") and obj.layer == layer_name:
        return True
    if hasattr(obj, "layers") and layer_name in (obj.layers or []):
        return True
    return False


def _get_layer(obj) -> str | None:
    if hasattr(obj, "layer") and obj.layer:
        return obj.layer
    if hasattr(obj, "layers") and obj.layers:
        return obj.layers[0]
    return None
