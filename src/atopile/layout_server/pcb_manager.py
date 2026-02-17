"""Manages loading, extracting render models, and editing a KiCad PCB file."""

from __future__ import annotations

import abc
import time
from pathlib import Path

from atopile.layout_server.models import (
    ArcTrackModel,
    BoardModel,
    DrawingModel,
    DrillModel,
    EdgeModel,
    FilledPolygonModel,
    FootprintModel,
    FootprintSummary,
    FootprintTextModel,
    NetModel,
    PadModel,
    Point2,
    Point3,
    RenderModel,
    Size2,
    TrackModel,
    ViaModel,
    ZoneModel,
)
from faebryk.libs.kicad.fileformats import kicad

# --- Actions for undo/redo ---


class Action(abc.ABC):
    """Base class for undoable actions."""

    @abc.abstractmethod
    def execute(self, pcb: kicad.pcb.KicadPcb) -> None: ...

    @abc.abstractmethod
    def undo(self, pcb: kicad.pcb.KicadPcb) -> None: ...


class MoveAction(Action):
    """Move a footprint to a new position."""

    def __init__(
        self,
        uuid: str,
        new_x: float,
        new_y: float,
        new_r: float | None,
    ) -> None:
        self.uuid = uuid
        self.new_x = new_x
        self.new_y = new_y
        self.new_r = new_r
        # Saved on first execute
        self.old_x: float = 0
        self.old_y: float = 0
        self.old_r: float | None = None

    def _find(self, pcb: kicad.pcb.KicadPcb):
        for fp in pcb.footprints:
            if fp.uuid == self.uuid:
                return fp
        raise ValueError(f"Footprint with uuid {self.uuid!r} not found")

    def execute(self, pcb: kicad.pcb.KicadPcb) -> None:
        fp = self._find(pcb)
        self.old_x = fp.at.x
        self.old_y = fp.at.y
        self.old_r = fp.at.r
        fp.at.x = self.new_x
        fp.at.y = self.new_y
        if self.new_r is not None:
            fp.at.r = self.new_r

    def undo(self, pcb: kicad.pcb.KicadPcb) -> None:
        fp = self._find(pcb)
        fp.at.x = self.old_x
        fp.at.y = self.old_y
        fp.at.r = self.old_r


class RotateAction(Action):
    """Rotate a footprint by a delta angle (degrees)."""

    def __init__(self, uuid: str, delta_degrees: float) -> None:
        self.uuid = uuid
        self.delta_degrees = delta_degrees
        self._old_r: float | None = None

    def _find(self, pcb: kicad.pcb.KicadPcb):
        for fp in pcb.footprints:
            if fp.uuid == self.uuid:
                return fp
        raise ValueError(f"Footprint with uuid {self.uuid!r} not found")

    def execute(self, pcb: kicad.pcb.KicadPcb) -> None:
        fp = self._find(pcb)
        self._old_r = fp.at.r
        fp.at.r = ((fp.at.r or 0) + self.delta_degrees) % 360

    def undo(self, pcb: kicad.pcb.KicadPcb) -> None:
        fp = self._find(pcb)
        fp.at.r = self._old_r


def _flip_layer(layer: str) -> str:
    if layer.startswith("F."):
        return layer.replace("F.", "B.", 1)
    elif layer.startswith("B."):
        return layer.replace("B.", "F.", 1)
    return layer


