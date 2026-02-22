"""Manages loading, extracting render models, and editing a KiCad PCB file."""

from __future__ import annotations

import abc
import math
import time
from pathlib import Path

from atopile.layout_server.models import (
    ArcDrawingModel,
    BoardModel,
    CircleDrawingModel,
    CurveDrawingModel,
    DrawingModel,
    EdgeModel,
    FilledPolygonModel,
    FlipFootprintCommand,
    FlipFootprintsCommand,
    FootprintGroupModel,
    FootprintModel,
    FootprintSummary,
    HoleModel,
    LayerModel,
    LineDrawingModel,
    MoveFootprintCommand,
    MoveFootprintsCommand,
    PadModel,
    PadNameAnnotationModel,
    PadNumberAnnotationModel,
    PointXY,
    PointXYR,
    PolygonDrawingModel,
    RectDrawingModel,
    RenderModel,
    RotateFootprintCommand,
    RotateFootprintsCommand,
    Size2,
    TextModel,
    TrackModel,
    ZoneModel,
)
from faebryk.libs.kicad.fileformats import kicad
from faebryk.libs.util import not_none

TextUnion = kicad.pcb.Text | kicad.pcb.FpText | kicad.pcb.Property

# --- Actions for undo/redo ---


class Action(abc.ABC):
    """Base class for undoable actions."""

    @abc.abstractmethod
    def execute(self, pcb: kicad.pcb.KicadPcb) -> None: ...

    @abc.abstractmethod
    def undo(self, pcb: kicad.pcb.KicadPcb) -> None: ...


def _find_footprint_by_uuid(pcb: kicad.pcb.KicadPcb, uuid: str):
    for fp in pcb.footprints:
        if fp.uuid == uuid:
            return fp
    raise ValueError(f"Footprint with uuid {uuid!r} not found")


class _FootprintAction(Action):
    uuid: str

    def _find(self, pcb: kicad.pcb.KicadPcb):
        return _find_footprint_by_uuid(pcb, self.uuid)


class MoveAction(_FootprintAction):
    """Move a footprint to a new position."""

    def __init__(
        self, uuid: str, new_x: float, new_y: float, new_r: float | None
    ) -> None:
        self.uuid = uuid
        self.new = kicad.pcb.Xyr(x=new_x, y=new_y, r=new_r)
        # Saved on first execute
        self.old: kicad.pcb.Xyr | None = None

    def execute(self, pcb: kicad.pcb.KicadPcb) -> None:
        from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

        fp = self._find(pcb)
        # Copy the Xyr to avoid reference issues when move_fp modifies fp.at
        self.old = kicad.pcb.Xyr(x=fp.at.x, y=fp.at.y, r=fp.at.r)
        new = kicad.pcb.Xyr(
            x=self.new.x,
            y=self.new.y,
            # if r is None, just keep old one
            r=self.new.r if self.new.r is not None else fp.at.r,
        )
        PCB_Transformer.move_fp(fp, new, layer=fp.layer)

    def undo(self, pcb: kicad.pcb.KicadPcb) -> None:
        from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

        fp = self._find(pcb)
        assert self.old is not None
        PCB_Transformer.move_fp(fp, self.old, layer=fp.layer)


class RotateAction(_FootprintAction):
    """Rotate a footprint by a delta angle (degrees)."""

    def __init__(self, uuid: str, delta_degrees: float) -> None:
        self.uuid = uuid
        self.delta_degrees = delta_degrees

    def execute(self, pcb: kicad.pcb.KicadPcb) -> None:
        from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

        fp = self._find(pcb)
        PCB_Transformer.rotate_fp(fp, self.delta_degrees)

    def undo(self, pcb: kicad.pcb.KicadPcb) -> None:
        from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

        fp = self._find(pcb)
        PCB_Transformer.rotate_fp(fp, -self.delta_degrees)


class FlipAction(_FootprintAction):
    """Flip a footprint between front and back."""

    def __init__(self, uuid: str) -> None:
        self.uuid = uuid

    def _flip(self, pcb: kicad.pcb.KicadPcb) -> None:
        from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

        fp = self._find(pcb)
        PCB_Transformer._flip_obj(fp)

    def execute(self, pcb: kicad.pcb.KicadPcb) -> None:
        self._flip(pcb)

    def undo(self, pcb: kicad.pcb.KicadPcb) -> None:
        self._flip(pcb)  # Flip is its own inverse


class CompositeAction(Action):
    """Execute multiple actions as a single undo/redo unit."""

    def __init__(self, actions: list[Action]) -> None:
        self.actions = actions

    def execute(self, pcb: kicad.pcb.KicadPcb) -> None:
        for action in self.actions:
            action.execute(pcb)

    def undo(self, pcb: kicad.pcb.KicadPcb) -> None:
        for action in reversed(self.actions):
            print(f"Undoing action: {action}")
            action.undo(pcb)


# --- PcbManager ---


