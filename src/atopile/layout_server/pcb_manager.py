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
    NetModel,
    PadModel,
    Point2,
    Point3,
    RenderModel,
    Size2,
    TextModel,
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
            drawings=self._extract_global_drawings(pcb),
            texts=self._extract_global_texts(pcb),
            footprints=[self._extract_footprint(fp) for fp in pcb.footprints],
            tracks=[self._extract_segment(seg) for seg in pcb.segments],
            arcs=[self._extract_arc_segment(arc) for arc in pcb.arcs],
            vias=[self._extract_via(via) for via in pcb.vias],
            zones=self._extract_zones(pcb),
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
            sw = _stroke_width(line)
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
            sw = _stroke_width(arc)
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
            sw = _stroke_width(circle)
            drawings.append(
                DrawingModel(
                    type="circle",
                    center=Point2(x=circle.center.x, y=circle.center.y),
                    end=Point2(x=circle.end.x, y=circle.end.y),
                    width=sw,
                    layer=layer,
                    filled=_is_filled(circle),
                )
            )
        for rect in fp.fp_rects:
            layer = _get_layer(rect)
            sw = _stroke_width(rect)
            drawings.append(
                DrawingModel(
                    type="rect",
                    start=Point2(x=rect.start.x, y=rect.start.y),
                    end=Point2(x=rect.end.x, y=rect.end.y),
                    width=sw,
                    layer=layer,
                    filled=_is_filled(rect),
                )
            )
        for poly in fp.fp_poly:
            layer = _get_layer(poly)
            sw = _stroke_width(poly)
            pts = [Point2(x=p.x, y=p.y) for p in poly.pts.xys]
            drawings.append(
                DrawingModel(
                    type="polygon",
                    points=pts,
                    width=sw,
                    layer=layer,
                    filled=_is_filled(poly),
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

    def _extract_global_drawings(self, pcb: kicad.pcb.KicadPcb) -> list[DrawingModel]:
        drawings: list[DrawingModel] = []

        for line in pcb.gr_lines:
            if _on_layer(line, "Edge.Cuts"):
                continue
            layer = _get_layer(line)
            sw = _stroke_width(line)
            drawings.append(
                DrawingModel(
                    type="line",
                    start=Point2(x=line.start.x, y=line.start.y),
                    end=Point2(x=line.end.x, y=line.end.y),
                    width=sw,
                    layer=layer,
                )
            )

        for arc in pcb.gr_arcs:
            if _on_layer(arc, "Edge.Cuts"):
                continue
            layer = _get_layer(arc)
            sw = _stroke_width(arc)
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

        for circle in pcb.gr_circles:
            if _on_layer(circle, "Edge.Cuts"):
                continue
            layer = _get_layer(circle)
            sw = _stroke_width(circle)
            drawings.append(
                DrawingModel(
                    type="circle",
                    center=Point2(x=circle.center.x, y=circle.center.y),
                    end=Point2(x=circle.end.x, y=circle.end.y),
                    width=sw,
                    layer=layer,
                    filled=_is_filled(circle),
                )
            )

        for rect in pcb.gr_rects:
            if _on_layer(rect, "Edge.Cuts"):
                continue
            layer = _get_layer(rect)
            sw = _stroke_width(rect)
            drawings.append(
                DrawingModel(
                    type="rect",
                    start=Point2(x=rect.start.x, y=rect.start.y),
                    end=Point2(x=rect.end.x, y=rect.end.y),
                    width=sw,
                    layer=layer,
                    filled=_is_filled(rect),
                )
            )

        for poly in pcb.gr_polys:
            if _on_layer(poly, "Edge.Cuts"):
                continue
            layer = _get_layer(poly)
            sw = _stroke_width(poly)
            drawings.append(
                DrawingModel(
                    type="polygon",
                    points=[Point2(x=p.x, y=p.y) for p in poly.pts.xys],
                    width=sw,
                    layer=layer,
                    filled=_is_filled(poly),
                )
            )

        for curve in pcb.gr_curves:
            if _on_layer(curve, "Edge.Cuts"):
                continue
            layer = _get_layer(curve)
            sw = _stroke_width(curve)
            drawings.append(
                DrawingModel(
                    type="curve",
                    points=[Point2(x=p.x, y=p.y) for p in curve.pts.xys],
                    width=sw,
                    layer=layer,
                )
            )

        for tb in pcb.gr_text_boxes:
            if _is_hidden(tb) or not tb.border:
                continue
            sw = tb.stroke.width if tb.stroke else 0.12
            if tb.start is not None and tb.end is not None:
                drawings.append(
                    DrawingModel(
                        type="rect",
                        start=Point2(x=tb.start.x, y=tb.start.y),
                        end=Point2(x=tb.end.x, y=tb.end.y),
                        width=sw,
                        layer=tb.layer,
                    )
                )
            elif tb.pts is not None:
                drawings.append(
                    DrawingModel(
                        type="polygon",
                        points=[Point2(x=p.x, y=p.y) for p in tb.pts.xys],
                        width=sw,
                        layer=tb.layer,
                    )
                )

        for dimension in pcb.dimensions:
            if not dimension.pts.xys:
                continue
            thickness = (
                dimension.style.thickness
                if dimension.style is not None and dimension.style.thickness is not None
                else 0.12
            )
            drawings.append(
                DrawingModel(
                    type="curve",
                    points=[Point2(x=p.x, y=p.y) for p in dimension.pts.xys],
                    width=thickness,
                    layer=dimension.layer,
                )
            )

        for target in pcb.targets:
            half_x = target.size.x / 2
            half_y = target.size.y / 2
            width = target.width if target.width is not None else 0.12
            drawings.append(
                DrawingModel(
                    type="line",
                    start=Point2(x=target.at.x - half_x, y=target.at.y),
                    end=Point2(x=target.at.x + half_x, y=target.at.y),
                    width=width,
                    layer=target.layer,
                )
            )
            drawings.append(
                DrawingModel(
                    type="line",
                    start=Point2(x=target.at.x, y=target.at.y - half_y),
                    end=Point2(x=target.at.x, y=target.at.y + half_y),
                    width=width,
                    layer=target.layer,
                )
            )

        for table in pcb.tables:
            for cell in table.cells.table_cells:
                if _is_hidden(cell) or not cell.border:
                    continue
                sw = (
                    cell.stroke.width
                    if cell.stroke is not None and cell.stroke.width is not None
                    else (
                        table.border.stroke.width
                        if table.border is not None
                        and table.border.stroke is not None
                        and table.border.stroke.width is not None
                        else 0.12
                    )
                )
                if cell.start is not None and cell.end is not None:
                    drawings.append(
                        DrawingModel(
                            type="rect",
                            start=Point2(x=cell.start.x, y=cell.start.y),
                            end=Point2(x=cell.end.x, y=cell.end.y),
                            width=sw,
                            layer=cell.layer,
                        )
                    )
                elif cell.pts is not None:
                    drawings.append(
                        DrawingModel(
                            type="polygon",
                            points=[Point2(x=p.x, y=p.y) for p in cell.pts.xys],
                            width=sw,
                            layer=cell.layer,
                        )
                    )

        return drawings

    def _extract_global_texts(self, pcb: kicad.pcb.KicadPcb) -> list[TextModel]:
        texts: list[TextModel] = []
        for txt in pcb.gr_texts:
            if _is_hidden(txt):
                continue
            text_value = getattr(txt, "text", "")
            if not text_value.strip():
                continue
            texts.append(self._extract_text_entry(text_value, txt))

        for tb in pcb.gr_text_boxes:
            if _is_hidden(tb):
                continue
            if not tb.text.strip():
                continue
            texts.append(self._extract_text_box_text(tb))

        for dimension in pcb.dimensions:
            if _is_hidden(dimension.gr_text):
                continue
            text_value = getattr(dimension.gr_text, "text", "")
            if not text_value.strip():
                continue
            texts.append(self._extract_text_entry(text_value, dimension.gr_text))

        for table in pcb.tables:
            for cell in table.cells.table_cells:
                if _is_hidden(cell):
                    continue
                if not cell.text.strip():
                    continue
                texts.append(self._extract_table_cell_text(cell))

        return texts

    def _extract_text_box_text(self, tb) -> TextModel:
        at = _text_box_position(tb)
        effects = getattr(tb, "effects", None)
        font = getattr(effects, "font", None)
        font_size = getattr(font, "size", None)
        size: Size2 | None = None
        if (
            font_size is not None
            and getattr(font_size, "w", None) is not None
            and getattr(font_size, "h", None) is not None
        ):
            size = Size2(w=float(font_size.w), h=float(font_size.h))
        return TextModel(
            text=tb.text,
            at=at,
            layer=tb.layer,
            size=size,
            thickness=(
                float(font.thickness)
                if font is not None and getattr(font, "thickness", None) is not None
                else None
            ),
            justify=_extract_text_justify(tb),
        )

    def _extract_table_cell_text(self, cell) -> TextModel:
        at = _table_cell_position(cell)
        effects = getattr(cell, "effects", None)
        font = getattr(effects, "font", None)
        font_size = getattr(font, "size", None)
        size: Size2 | None = None
        if (
            font_size is not None
            and getattr(font_size, "w", None) is not None
            and getattr(font_size, "h", None) is not None
        ):
            size = Size2(w=float(font_size.w), h=float(font_size.h))
        return TextModel(
            text=cell.text,
            at=at,
            layer=cell.layer,
            size=size,
            thickness=(
                float(font.thickness)
                if font is not None and getattr(font, "thickness", None) is not None
                else None
            ),
            justify=_extract_text_justify(cell),
        )

    def _extract_text_entries(
        self, fp, reference: str | None, footprint_value: str | None
    ) -> list[TextModel]:
        texts: list[TextModel] = []

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
                    text=resolved,
                    obj=txt,
                )
            )

        return texts

    def _extract_text_entry(self, text: str, obj) -> TextModel:
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
            size = Size2(w=float(font_size.w), h=float(font_size.h))

        return TextModel(
            text=text,
            at=Point3(
                x=getattr(at, "x", 0.0),
                y=getattr(at, "y", 0.0),
                r=(getattr(at, "r", 0.0) or 0.0),
            ),
            layer=_text_layer_name(getattr(obj, "layer", None)),
            size=size,
            thickness=(
                float(font.thickness)
                if font is not None and getattr(font, "thickness", None) is not None
                else None
            ),
            justify=_extract_text_justify(obj),
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

    def _extract_zones(self, pcb: kicad.pcb.KicadPcb) -> list[ZoneModel]:
        raw_zones = getattr(pcb, "zones", None)
        if raw_zones is None:
            raw_zones = getattr(pcb, "zone", [])
        return [self._extract_zone(zone) for zone in raw_zones]

    def _extract_zone(self, zone) -> ZoneModel:
        layers = list(getattr(zone, "layers", []) or [])
        layer = getattr(zone, "layer", None)
        if not layers and layer:
            layers = [layer]

        polygon = getattr(zone, "polygon", None)
        polygon_pts = getattr(getattr(polygon, "pts", None), "xys", None)
        pts = (
            [Point2(x=p.x, y=p.y) for p in polygon_pts]
            if polygon_pts is not None
            else []
        )

        filled: list[FilledPolygonModel] = []
        raw_filled = getattr(zone, "filled_polygon", None)
        if raw_filled is None:
            raw_filled = getattr(zone, "filled_polygons", [])

        for fp in raw_filled:
            fp_pts = getattr(getattr(fp, "pts", None), "xys", None)
            if fp_pts is None:
                fp_polygon = getattr(fp, "polygon", None)
                fp_pts = getattr(getattr(fp_polygon, "pts", None), "xys", None)
            if fp_pts is None:
                continue

            fp_layer = getattr(fp, "layer", None)
            if fp_layer is None:
                fp_layers = getattr(fp, "layers", None)
                fp_layer = fp_layers[0] if fp_layers else (layers[0] if layers else "")
            if not fp_layer:
                continue

            filled.append(
                FilledPolygonModel(
                    layer=fp_layer,
                    points=[Point2(x=p.x, y=p.y) for p in fp_pts],
                )
            )

        hatch = getattr(zone, "hatch", None)
        hatch_mode = getattr(hatch, "mode", None)
        hatch_pitch = getattr(hatch, "pitch", None)
        zone_fill = getattr(zone, "fill", None)

        return ZoneModel(
            net=getattr(zone, "net", 0),
            net_name=getattr(zone, "net_name", ""),
            layers=layers,
            name=getattr(zone, "name", None),
            uuid=getattr(zone, "uuid", None),
            keepout=(getattr(zone, "keepout", None) is not None),
            hatch_mode=(str(hatch_mode).lower() if hatch_mode is not None else None),
            hatch_pitch=(float(hatch_pitch) if hatch_pitch is not None else None),
            fill_enabled=(
                _to_optional_bool(getattr(zone_fill, "enable", None))
                if zone_fill is not None
                else None
            ),
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


def _stroke_width(obj, default: float = 0.12) -> float:
    stroke = getattr(obj, "stroke", None)
    width = getattr(stroke, "width", None)
    if width is None:
        return default
    width_value = float(width)
    if width_value < 0:
        return 0.0
    return width_value


def _is_filled(obj) -> bool:
    fill = getattr(obj, "fill", None)
    if isinstance(fill, bool):
        return fill
    if fill is None:
        return False
    token = str(fill).strip().lower()
    return token in {"yes", "true", "solid", "fill"}


def _to_optional_bool(value) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    token = str(value).strip().lower()
    if token in {"yes", "true", "on", "enable", "enabled"}:
        return True
    if token in {"no", "false", "off", "disable", "disabled"}:
        return False
    return None


def _text_layer_name(layer_obj) -> str | None:
    if layer_obj is None:
        return None
    if isinstance(layer_obj, str):
        return layer_obj
    if hasattr(layer_obj, "layer") and layer_obj.layer:
        return layer_obj.layer
    return None


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


def _extract_text_justify(text_obj) -> list[str] | None:
    effects = getattr(text_obj, "effects", None)
    justify = getattr(effects, "justify", None)
    if justify is None:
        return None

    out: list[str] = []
    for attr in ("justify1", "justify2", "justify3"):
        value = getattr(justify, attr, None)
        if value is None:
            continue
        token = str(value).strip().lower()
        if token:
            out.append(token)
    return out or None


def _text_box_position(tb) -> Point3:
    if tb.start is not None and tb.end is not None:
        return Point3(
            x=(tb.start.x + tb.end.x) / 2,
            y=(tb.start.y + tb.end.y) / 2,
            r=float(tb.angle or 0),
        )
    if tb.pts is not None and tb.pts.xys:
        xs = [p.x for p in tb.pts.xys]
        ys = [p.y for p in tb.pts.xys]
        return Point3(
            x=(min(xs) + max(xs)) / 2,
            y=(min(ys) + max(ys)) / 2,
            r=float(tb.angle or 0),
        )
    return Point3(x=0, y=0, r=float(tb.angle or 0))


def _table_cell_position(cell) -> Point3:
    if cell.start is not None and cell.end is not None:
        return Point3(
            x=(cell.start.x + cell.end.x) / 2,
            y=(cell.start.y + cell.end.y) / 2,
            r=float(cell.angle or 0),
        )
    if cell.pts is not None and cell.pts.xys:
        xs = [p.x for p in cell.pts.xys]
        ys = [p.y for p in cell.pts.xys]
        return Point3(
            x=(min(xs) + max(xs)) / 2,
            y=(min(ys) + max(ys)) / 2,
            r=float(cell.angle or 0),
        )
    return Point3(x=0, y=0, r=float(cell.angle or 0))