class FlipAction(Action):
    """Flip a footprint between front and back."""

    def __init__(self, uuid: str) -> None:
        self.uuid = uuid

    def _find(self, pcb: kicad.pcb.KicadPcb):
        for fp in pcb.footprints:
            if fp.uuid == self.uuid:
                return fp
        raise ValueError(f"Footprint with uuid {self.uuid!r} not found")

    def _flip(self, pcb: kicad.pcb.KicadPcb) -> None:
        fp = self._find(pcb)
        # Flip the footprint layer
        fp.layer = _flip_layer(fp.layer)
        # Mirror rotation
        fp.at.r = ((fp.at.r or 0) + 180) % 360
        # Flip pads
        for pad in fp.pads:
            pad.at.y = -pad.at.y
            pad.at.r = ((pad.at.r or 0) + 180) % 360
            pad.layers = [_flip_layer(ly) for ly in pad.layers]
        # Flip drawings
        for line in fp.fp_lines:
            line.start.y = -line.start.y
            line.end.y = -line.end.y
            if hasattr(line, "layer") and line.layer:
                line.layer = _flip_layer(line.layer)
        for arc in fp.fp_arcs:
            arc.start.y = -arc.start.y
            arc.mid.y = -arc.mid.y
            arc.end.y = -arc.end.y
            if hasattr(arc, "layer") and arc.layer:
                arc.layer = _flip_layer(arc.layer)
        for circle in fp.fp_circles:
            circle.center.y = -circle.center.y
            circle.end.y = -circle.end.y
            if hasattr(circle, "layer") and circle.layer:
                circle.layer = _flip_layer(circle.layer)
        for rect in fp.fp_rects:
            rect.start.y = -rect.start.y
            rect.end.y = -rect.end.y
            if hasattr(rect, "layer") and rect.layer:
                rect.layer = _flip_layer(rect.layer)
        for poly in fp.fp_poly:
            for pt in poly.pts.xys:
                pt.y = -pt.y
            if hasattr(poly, "layer") and poly.layer:
                poly.layer = _flip_layer(poly.layer)
        # Flip text/properties
        for prop in fp.propertys:
            prop.at.y = -prop.at.y
            if hasattr(prop, "layer") and prop.layer:
                prop.layer = _flip_layer(prop.layer)
        for txt in fp.fp_texts:
            txt.at.y = -txt.at.y
            if not hasattr(txt, "layer") or not txt.layer:
                continue
            if hasattr(txt.layer, "layer") and txt.layer.layer:
                txt.layer.layer = _flip_layer(txt.layer.layer)
            elif isinstance(txt.layer, str):
                txt.layer = _flip_layer(txt.layer)

    def execute(self, pcb: kicad.pcb.KicadPcb) -> None:
        self._flip(pcb)

    def undo(self, pcb: kicad.pcb.KicadPcb) -> None:
        self._flip(pcb)  # Flip is its own inverse


# --- PcbManager ---