class PcbManager:
    def __init__(self) -> None:
        self._path: Path | None = None
        self._pcb_file: kicad.pcb.PcbFile | None = None
        self._undo_stack: list[Action] = []
        self._redo_stack: list[Action] = []
        self._last_save_time: float = 0
        self._render_model_cache: RenderModel | None = None

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
        self._render_model_cache = None

    # --- Action execution ---

    def execute_action(self, action: Action) -> None:
        action.execute(self.pcb)
        self._undo_stack.append(action)
        self._redo_stack.clear()
        self._render_model_cache = None

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        action = self._undo_stack.pop()
        action.undo(self.pcb)
        self._redo_stack.append(action)
        self._render_model_cache = None
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        action = self._redo_stack.pop()
        action.execute(self.pcb)
        self._undo_stack.append(action)
        self._render_model_cache = None
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
        self.execute_action(MoveAction(uuid, x, y, r or 0))

    def rotate_footprint(self, uuid: str, delta_degrees: float) -> None:
        self.execute_action(RotateAction(uuid, delta_degrees))

    def flip_footprint(self, uuid: str) -> None:
        self.execute_action(FlipAction(uuid))

    def move_footprints(self, uuids: list[str], dx: float, dy: float) -> None:
        targets = self._footprints_from_uuids(uuids)
        if not targets:
            return
        actions: list[Action] = []
        for fp in targets:
            if fp.uuid is None:
                continue
            actions.append(
                MoveAction(
                    uuid=fp.uuid,
                    new_x=fp.at.x + dx,
                    new_y=fp.at.y + dy,
                    new_r=fp.at.r or 0,
                )
            )
        if actions:
            self.execute_action(CompositeAction(actions))

    def rotate_footprints(self, uuids: list[str], delta_degrees: float) -> None:
        targets = self._footprints_from_uuids(uuids)
        if not targets:
            return
        cx = sum(fp.at.x for fp in targets) / len(targets)
        cy = sum(fp.at.y for fp in targets) / len(targets)

        actions: list[Action] = []
        for fp in targets:
            if fp.uuid is None:
                continue
            # vector from center of group to footprint
            dx = fp.at.x - cx
            dy = fp.at.y - cy
            # rotate vector using KiCad screen-space rotation convention
            # (clockwise-positive in rendered view), matching single-footprint rotate.
            rdx, rdy = _rotate_kicad_xy(dx, dy, delta_degrees)
            new_x = cx + rdx
            new_y = cy + rdy

            new_r = ((fp.at.r or 0.0) + delta_degrees) % 360.0
            actions.append(
                MoveAction(
                    uuid=fp.uuid,
                    new_x=new_x,
                    new_y=new_y,
                    new_r=new_r,
                )
            )
        if actions:
            self.execute_action(CompositeAction(actions))

    def flip_footprints(self, uuids: list[str]) -> None:
        targets = self._footprints_from_uuids(uuids)
        if not targets:
            return
        cx = sum(fp.at.x for fp in targets) / len(targets)
        actions: list[Action] = []
        for fp in targets:
            if fp.uuid is None:
                continue
            mirrored_x = 2.0 * cx - fp.at.x
            actions.append(FlipAction(fp.uuid))
            actions.append(
                MoveAction(
                    uuid=fp.uuid,
                    new_x=mirrored_x,
                    new_y=fp.at.y,
                    # keep post-flip rotation
                    new_r=None,
                )
            )
        if actions:
            self.execute_action(CompositeAction(actions))

    def dispatch_action(
        self,
        request: MoveFootprintCommand
        | RotateFootprintCommand
        | FlipFootprintCommand
        | MoveFootprintsCommand
        | RotateFootprintsCommand
        | FlipFootprintsCommand,
    ) -> None:
        """Execute a typed v2 action request."""
        if isinstance(request, MoveFootprintCommand):
            self.move_footprint(request.uuid, request.x, request.y, request.r)
            return
        if isinstance(request, RotateFootprintCommand):
            self.rotate_footprint(request.uuid, request.delta_degrees)
            return
        if isinstance(request, FlipFootprintCommand):
            self.flip_footprint(request.uuid)
            return
        if isinstance(request, MoveFootprintsCommand):
            self.move_footprints(
                uuids=[uuid for uuid in request.uuids if uuid.strip()],
                dx=request.dx,
                dy=request.dy,
            )
            return
        if isinstance(request, RotateFootprintsCommand):
            self.rotate_footprints(
                uuids=[uuid for uuid in request.uuids if uuid.strip()],
                delta_degrees=request.delta_degrees,
            )
            return
        if isinstance(request, FlipFootprintsCommand):
            self.flip_footprints(uuids=[uuid for uuid in request.uuids if uuid.strip()])
            return

    def was_recently_saved(self, threshold: float = 2.0) -> bool:
        """Check if we saved within the last `threshold` seconds."""
        return (time.monotonic() - self._last_save_time) < threshold

    def save(self) -> None:
        assert self._path is not None and self._pcb_file is not None
        kicad.dumps(self._pcb_file, self._path)
        self._last_save_time = time.monotonic()

    # --- Extraction ---

    def get_render_model(self) -> RenderModel:
        if self._render_model_cache is not None:
            return self._render_model_cache
        pcb = self.pcb
        all_layers = _board_all_layers(pcb)
        copper_layers = _board_copper_layers(pcb)
        global_texts = self._extract_global_texts(pcb)
        via_drawings = self._synthesize_via_drawings(pcb.vias, copper_layers)
        net_names_by_number = {
            net.number: not_none(net.name) for net in pcb.nets if net.name
        }
        model = RenderModel(
            board=self._extract_board(pcb),
            drawings=[*self._extract_global_drawings(pcb), *via_drawings],
            texts=global_texts,
            footprints=[
                self._extract_footprint(
                    fp,
                    net_names_by_number,
                    copper_layers,
                    all_layers,
                )
                for fp in pcb.footprints
            ],
            footprint_groups=self._extract_footprint_groups(pcb),
            tracks=[
                *[self._extract_segment(seg) for seg in pcb.segments],
                *[self._extract_arc_segment(arc) for arc in pcb.arcs],
            ],
            zones=self._extract_zones(pcb, all_layers),
        )
        model.layers = _build_layer_models(model, all_layers, copper_layers)
        self._render_model_cache = model
        return model

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

    def _footprints_from_uuids(self, uuids: list[str]) -> list[kicad.pcb.Footprint]:
        wanted = {uuid for uuid in uuids if uuid}
        if not wanted:
            return []
        by_uuid = {fp.uuid: fp for fp in self.pcb.footprints if fp.uuid is not None}
        ordered: list[kicad.pcb.Footprint] = []
        seen: set[str] = set()
        for uuid in uuids:
            if uuid in seen:
                continue
            fp = by_uuid.get(uuid)
            if fp is None:
                continue
            seen.add(uuid)
            ordered.append(fp)
        return ordered

    def _extract_footprint_groups(
        self, pcb: kicad.pcb.KicadPcb
    ) -> list[FootprintGroupModel]:
        footprints_by_uuid = {fp.uuid for fp in pcb.footprints if fp.uuid is not None}
        groups: list[FootprintGroupModel] = []
        for group in pcb.groups:
            member_uuids: list[str] = []
            seen_members: set[str] = set()
            for member in group.members:
                token = member.strip()
                if not token or token in seen_members:
                    continue
                if token not in footprints_by_uuid:
                    continue
                seen_members.add(token)
                member_uuids.append(token)
            if len(member_uuids) < 2:
                continue
            groups.append(
                FootprintGroupModel(
                    uuid=((group.uuid or "").strip() or None),
                    name=((group.name or "").strip() or None),
                    member_uuids=member_uuids,
                )
            )
        return groups

    def _extract_board(self, pcb: kicad.pcb.KicadPcb) -> BoardModel:
        edges: list[EdgeModel] = []
        for line in pcb.gr_lines:
            if _on_layer(line, "Edge.Cuts"):
                edges.append(
                    EdgeModel(
                        type="line",
                        start=PointXY(x=line.start.x, y=line.start.y),
                        end=PointXY(x=line.end.x, y=line.end.y),
                    )
                )
        for arc in pcb.gr_arcs:
            if _on_layer(arc, "Edge.Cuts"):
                edges.append(
                    EdgeModel(
                        type="arc",
                        start=PointXY(x=arc.start.x, y=arc.start.y),
                        mid=PointXY(x=arc.mid.x, y=arc.mid.y),
                        end=PointXY(x=arc.end.x, y=arc.end.y),
                    )
                )
        for circle in pcb.gr_circles:
            if _on_layer(circle, "Edge.Cuts"):
                edges.append(
                    EdgeModel(
                        type="circle",
                        center=PointXY(x=circle.center.x, y=circle.center.y),
                        end=PointXY(x=circle.end.x, y=circle.end.y),
                    )
                )
        for rect in pcb.gr_rects:
            if _on_layer(rect, "Edge.Cuts"):
                edges.append(
                    EdgeModel(
                        type="rect",
                        start=PointXY(x=rect.start.x, y=rect.start.y),
                        end=PointXY(x=rect.end.x, y=rect.end.y),
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
            origin=PointXY(x=origin_x, y=origin_y),
        )

    def _extract_footprint(
        self,
        fp: kicad.pcb.Footprint,
        net_names_by_number: dict[int, str],
        copper_layers: list[str],
        all_layers: list[str],
    ) -> FootprintModel:
        ref = _get_property(fp, "Reference")
        value = _get_property(fp, "Value")

        pads: list[PadModel] = []
        fp_rotation = fp.at.r or 0
        for pad in fp.pads:
            pad_h = pad.size.h if pad.size.h is not None else pad.size.w
            pad_layers = _expand_layer_rules(list(pad.layers), known_layers=all_layers)
            # KiCad stores pad rotation as absolute in PCB coordinates, but x/y
            # are relative to the footprint. Convert rotation to be relative to
            # the footprint so the frontend can treat it as a sub-coordinate system.
            pad_relative_r = ((pad.at.r or 0) - fp_rotation) % 360
            pads.append(
                PadModel(
                    name=pad.name,
                    at=PointXYR(x=pad.at.x, y=pad.at.y, r=pad_relative_r),
                    size=Size2(w=pad.size.w, h=pad_h),
                    shape=pad.shape,
                    type=pad.type,
                    layers=pad_layers,
                    net=pad.net.number if pad.net else 0,
                    hole=self._extract_pad_hole(pad),
                    roundrect_rratio=pad.roundrect_rratio,
                )
            )

        drawings = self._extract_drawing_primitives(
            lines=fp.fp_lines,
            arcs=fp.fp_arcs,
            circles=fp.fp_circles,
            rects=fp.fp_rects,
            polygons=fp.fp_poly,
            curves=getattr(fp, "fp_curves", []),  # Not in typed model
        )

        texts = self._extract_text_entries(fp, ref, value)
        pad_names = self._extract_pad_name_annotations_for_footprint(
            fp,
            net_names_by_number,
            copper_layers,
        )
        pad_numbers = self._extract_pad_number_annotations_for_footprint(
            fp, copper_layers
        )

        return FootprintModel(
            uuid=fp.uuid,
            name=fp.name,
            reference=ref,
            value=value,
            at=PointXYR(x=fp.at.x, y=fp.at.y, r=fp.at.r or 0),
            layer=fp.layer,
            pads=pads,
            drawings=drawings,
            texts=texts,
            pad_names=pad_names,
            pad_numbers=pad_numbers,
        )

    def _extract_global_drawings(self, pcb: kicad.pcb.KicadPcb) -> list[DrawingModel]:
        drawings = self._extract_drawing_primitives(
            lines=pcb.gr_lines,
            arcs=pcb.gr_arcs,
            circles=pcb.gr_circles,
            rects=pcb.gr_rects,
            polygons=pcb.gr_polys,
            curves=pcb.gr_curves,
            skip_edge_cuts=True,
        )

        for tb in pcb.gr_text_boxes:
            if _is_hidden(tb) or not tb.border:
                continue
            sw = tb.stroke.width if tb.stroke else 0.12
            if tb.start is not None and tb.end is not None:
                drawings.append(
                    _rect_drawing(
                        start=PointXY(x=tb.start.x, y=tb.start.y),
                        end=PointXY(x=tb.end.x, y=tb.end.y),
                        width=sw,
                        layer=tb.layer,
                    )
                )
            elif tb.pts is not None:
                drawings.append(
                    _polygon_drawing(
                        points=[PointXY(x=p.x, y=p.y) for p in tb.pts.xys],
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
                _curve_drawing(
                    points=[PointXY(x=p.x, y=p.y) for p in dimension.pts.xys],
                    width=thickness,
                    layer=dimension.layer,
                )
            )

        for target in pcb.targets:
            half_x = target.size.x / 2
            half_y = target.size.y / 2
            width = target.width if target.width is not None else 0.12
            drawings.append(
                _line_drawing(
                    start=PointXY(x=target.at.x - half_x, y=target.at.y),
                    end=PointXY(x=target.at.x + half_x, y=target.at.y),
                    width=width,
                    layer=target.layer,
                )
            )
            drawings.append(
                _line_drawing(
                    start=PointXY(x=target.at.x, y=target.at.y - half_y),
                    end=PointXY(x=target.at.x, y=target.at.y + half_y),
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
                    if cell.stroke is not None
                    else table.border.stroke.width
                )
                if cell.start is not None and cell.end is not None:
                    drawings.append(
                        _rect_drawing(
                            start=PointXY(x=cell.start.x, y=cell.start.y),
                            end=PointXY(x=cell.end.x, y=cell.end.y),
                            width=sw,
                            layer=cell.layer,
                        )
                    )
                elif cell.pts is not None:
                    drawings.append(
                        _polygon_drawing(
                            points=[PointXY(x=p.x, y=p.y) for p in cell.pts.xys],
                            width=sw,
                            layer=cell.layer,
                        )
                    )

        return drawings

    def _extract_drawing_primitives(
        self,
        *,
        lines: list[kicad.pcb.Line],
        arcs: list[kicad.pcb.Arc],
        circles: list[kicad.pcb.Circle],
        rects: list[kicad.pcb.Rect],
        polygons: list[kicad.pcb.Polygon],
        curves: list[kicad.pcb.Curve],
        skip_edge_cuts: bool = False,
    ) -> list[DrawingModel]:
        drawings: list[DrawingModel] = []

        for line in lines:
            if skip_edge_cuts and _on_layer(line, "Edge.Cuts"):
                continue
            drawings.append(
                _line_drawing(
                    start=PointXY(x=line.start.x, y=line.start.y),
                    end=PointXY(x=line.end.x, y=line.end.y),
                    width=_stroke_width(line),
                    layer=_get_layer(line),
                )
            )

        for arc in arcs:
            if skip_edge_cuts and _on_layer(arc, "Edge.Cuts"):
                continue
            drawings.append(
                _arc_drawing(
                    start=PointXY(x=arc.start.x, y=arc.start.y),
                    mid=PointXY(x=arc.mid.x, y=arc.mid.y),
                    end=PointXY(x=arc.end.x, y=arc.end.y),
                    width=_stroke_width(arc),
                    layer=_get_layer(arc),
                )
            )

        for circle in circles:
            if skip_edge_cuts and _on_layer(circle, "Edge.Cuts"):
                continue
            drawings.append(
                _circle_drawing(
                    center=PointXY(x=circle.center.x, y=circle.center.y),
                    end=PointXY(x=circle.end.x, y=circle.end.y),
                    width=_stroke_width(circle),
                    layer=_get_layer(circle),
                    filled=_is_filled(circle),
                )
            )

        for rect in rects:
            if skip_edge_cuts and _on_layer(rect, "Edge.Cuts"):
                continue
            drawings.append(
                _rect_drawing(
                    start=PointXY(x=rect.start.x, y=rect.start.y),
                    end=PointXY(x=rect.end.x, y=rect.end.y),
                    width=_stroke_width(rect),
                    layer=_get_layer(rect),
                    filled=_is_filled(rect),
                )
            )

        for poly in polygons:
            if skip_edge_cuts and _on_layer(poly, "Edge.Cuts"):
                continue
            drawings.append(
                _polygon_drawing(
                    points=[PointXY(x=p.x, y=p.y) for p in poly.pts.xys],
                    width=_stroke_width(poly),
                    layer=_get_layer(poly),
                    filled=_is_filled(poly),
                )
            )

        for curve in curves:
            if skip_edge_cuts and _on_layer(curve, "Edge.Cuts"):
                continue
            drawings.append(
                _curve_drawing(
                    points=[PointXY(x=p.x, y=p.y) for p in curve.pts.xys],
                    width=_stroke_width(curve),
                    layer=_get_layer(curve),
                )
            )

        return drawings

    def _extract_global_texts(self, pcb: kicad.pcb.KicadPcb) -> list[TextModel]:
        texts: list[TextModel] = []
        for txt in pcb.gr_texts:
            if _is_hidden(txt):
                continue
            if not txt.text.strip():
                continue
            texts.append(self._extract_text_entry(txt.text, txt))

        for tb in pcb.gr_text_boxes:
            if _is_hidden(tb):
                continue
            if not tb.text.strip():
                continue
            texts.append(self._extract_text_box_text(tb))

        for dimension in pcb.dimensions:
            if _is_hidden(dimension.gr_text):
                continue
            if not dimension.gr_text.text.strip():
                continue
            texts.append(
                self._extract_text_entry(dimension.gr_text.text, dimension.gr_text)
            )

        for table in pcb.tables:
            for cell in table.cells.table_cells:
                if _is_hidden(cell):
                    continue
                if not cell.text.strip():
                    continue
                texts.append(self._extract_table_cell_text(cell))

        return texts

    def _extract_text_box_text(self, tb: kicad.pcb.TextBox) -> TextModel:
        at = _text_box_position(tb)
        font = tb.effects.font
        font_size = font.size
        size: Size2 | None = None
        if font_size.h is not None:
            size = Size2(w=float(font_size.w), h=float(font_size.h))
        return TextModel(
            text=tb.text,
            at=at,
            layer=tb.layer,
            size=size,
            thickness=(float(font.thickness) if font.thickness is not None else None),
            justify=_extract_text_justify(tb.effects),
        )

    def _extract_pad_name_annotations_for_footprint(
        self,
        fp: kicad.pcb.Footprint,
        net_names_by_number: dict[int, str],
        copper_layers: list[str],
    ) -> list[PadNameAnnotationModel]:
        out: list[PadNameAnnotationModel] = []
        for pad_index, pad in enumerate(fp.pads):
            pad_name = pad.name.strip()
            if not pad_name:
                continue
            text_layer_ids = _pad_net_text_layers(
                pad.layers,
                all_copper_layers=copper_layers,
            )
            if not text_layer_ids:
                continue
            pad_net = pad.net
            if pad_net is None:
                continue
            net_number = pad_net.number
            if net_number <= 0:
                continue
            net_name = (pad_net.name or "").strip()
            if not net_name:
                net_name = (net_names_by_number.get(net_number) or "").strip()
            if not net_name:
                continue
            out.append(
                PadNameAnnotationModel(
                    pad_index=pad_index,
                    pad=pad_name,
                    text=net_name,
                    layer_ids=text_layer_ids,
                )
            )
        return out

    def _extract_pad_number_annotations_for_footprint(
        self, fp: kicad.pcb.Footprint, copper_layers: list[str]
    ) -> list[PadNumberAnnotationModel]:
        out: list[PadNumberAnnotationModel] = []
        for pad_index, pad in enumerate(fp.pads):
            pad_name = pad.name.strip()
            if not pad_name:
                continue
            text_layer_ids = _pad_number_text_layers(
                list(pad.layers),
                all_copper_layers=copper_layers,
            )
            if not text_layer_ids:
                continue
            out.append(
                PadNumberAnnotationModel(
                    pad_index=pad_index,
                    pad=pad_name,
                    text=pad_name,
                    layer_ids=text_layer_ids,
                )
            )
        return out

    def _extract_table_cell_text(self, cell: kicad.pcb.TableCell) -> TextModel:
        at = _table_cell_position(cell)
        font = cell.effects.font
        font_size = font.size
        size: Size2 | None = None
        if font_size.h is not None:
            size = Size2(w=float(font_size.w), h=float(font_size.h))
        return TextModel(
            text=cell.text,
            at=at,
            layer=cell.layer,
            size=size,
            thickness=(float(font.thickness) if font.thickness is not None else None),
            justify=_extract_text_justify(cell.effects),
        )

    def _extract_text_entries(
        self,
        fp: kicad.pcb.Footprint,
        reference: str | None,
        footprint_value: str | None,
    ) -> list[TextModel]:
        texts: list[TextModel] = []

        for prop in fp.propertys:
            if _is_hidden(prop):
                continue
            resolved = _resolve_text_tokens(prop.value, reference, footprint_value)
            if not resolved.strip():
                continue
            texts.append(self._extract_text_entry(text=resolved, obj=prop))

        for txt in fp.fp_texts:
            if _is_hidden(txt):
                continue
            resolved = _resolve_text_tokens(txt.text, reference, footprint_value)
            if not resolved.strip():
                continue
            texts.append(self._extract_text_entry(text=resolved, obj=txt))

        return texts

    def _extract_text_entry(self, text: str, obj: TextUnion) -> TextModel:
        at = obj.at
        effects = obj.effects
        font = effects.font if effects is not None else None
        font_size = font.size if font is not None else None
        size: Size2 | None = None
        if font_size is not None and font_size.h is not None:
            size = Size2(w=float(font_size.w), h=float(font_size.h))

        return TextModel(
            text=text,
            at=PointXYR(x=at.x, y=at.y, r=(at.r or 0.0)),
            layer=_text_layer_name(obj.layer),
            size=size,
            thickness=(
                float(font.thickness)
                if font is not None and font.thickness is not None
                else None
            ),
            justify=_extract_text_justify(effects),
        )

    def _extract_pad_hole(self, pad: kicad.pcb.Pad) -> HoleModel | None:
        drill = pad.drill
        if drill is None:
            return None
        size_x = drill.size_x
        size_y = drill.size_y
        if size_x is None and size_y is None:
            return None
        if size_x is None:
            size_x = size_y
        if size_y is None:
            size_y = size_x
        if size_x is None or size_y is None or size_x <= 0 or size_y <= 0:
            return None

        offset: PointXY | None = None
        if drill.offset is not None:
            offset = PointXY(x=drill.offset.x, y=drill.offset.y)

        plated = pad.type != "np_thru_hole" if pad.type else None

        return HoleModel(
            shape=_normalize_hole_shape(drill.shape, size_x, size_y),
            size_x=size_x,
            size_y=size_y,
            offset=offset,
            plated=plated,
        )

    def _extract_segment(self, seg: kicad.pcb.Segment) -> TrackModel:
        return TrackModel(
            start=PointXY(x=seg.start.x, y=seg.start.y),
            end=PointXY(x=seg.end.x, y=seg.end.y),
            width=seg.width,
            layer=seg.layer,
            net=seg.net,
            uuid=seg.uuid,
        )

    def _extract_arc_segment(self, arc: kicad.pcb.ArcSegment) -> TrackModel:
        return TrackModel(
            start=PointXY(x=arc.start.x, y=arc.start.y),
            mid=PointXY(x=arc.mid.x, y=arc.mid.y),
            end=PointXY(x=arc.end.x, y=arc.end.y),
            width=arc.width,
            layer=arc.layer,
            net=arc.net,
            uuid=arc.uuid,
        )

    def _synthesize_via_drawings(
        self, vias: list[kicad.pcb.Via], copper_layers: list[str]
    ) -> list[DrawingModel]:
        drawings: list[DrawingModel] = []
        for via in vias:
            cx = via.at.x
            cy = via.at.y

            drill = via.drill
            hole: HoleModel | None = None
            if drill > 0:
                hole = HoleModel(
                    shape=_normalize_hole_shape(
                        getattr(via, "drillshape", None), drill, drill
                    ),
                    size_x=drill,
                    size_y=drill,
                    offset=None,
                    plated=True,
                )

            outer_diameter = via.size
            drill_diameter = 0.0
            if hole is not None:
                hx = _safe_float(hole.size_x) or 0.0
                hy = _safe_float(hole.size_y) or hx
                drill_diameter = max(hx, hy)
            if drill_diameter <= 0:
                drill_diameter = drill

            via_layers = list(via.layers)
            expanded_copper_layers = _expand_copper_layers(
                via_layers,
                all_copper_layers=copper_layers,
                include_between=True,
            )
            for copper_layer in expanded_copper_layers:
                if outer_diameter <= 0:
                    continue
                if drill_diameter > 0 and outer_diameter > drill_diameter:
                    annulus_thickness = (outer_diameter - drill_diameter) / 2.0
                    centerline_radius = (outer_diameter + drill_diameter) / 4.0
                    if annulus_thickness > 0 and centerline_radius > 0:
                        drawings.append(
                            _circle_drawing(
                                center=PointXY(x=cx, y=cy),
                                end=PointXY(x=cx + centerline_radius, y=cy),
                                width=annulus_thickness,
                                layer=copper_layer,
                                filled=False,
                            )
                        )
                        continue
                drawings.append(
                    _circle_drawing(
                        center=PointXY(x=cx, y=cy),
                        end=PointXY(x=cx + outer_diameter / 2.0, y=cy),
                        width=0.0,
                        layer=copper_layer,
                        filled=True,
                    )
                )

            if hole is None:
                continue
            for drill_layer in _drill_layers_from_copper_layers(
                expanded_copper_layers,
                all_copper_layers=copper_layers,
                include_between=False,
            ):
                drawings.extend(
                    _drill_hole_drawings(
                        cx=cx,
                        cy=cy,
                        rotation_deg=0.0,
                        hole=hole,
                        layer=drill_layer,
                    )
                )
        return drawings

    def _extract_zones(
        self, pcb: kicad.pcb.KicadPcb, all_layers: list[str]
    ) -> list[ZoneModel]:
        return [self._extract_zone(zone, all_layers) for zone in pcb.zones]

    def _extract_zone(self, zone: kicad.pcb.Zone, all_layers: list[str]) -> ZoneModel:
        layers = list(zone.layers)
        if not layers and zone.layer:
            layers = [zone.layer]
        layers = _expand_layer_rules(layers, known_layers=all_layers)

        pts = [PointXY(x=p.x, y=p.y) for p in zone.polygon.pts.xys]

        filled: list[FilledPolygonModel] = []
        for fp in zone.filled_polygon:
            if not fp.layer:
                continue
            filled.append(
                FilledPolygonModel(
                    layer=fp.layer,
                    points=[PointXY(x=p.x, y=p.y) for p in fp.pts.xys],
                )
            )

        hatch = zone.hatch
        zone_fill = zone.fill

        return ZoneModel(
            net=zone.net,
            net_name=zone.net_name,
            layers=layers,
            name=zone.name,
            uuid=zone.uuid,
            keepout=(zone.keepout is not None),
            hatch_mode=hatch.mode.lower() if hatch.mode else None,
            hatch_pitch=hatch.pitch,
            fill_enabled=(
                _to_optional_bool(zone_fill.enable) if zone_fill is not None else None
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


def _line_drawing(
    *,
    start: PointXY,
    end: PointXY,
    width: float,
    layer: str | None,
    filled: bool = False,
) -> DrawingModel:
    return LineDrawingModel(
        start=start,
        end=end,
        width=width,
        layer=layer,
        filled=filled,
    )


def _arc_drawing(
    *,
    start: PointXY,
    mid: PointXY,
    end: PointXY,
    width: float,
    layer: str | None,
    filled: bool = False,
) -> DrawingModel:
    return ArcDrawingModel(
        start=start,
        mid=mid,
        end=end,
        width=width,
        layer=layer,
        filled=filled,
    )


def _circle_drawing(
    *,
    center: PointXY,
    end: PointXY,
    width: float,
    layer: str | None,
    filled: bool = False,
) -> DrawingModel:
    return CircleDrawingModel(
        center=center,
        end=end,
        width=width,
        layer=layer,
        filled=filled,
    )


def _rect_drawing(
    *,
    start: PointXY,
    end: PointXY,
    width: float,
    layer: str | None,
    filled: bool = False,
) -> DrawingModel:
    return RectDrawingModel(
        start=start,
        end=end,
        width=width,
        layer=layer,
        filled=filled,
    )


def _polygon_drawing(
    *, points: list[PointXY], width: float, layer: str | None, filled: bool = False
) -> DrawingModel:
    return PolygonDrawingModel(
        points=points,
        width=width,
        layer=layer,
        filled=filled,
    )


def _curve_drawing(
    *, points: list[PointXY], width: float, layer: str | None, filled: bool = False
) -> DrawingModel:
    return CurveDrawingModel(
        points=points,
        width=width,
        layer=layer,
        filled=filled,
    )


PAD_NET_FIT_MARGIN = 0.78
PAD_NET_MAJOR_FIT = 0.96
PAD_NET_MINOR_FIT = 0.88
PAD_NET_CHAR_SCALE = 0.60
PAD_NET_MIN_CHAR_H = 0.11
PAD_NET_CHAR_W_RATIO = 0.72
PAD_NET_STROKE_SCALE = 0.30
PAD_NET_STROKE_MIN = 0.06
PAD_NET_STROKE_MAX = 0.20
PAD_NET_GENERIC_TOKENS = {"input", "output", "line", "net"}
PAD_NET_PREFIXES = ("power_in-", "power_vbus-", "power-")
PAD_NET_TRUNCATE_LENGTHS = (16, 12, 10, 8, 6, 5, 4, 3, 2, 1)


def _pad_net_text_layers(
    pad_layers: list[str] | None, *, all_copper_layers: list[str]
) -> list[str]:
    copper_layers = _expand_copper_layers(
        pad_layers,
        all_copper_layers=all_copper_layers,
    )
    return [layer[:-3] + ".Nets" for layer in copper_layers if layer.endswith(".Cu")]


def _pad_number_text_layers(
    pad_layers: list[str] | None, *, all_copper_layers: list[str]
) -> list[str]:
    copper_layers = _expand_copper_layers(
        pad_layers,
        all_copper_layers=all_copper_layers,
    )
    return [
        layer[:-3] + ".PadNumbers" for layer in copper_layers if layer.endswith(".Cu")
    ]


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


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _rotate_kicad_xy(x: float, y: float, rotation_deg: float) -> tuple[float, float]:
    # Match frontend's KiCad rotation convention (clockwise in screen space).
    rad = math.radians(-(rotation_deg or 0.0))
    cos_t = math.cos(rad)
    sin_t = math.sin(rad)
    return (x * cos_t - y * sin_t, x * sin_t + y * cos_t)


def _board_copper_layers(pcb: kicad.pcb.KicadPcb) -> list[str]:
    copper: list[str] = []
    seen: set[str] = set()
    for layer in pcb.layers:
        name = layer.name
        if not name.endswith(".Cu"):
            continue
        if name in seen:
            continue
        seen.add(name)
        # Keep PCB file layer order; this reflects stack/root ordering
        # (e.g. F, In1, In2, B) better than numeric IDs.
        copper.append(name)
    if not copper:
        return ["F.Cu", "B.Cu"]
    return copper


def _board_all_layers(pcb: kicad.pcb.KicadPcb) -> list[str]:
    layers: list[str] = []
    seen: set[str] = set()
    for layer in pcb.layers:
        name = layer.name.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        layers.append(name)
    if not layers:
        return ["F.Cu", "B.Cu", "F.Mask", "B.Mask", "F.SilkS", "B.SilkS", "Edge.Cuts"]
    return layers


def _expand_layer_rules(
    layers: list[str] | None,
    *,
    known_layers: list[str],
) -> list[str]:
    if not layers:
        return []
    out: list[str] = []
    seen: set[str] = set()
    known_set = set(known_layers)

    def add(layer: str) -> None:
        token = layer.strip()
        if not token or token in seen:
            return
        seen.add(token)
        out.append(token)

    for layer in layers:
        token = (layer or "").strip()
        if not token:
            continue

        if "*" in token:
            dot_idx = token.find(".")
            suffix = token[dot_idx:] if dot_idx >= 0 else ""
            expanded = [
                name for name in known_layers if suffix and name.endswith(suffix)
            ]
            for candidate in expanded:
                add(candidate)
            continue

        if "&" in token and "." in token:
            dot_idx = token.find(".")
            prefixes = token[:dot_idx].split("&")
            suffix = token[dot_idx:]
            for prefix in prefixes:
                candidate = f"{prefix}{suffix}".strip()
                if candidate in known_set:
                    add(candidate)
            continue

        add(token)

    return out


_LAYER_COLOR_OVERRIDES: dict[str, tuple[float, float, float, float]] = {
    "F.Cu": (0.86, 0.23, 0.22, 0.88),
    "B.Cu": (0.16, 0.28, 0.47, 0.88),
    "In1.Cu": (0.70, 0.58, 0.24, 0.78),
    "In2.Cu": (0.53, 0.40, 0.70, 0.78),
    "F.SilkS": (0.92, 0.90, 0.62, 0.95),
    "B.SilkS": (0.78, 0.86, 0.87, 0.92),
    "F.Mask": (0.70, 0.35, 0.48, 0.42),
    "B.Mask": (0.12, 0.19, 0.34, 0.38),
    "F.Paste": (0.90, 0.80, 0.60, 0.48),
    "B.Paste": (0.66, 0.74, 0.86, 0.48),
    "F.Fab": (0.95, 0.62, 0.45, 0.90),
    "B.Fab": (0.62, 0.73, 0.90, 0.90),
    "F.CrtYd": (0.91, 0.91, 0.91, 0.62),
    "B.CrtYd": (0.80, 0.85, 0.93, 0.62),
    "Edge.Cuts": (0.93, 0.95, 0.95, 1.00),
    "Dwgs.User": (0.70, 0.70, 0.72, 0.65),
    "Cmts.User": (0.74, 0.66, 0.84, 0.65),
}

_LAYER_KIND_PANEL_PRIORITY: dict[str, int] = {
    "Cu": 0,
    "Drill": 1,
    "Fab": 2,
    "Mask": 3,
    "Nets": 4,
    "PadNumbers": 5,
    "Paste": 6,
    "SilkS": 7,
    "User": 8,
    "Cuts": 9,
}


def _collect_scene_layers(model: RenderModel) -> set[str]:
    layer_ids: set[str] = set()
    layer_ids.add("Edge.Cuts")
    for drawing in model.drawings:
        if drawing.layer:
            layer_ids.add(drawing.layer)
    for text in model.texts:
        if text.layer:
            layer_ids.add(text.layer)
    for track in model.tracks:
        if track.layer:
            layer_ids.add(track.layer)
    for zone in model.zones:
        layer_ids.update(zone.layers)
        for filled in zone.filled_polygons:
            if filled.layer:
                layer_ids.add(filled.layer)
    for fp in model.footprints:
        if fp.layer:
            layer_ids.add(fp.layer)
        for pad in fp.pads:
            layer_ids.update(pad.layers)
        for drawing in fp.drawings:
            if drawing.layer:
                layer_ids.add(drawing.layer)
        for text in fp.texts:
            if text.layer:
                layer_ids.add(text.layer)
        for annotation in fp.pad_names:
            layer_ids.update(annotation.layer_ids)
        for annotation in fp.pad_numbers:
            layer_ids.update(annotation.layer_ids)
    return {
        layer for layer in layer_ids if layer and "*" not in layer and "&" not in layer
    }


def _split_layer_id(layer_id: str) -> tuple[str | None, str]:
    dot_idx = layer_id.find(".")
    if dot_idx < 0:
        return (None, layer_id)
    return (layer_id[:dot_idx], layer_id[dot_idx + 1 :])


def _root_panel_key(root: str | None) -> tuple[int, int, str]:
    if root is None:
        return (3, 0, "")
    token = root.strip()
    if token == "F":
        return (0, 0, token)
    if token == "B":
        return (2, 0, token)
    if token.startswith("In") and token[2:].isdigit():
        return (1, int(token[2:]), token)
    return (3, 0, token)


def _layer_color(layer_id: str, kind: str) -> tuple[float, float, float, float]:
    if layer_id in _LAYER_COLOR_OVERRIDES:
        return _LAYER_COLOR_OVERRIDES[layer_id]
    if kind in {"Nets", "PadNumbers"}:
        return (1.0, 1.0, 1.0, 1.0)
    if kind == "Drill":
        return (0.89, 0.82, 0.15, 1.0)
    return (0.50, 0.50, 0.50, 0.50)


def _build_layer_models(
    model: RenderModel,
    all_layers: list[str],
    copper_layers: list[str],
) -> list[LayerModel]:
    # Include all board-defined layers plus any synthesized layers from scene geometry.
    layer_ids = _collect_scene_layers(model)
    for fp in model.footprints:
        for pad in fp.pads:
            if pad.hole is None:
                continue
            layer_ids.update(
                _drill_layers_from_copper_layers(
                    pad.layers,
                    all_copper_layers=copper_layers,
                    include_between=True,
                )
            )
    layer_ids.update(all_layers)
    layer_ids = {layer for layer in layer_ids if layer}

    copper_roots = [name[:-3] for name in copper_layers if name.endswith(".Cu")]
    panel_root_index = {root: idx for idx, root in enumerate(copper_roots)}
    paint_root_order = list(reversed(copper_roots))
    paint_root_index = {root: idx for idx, root in enumerate(paint_root_order)}

    def panel_key(layer_id: str) -> tuple[int, int, int, str]:
        root, kind = _split_layer_id(layer_id)
        root_key = _root_panel_key(root)
        root_index = panel_root_index.get(root or "", 999)
        kind_priority = _LAYER_KIND_PANEL_PRIORITY.get(kind, 99)
        return (
            root_key[0],
            root_key[1] if root_index == 999 else root_index,
            kind_priority,
            layer_id,
        )

    def paint_key(layer_id: str) -> tuple[int, int, int, str]:
        root, kind = _split_layer_id(layer_id)
        kind_priority = _LAYER_KIND_PANEL_PRIORITY.get(kind, 99)
        # Bottom-to-top: B first, then inner, then F. Non-stack layers last.
        if root in paint_root_index:
            return (0, paint_root_index[root], kind_priority, layer_id)
        root_fallback = _root_panel_key(root)
        return (1, root_fallback[0] * 100 + root_fallback[1], kind_priority, layer_id)

    panel_sorted = sorted(layer_ids, key=panel_key)
    panel_order_by_id = {layer_id: idx for idx, layer_id in enumerate(panel_sorted)}
    paint_sorted = sorted(layer_ids, key=paint_key)
    paint_order_by_id = {layer_id: idx for idx, layer_id in enumerate(paint_sorted)}

    layers: list[LayerModel] = []
    for layer_id in panel_sorted:
        root, kind = _split_layer_id(layer_id)
        layers.append(
            LayerModel(
                id=layer_id,
                root=root,
                kind=kind,
                group=root,
                label=kind if root is not None else layer_id,
                panel_order=panel_order_by_id[layer_id],
                paint_order=paint_order_by_id[layer_id],
                color=_layer_color(layer_id, kind),
                default_visible=(kind != "Fab"),
            )
        )
    return layers


def _expand_copper_layers(
    layers: list[str] | None,
    *,
    all_copper_layers: list[str] | None = None,
    include_between: bool = False,
) -> list[str]:
    known_copper_layers = all_copper_layers or ["F.Cu", "B.Cu"]
    out: set[str] = set()
    for layer in layers or []:
        token = (layer or "").strip()
        if not token:
            continue
        if token == "*.Cu":
            out.update(known_copper_layers)
            continue
        if token.endswith(".Cu") and "&" in token:
            suffix_idx = token.find(".")
            prefixes = token[:suffix_idx].split("&")
            suffix = token[suffix_idx:]
            out.update(f"{prefix}{suffix}" for prefix in prefixes if prefix)
            continue
        if token.endswith(".Cu"):
            out.add(token)
    if not out:
        return []

    expanded = set(out)
    if include_between and known_copper_layers:
        index_by_layer = {name: idx for idx, name in enumerate(known_copper_layers)}
        indices = sorted(
            {index_by_layer[name] for name in expanded if name in index_by_layer}
        )
        if len(indices) >= 2:
            expanded.update(known_copper_layers[indices[0] : indices[-1] + 1])

    ordered_known = [name for name in known_copper_layers if name in expanded]
    unknown = sorted(expanded.difference(ordered_known))
    return [*ordered_known, *unknown]


def _drill_layers_from_copper_layers(
    layers: list[str] | None,
    *,
    all_copper_layers: list[str] | None = None,
    include_between: bool = False,
) -> list[str]:
    copper_layers = _expand_copper_layers(
        layers,
        all_copper_layers=all_copper_layers,
        include_between=include_between,
    )
    if not copper_layers:
        # Drills are board-through visualization, even when copper layer set is empty
        # (e.g. NPTH pads).
        fallback_copper = all_copper_layers or ["F.Cu", "B.Cu"]
        ordered = list(dict.fromkeys(fallback_copper))
        return [layer[:-3] + ".Drill" for layer in ordered]
    ordered = list(dict.fromkeys(copper_layers))
    return [layer[:-3] + ".Drill" for layer in ordered]


def _drill_hole_drawings(
    *,
    cx: float,
    cy: float,
    rotation_deg: float,
    hole: HoleModel,
    layer: str,
) -> list[DrawingModel]:
    sx = max(0.0, _safe_float(hole.size_x) or 0.0)
    sy = max(0.0, _safe_float(hole.size_y) or 0.0)
    if sx <= 0 or sy <= 0:
        return []

    shape = str(hole.shape or "").strip().lower()
    is_oval = shape in {"oval", "slot", "oblong"} or abs(sx - sy) > 1e-6
    if not is_oval:
        return [
            _circle_drawing(
                center=PointXY(x=cx, y=cy),
                end=PointXY(x=cx + sx / 2.0, y=cy),
                width=0.0,
                layer=layer,
                filled=True,
            )
        ]

    major = max(sx, sy)
    minor = min(sx, sy)
    focal = max(0.0, (major - minor) / 2.0)
    if sx >= sy:
        p1_local = (-focal, 0.0)
        p2_local = (focal, 0.0)
    else:
        p1_local = (0.0, -focal)
        p2_local = (0.0, focal)
    p1r = _rotate_kicad_xy(p1_local[0], p1_local[1], rotation_deg)
    p2r = _rotate_kicad_xy(p2_local[0], p2_local[1], rotation_deg)
    return [
        _line_drawing(
            start=PointXY(x=cx + p1r[0], y=cy + p1r[1]),
            end=PointXY(x=cx + p2r[0], y=cy + p2r[1]),
            width=minor,
            layer=layer,
        )
    ]


def _normalize_hole_shape(raw_shape, size_x: float, size_y: float) -> str:
    token = str(raw_shape or "").strip().lower()
    if token:
        if token in {"oblong", "slot"}:
            return "oval"
        if token in {"circle", "oval"}:
            return token
    return "oval" if abs(size_x - size_y) > 1e-6 else "circle"


def _text_layer_name(layer_obj: kicad.pcb.TextLayer | str | None) -> str | None:
    if layer_obj is None:
        return None
    if isinstance(layer_obj, str):
        return layer_obj
    return layer_obj.layer or None


def _is_hidden(text_obj: TextUnion | kicad.pcb.TableCell | kicad.pcb.TextBox) -> bool:
    # FpText and Property have a direct hide field; other types do not.
    if isinstance(text_obj, (kicad.pcb.FpText, kicad.pcb.Property)) and bool(
        text_obj.hide
    ):
        return True
    effects = text_obj.effects
    if effects is not None and bool(effects.hide):
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


def _extract_text_justify(effects: kicad.pcb.Effects | None) -> list[str] | None:
    if effects is None:
        return None
    justify = effects.justify
    if justify is None:
        return None

    out: list[str] = []
    for val in (justify.justify1, justify.justify2, justify.justify3):
        if val is None:
            continue
        token = str(val).strip().lower()
        if token:
            out.append(token)
    return out or None


def _text_box_position(tb: kicad.pcb.TextBox) -> PointXYR:
    if tb.start is not None and tb.end is not None:
        return PointXYR(
            x=(tb.start.x + tb.end.x) / 2,
            y=(tb.start.y + tb.end.y) / 2,
            r=float(tb.angle or 0),
        )
    if tb.pts is not None and tb.pts.xys:
        xs = [p.x for p in tb.pts.xys]
        ys = [p.y for p in tb.pts.xys]
        return PointXYR(
            x=(min(xs) + max(xs)) / 2,
            y=(min(ys) + max(ys)) / 2,
            r=float(tb.angle or 0),
        )
    return PointXYR(x=0, y=0, r=float(tb.angle or 0))


def _table_cell_position(cell: kicad.pcb.TableCell) -> PointXYR:
    if cell.start is not None and cell.end is not None:
        return PointXYR(
            x=(cell.start.x + cell.end.x) / 2,
            y=(cell.start.y + cell.end.y) / 2,
            r=float(cell.angle or 0),
        )
    if cell.pts is not None and cell.pts.xys:
        xs = [p.x for p in cell.pts.xys]
        ys = [p.y for p in cell.pts.xys]
        return PointXYR(
            x=(min(xs) + max(xs)) / 2,
            y=(min(ys) + max(ys)) / 2,
            r=float(cell.angle or 0),
        )
    return PointXYR(x=0, y=0, r=float(cell.angle or 0))