class PcbManager:
    def __init__(self) -> None:
        self._path: Path | None = None
        self._pcb_file: kicad.pcb.PcbFile | None = None
        self._undo_stack: list[Action] = []
        self._redo_stack: list[Action] = []
        self._last_save_time: float = 0

    @property
    def pcb(self) -> kicad.pcb.KicadPcb:
        assert self._pcb_file is not None
        return self._pcb_file.kicad_pcb

    def load(self, path: Path) -> None:
        self._path = path.resolve()
        text = self._path.read_text()
        self._pcb_file = kicad.loads(kicad.pcb.PcbFile, text)
        self._undo_stack.clear()
        self._redo_stack.clear()

    # --- Action execution ---

    def execute_action(self, action: Action) -> None:
        action.execute(self.pcb)
        self._undo_stack.append(action)
        self._redo_stack.clear()

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        action = self._undo_stack.pop()
        action.undo(self.pcb)
        self._redo_stack.append(action)
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        action = self._redo_stack.pop()
        action.execute(self.pcb)
        self._undo_stack.append(action)
        return True

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    # --- High-level mutation helpers ---

    def move_footprint(
        self, uuid: str, x: float, y: float, r: float | None = None
    ) -> None:
        self.execute_action(MoveAction(uuid, x, y, r))

    def rotate_footprint(self, uuid: str, delta_degrees: float) -> None:
        self.execute_action(RotateAction(uuid, delta_degrees))

    def flip_footprint(self, uuid: str) -> None:
        self.execute_action(FlipAction(uuid))

    ACTION_HANDLERS: dict[str, str] = {
        "move": "move_footprint",
        "rotate": "rotate_footprint",
        "flip": "flip_footprint",
    }

    def dispatch_action(self, action_type: str, details: dict) -> bool:
        """Dispatch an action by type name. Returns False if unknown action."""
        method_name = self.ACTION_HANDLERS.get(action_type)
        if method_name is None:
            return False
        method = getattr(self, method_name)
        method(**details)
        return True

    def was_recently_saved(self, threshold: float = 2.0) -> bool:
        """Check if we saved within the last `threshold` seconds."""
        return (time.monotonic() - self._last_save_time) < threshold

    def save(self) -> None:
        assert self._path is not None and self._pcb_file is not None
        kicad.dumps(self._pcb_file, self._path)
        self._last_save_time = time.monotonic()

    # --- Extraction ---

    def get_render_model(self) -> RenderModel:
        pcb = self.pcb
        return RenderModel(
            board=self._extract_board(pcb),
            footprints=[self._extract_footprint(fp) for fp in pcb.footprints],
            tracks=[self._extract_segment(seg) for seg in pcb.segments],
            arcs=[self._extract_arc_segment(arc) for arc in pcb.arcs],
            vias=[self._extract_via(via) for via in pcb.vias],
            zones=[self._extract_zone(zone) for zone in pcb.zones],
            nets=[NetModel(number=n.number, name=n.name) for n in pcb.nets],
        )

    def get_footprints(self) -> list[FootprintSummary]:
        result: list[FootprintSummary] = []
        for fp in self.pcb.footprints:
            ref = _get_property(fp, "Reference")
            value = _get_property(fp, "Value")
            result.append(
                FootprintSummary(
                    uuid=fp.uuid,
                    reference=ref,
                    value=value,
                    x=fp.at.x,
                    y=fp.at.y,
                    r=fp.at.r or 0,
                    layer=fp.layer,
                )
            )
        return result

    # --- Private extraction helpers ---

    def _extract_board(self, pcb: kicad.pcb.KicadPcb) -> BoardModel:
        edges: list[EdgeModel] = []
        for line in pcb.gr_lines:
            if _on_layer(line, "Edge.Cuts"):
                edges.append(
                    EdgeModel(
                        type="line",
                        start=Point2(x=line.start.x, y=line.start.y),
                        end=Point2(x=line.end.x, y=line.end.y),
                    )
                )
        for arc in pcb.gr_arcs:
            if _on_layer(arc, "Edge.Cuts"):
                edges.append(
                    EdgeModel(
                        type="arc",
                        start=Point2(x=arc.start.x, y=arc.start.y),
                        mid=Point2(x=arc.mid.x, y=arc.mid.y),
                        end=Point2(x=arc.end.x, y=arc.end.y),
                    )
                )
        for circle in pcb.gr_circles:
            if _on_layer(circle, "Edge.Cuts"):
                edges.append(
                    EdgeModel(
                        type="circle",
                        center=Point2(x=circle.center.x, y=circle.center.y),
                        end=Point2(x=circle.end.x, y=circle.end.y),
                    )
                )
        for rect in pcb.gr_rects:
            if _on_layer(rect, "Edge.Cuts"):
                edges.append(
                    EdgeModel(
                        type="rect",
                        start=Point2(x=rect.start.x, y=rect.start.y),
                        end=Point2(x=rect.end.x, y=rect.end.y),
                    )
                )

        all_x: list[float] = []
        all_y: list[float] = []
        for e in edges:
            for pt in (e.start, e.end, e.mid, e.center):
                if pt is not None:
                    all_x.append(pt.x)
                    all_y.append(pt.y)

        width = (max(all_x) - min(all_x)) if all_x else 0
        height = (max(all_y) - min(all_y)) if all_y else 0
        origin_x = min(all_x) if all_x else 0
        origin_y = min(all_y) if all_y else 0

        return BoardModel(
            edges=edges,
            width=width,
            height=height,
            origin=Point2(x=origin_x, y=origin_y),
        )

    def _extract_footprint(self, fp) -> FootprintModel:
        ref = _get_property(fp, "Reference")
        value = _get_property(fp, "Value")

        pads: list[PadModel] = []
        for pad in fp.pads:
            pad_h = pad.size.h if pad.size.h is not None else pad.size.w
            pads.append(
                PadModel(
                    name=pad.name,
                    at=Point3(x=pad.at.x, y=pad.at.y, r=pad.at.r or 0),
                    size=Size2(w=pad.size.w, h=pad_h),
                    shape=pad.shape,
                    type=pad.type,
                    layers=list(pad.layers),
                    net=pad.net.number if pad.net else 0,
                    roundrect_rratio=pad.roundrect_rratio,
                    drill=(self._extract_drill(pad.drill) if pad.drill else None),
                )
            )

        drawings: list[DrawingModel] = []
        for line in fp.fp_lines:
            layer = _get_layer(line)
            sw = line.stroke.width if line.stroke else 0.12
            drawings.append(
                DrawingModel(
                    type="line",
                    start=Point2(x=line.start.x, y=line.start.y),
                    end=Point2(x=line.end.x, y=line.end.y),
                    width=sw,
                    layer=layer,
                )
            )
        for arc in fp.fp_arcs:
            layer = _get_layer(arc)
            sw = arc.stroke.width if arc.stroke else 0.12
            drawings.append(
                DrawingModel(
                    type="arc",
                    start=Point2(x=arc.start.x, y=arc.start.y),
                    mid=Point2(x=arc.mid.x, y=arc.mid.y),
                    end=Point2(x=arc.end.x, y=arc.end.y),
                    width=sw,
                    layer=layer,
                )
            )
        for circle in fp.fp_circles:
            layer = _get_layer(circle)
            sw = circle.stroke.width if circle.stroke else 0.12
            drawings.append(
                DrawingModel(
                    type="circle",
                    center=Point2(x=circle.center.x, y=circle.center.y),
                    end=Point2(x=circle.end.x, y=circle.end.y),
                    width=sw,
                    layer=layer,
                )
            )
        for rect in fp.fp_rects:
            layer = _get_layer(rect)
            sw = rect.stroke.width if rect.stroke else 0.12
            drawings.append(
                DrawingModel(
                    type="rect",
                    start=Point2(x=rect.start.x, y=rect.start.y),
                    end=Point2(x=rect.end.x, y=rect.end.y),
                    width=sw,
                    layer=layer,
                )
            )
        for poly in fp.fp_poly:
            layer = _get_layer(poly)
            sw = poly.stroke.width if poly.stroke else 0.12
            pts = [Point2(x=p.x, y=p.y) for p in poly.pts.xys]
            drawings.append(
                DrawingModel(
                    type="polygon",
                    points=pts,
                    width=sw,
                    layer=layer,
                )
            )

        texts = self._extract_text_entries(fp, ref, value)

        return FootprintModel(
            uuid=fp.uuid,
            name=fp.name,
            reference=ref,
            value=value,
            at=Point3(x=fp.at.x, y=fp.at.y, r=fp.at.r or 0),
            layer=fp.layer,
            pads=pads,
            drawings=drawings,
            texts=texts,
        )

    def _extract_text_entries(
        self, fp, reference: str | None, footprint_value: str | None
    ) -> list[FootprintTextModel]:
        texts: list[FootprintTextModel] = []

        for prop in fp.propertys:
            if _is_hidden(prop):
                continue
            prop_value = getattr(prop, "value", None)
            if prop_value is None:
                continue
            resolved = _resolve_text_tokens(prop_value, reference, footprint_value)
            if not resolved.strip():
                continue
            texts.append(
                self._extract_text_entry(
                    kind="property",
                    name=getattr(prop, "name", None),
                    text=resolved,
                    obj=prop,
                )
            )

        for txt in fp.fp_texts:
            if _is_hidden(txt):
                continue
            txt_value = getattr(txt, "text", None)
            if txt_value is None:
                continue
            resolved = _resolve_text_tokens(txt_value, reference, footprint_value)
            if not resolved.strip():
                continue
            texts.append(
                self._extract_text_entry(
                    kind="fp_text",
                    name=_text_type_name(getattr(txt, "type", None)),
                    text=resolved,
                    obj=txt,
                )
            )

        return texts

    def _extract_text_entry(
        self, kind: str, name: str | None, text: str, obj
    ) -> FootprintTextModel:
        at = getattr(obj, "at", None)
        effects = getattr(obj, "effects", None)
        font = getattr(effects, "font", None)
        font_size = getattr(font, "size", None)

        size: Size2 | None = None
        if (
            font_size is not None
            and getattr(font_size, "w", None) is not None
            and getattr(font_size, "h", None) is not None
        ):
            size = Size2(w=font_size.w, h=font_size.h)

        return FootprintTextModel(
            kind=kind,
            name=name,
            text=text,
            at=Point3(
                x=getattr(at, "x", 0.0),
                y=getattr(at, "y", 0.0),
                r=(getattr(at, "r", 0.0) or 0.0),
            ),
            layer=_text_layer_name(getattr(obj, "layer", None)),
            hide=bool(getattr(obj, "hide", False)),
            size=size,
            thickness=getattr(font, "thickness", None),
        )

    def _extract_drill(self, drill) -> DrillModel:
        return DrillModel(
            shape=getattr(drill, "shape", None),
            size_x=(drill.size_x if hasattr(drill, "size_x") else None),
            size_y=(drill.size_y if hasattr(drill, "size_y") else None),
        )

    def _extract_segment(self, seg) -> TrackModel:
        return TrackModel(
            start=Point2(x=seg.start.x, y=seg.start.y),
            end=Point2(x=seg.end.x, y=seg.end.y),
            width=seg.width,
            layer=seg.layer,
            net=seg.net,
            uuid=seg.uuid,
        )

    def _extract_arc_segment(self, arc) -> ArcTrackModel:
        return ArcTrackModel(
            start=Point2(x=arc.start.x, y=arc.start.y),
            mid=Point2(x=arc.mid.x, y=arc.mid.y),
            end=Point2(x=arc.end.x, y=arc.end.y),
            width=arc.width,
            layer=arc.layer,
            net=arc.net,
            uuid=arc.uuid,
        )

    def _extract_via(self, via) -> ViaModel:
        return ViaModel(
            at=Point2(x=via.at.x, y=via.at.y),
            size=via.size,
            drill=via.drill,
            layers=list(via.layers),
            net=via.net,
            uuid=via.uuid,
        )

    def _extract_zone(self, zone) -> ZoneModel:
        layers = (
            list(zone.layers) if zone.layers else ([zone.layer] if zone.layer else [])
        )
        pts = (
            [Point2(x=p.x, y=p.y) for p in zone.polygon.pts.xys] if zone.polygon else []
        )
        filled: list[FilledPolygonModel] = []
        for fp in zone.filled_polygon:
            filled.append(
                FilledPolygonModel(
                    layer=fp.layer,
                    points=[Point2(x=p.x, y=p.y) for p in fp.pts.xys],
                )
            )
        return ZoneModel(
            net=zone.net,
            net_name=zone.net_name,
            layers=layers,
            name=zone.name,
            uuid=zone.uuid,
            outline=pts,
            filled_polygons=filled,
        )


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


def _text_layer_name(layer_obj) -> str | None:
    if layer_obj is None:
        return None
    if isinstance(layer_obj, str):
        return layer_obj
    if hasattr(layer_obj, "layer") and layer_obj.layer:
        return layer_obj.layer
    return None


def _text_type_name(text_type) -> str | None:
    if text_type is None:
        return None
    if isinstance(text_type, str):
        return text_type
    if hasattr(text_type, "name"):
        return str(text_type.name).lower()
    return str(text_type).split(".")[-1].lower()


def _is_hidden(text_obj) -> bool:
    if bool(getattr(text_obj, "hide", False)):
        return True
    effects = getattr(text_obj, "effects", None)
    if effects is not None and bool(getattr(effects, "hide", False)):
        return True
    return False


def _resolve_text_tokens(text: str, reference: str | None, value: str | None) -> str:
    if not text:
        return text

    ref_text = reference or ""
    value_text = value or ""
    out = text.replace("%R", ref_text).replace("%V", value_text)

    replacements = {
        "REFERENCE": ref_text,
        "REF": ref_text,
        "REFDES": ref_text,
        "VALUE": value_text,
        "VAL": value_text,
    }

    result_parts: list[str] = []
    i = 0
    while i < len(out):
        if i + 2 < len(out) and out[i] == "$" and out[i + 1] == "{":
            end = out.find("}", i + 2)
            if end != -1:
                key = out[i + 2 : end].strip().upper()
                if key in replacements:
                    result_parts.append(replacements[key])
                else:
                    result_parts.append(out[i : end + 1])
                i = end + 1
                continue
        result_parts.append(out[i])
        i += 1

    return "".join(result_parts)
