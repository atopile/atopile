"""Manages loading, extracting render models, and editing a KiCad PCB file."""

from __future__ import annotations

import abc
import math
import time
from pathlib import Path

from atopile.layout_server.models import (
    ArcTrackModel,
    BoardModel,
    DrawingModel,
    EdgeModel,
    FilledPolygonModel,
    FlipFootprintCommand,
    FlipFootprintsCommand,
    FootprintGroupModel,
    FootprintModel,
    FootprintSummary,
    HoleModel,
    MoveFootprintCommand,
    MoveFootprintsCommand,
    NetModel,
    PadModel,
    PadNameAnnotationModel,
    PadNumberAnnotationModel,
    Point2,
    Point3,
    RenderModel,
    RotateFootprintCommand,
    RotateFootprintsCommand,
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


class CompositeAction(Action):
    """Execute multiple actions as a single undo/redo unit."""

    def __init__(self, actions: list[Action]) -> None:
        self.actions = actions

    def execute(self, pcb: kicad.pcb.KicadPcb) -> None:
        for action in self.actions:
            action.execute(pcb)

    def undo(self, pcb: kicad.pcb.KicadPcb) -> None:
        for action in reversed(self.actions):
            action.undo(pcb)


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
                    new_r=fp.at.r,
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
        delta_rad = math.radians(delta_degrees)
        cos_t = math.cos(delta_rad)
        sin_t = math.sin(delta_rad)

        actions: list[Action] = []
        for fp in targets:
            if fp.uuid is None:
                continue
            dx = fp.at.x - cx
            dy = fp.at.y - cy
            new_x = cx + dx * cos_t - dy * sin_t
            new_y = cy + dx * sin_t + dy * cos_t
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
        pcb = self.pcb
        copper_layers = _board_copper_layers(pcb)
        global_texts = self._extract_global_texts(pcb)
        vias = [self._extract_via(via) for via in pcb.vias]
        via_drawings = self._synthesize_via_drawings(vias, copper_layers)
        net_names_by_number = {
            int(net.number): net.name for net in pcb.nets if getattr(net, "name", None)
        }
        return RenderModel(
            board=self._extract_board(pcb),
            drawings=[*self._extract_global_drawings(pcb), *via_drawings],
            texts=global_texts,
            footprints=[
                self._extract_footprint(fp, net_names_by_number, copper_layers)
                for fp in pcb.footprints
            ],
            footprint_groups=self._extract_footprint_groups(pcb),
            tracks=[self._extract_segment(seg) for seg in pcb.segments],
            arcs=[self._extract_arc_segment(arc) for arc in pcb.arcs],
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

    def _footprints_from_uuids(self, uuids: list[str]) -> list:
        wanted = {uuid for uuid in uuids if uuid}
        if not wanted:
            return []
        by_uuid = {
            str(fp.uuid): fp
            for fp in self.pcb.footprints
            if getattr(fp, "uuid", None) is not None
        }
        ordered: list = []
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
        footprints_by_uuid = {
            str(fp.uuid)
            for fp in pcb.footprints
            if getattr(fp, "uuid", None) is not None
        }
        groups: list[FootprintGroupModel] = []
        raw_groups = getattr(pcb, "groups", []) or []
        for group in raw_groups:
            raw_members = getattr(group, "members", []) or []
            member_uuids: list[str] = []
            seen_members: set[str] = set()
            for member in raw_members:
                token = str(member).strip()
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
                    uuid=(str(getattr(group, "uuid", "") or "").strip() or None),
                    name=(str(getattr(group, "name", "") or "").strip() or None),
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

    def _extract_footprint(
        self,
        fp,
        net_names_by_number: dict[int, str],
        copper_layers: list[str],
    ) -> FootprintModel:
        ref = _get_property(fp, "Reference")
        value = _get_property(fp, "Value")

        pads: list[PadModel] = []
        raw_pads = list(fp.pads)
        for pad in raw_pads:
            pad_h = pad.size.h if pad.size.h is not None else pad.size.w
            pad_layers = list(pad.layers)
            pad_type = str(getattr(pad, "type", "") or "")
            if pad_type in {"thru_hole", "np_thru_hole"}:
                # Through-hole copper/drill are synthesized into normal drawings.
                # Keep pad metadata (name/position/size/net) but don't draw
                # pads directly.
                pad_layers = []
            pads.append(
                PadModel(
                    name=pad.name,
                    at=Point3(x=pad.at.x, y=pad.at.y, r=pad.at.r or 0),
                    size=Size2(w=pad.size.w, h=pad_h),
                    shape=pad.shape,
                    type=pad.type,
                    layers=pad_layers,
                    net=pad.net.number if pad.net else 0,
                    roundrect_rratio=pad.roundrect_rratio,
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
        drawings.extend(
            self._synthesize_th_pad_copper_drawings(raw_pads, copper_layers)
        )
        drawings.extend(self._synthesize_pad_drill_drawings(raw_pads, copper_layers))

        texts = self._extract_text_entries(fp, ref, value)
        pad_names = self._extract_pad_name_annotations_for_footprint(
            fp, net_names_by_number
        )
        pad_numbers = self._extract_pad_number_annotations_for_footprint(fp)

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
            pad_names=pad_names,
            pad_numbers=pad_numbers,
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

    def _extract_pad_name_annotations_for_footprint(
        self, fp, net_names_by_number: dict[int, str]
    ) -> list[PadNameAnnotationModel]:
        out: list[PadNameAnnotationModel] = []
        for pad_index, pad in enumerate(fp.pads):
            pad_name = (getattr(pad, "name", "") or "").strip()
            if not pad_name:
                continue
            text_layer = _pad_net_text_layer(list(getattr(pad, "layers", []) or []))
            if text_layer is None:
                continue
            pad_net = getattr(pad, "net", None)
            if pad_net is None:
                continue
            net_number = int(getattr(pad_net, "number", 0) or 0)
            if net_number <= 0:
                continue
            net_name = (getattr(pad_net, "name", None) or "").strip()
            if not net_name:
                net_name = (net_names_by_number.get(net_number) or "").strip()
            if not net_name:
                continue
            out.append(
                PadNameAnnotationModel(
                    pad_index=pad_index,
                    pad=pad_name,
                    text=net_name,
                    layer=text_layer,
                )
            )
        return out

    def _extract_pad_number_annotations_for_footprint(
        self, fp
    ) -> list[PadNumberAnnotationModel]:
        out: list[PadNumberAnnotationModel] = []
        for pad_index, pad in enumerate(fp.pads):
            pad_name = (getattr(pad, "name", "") or "").strip()
            if not pad_name:
                continue
            text_layer = _pad_number_text_layer(list(getattr(pad, "layers", []) or []))
            if text_layer is None:
                continue
            out.append(
                PadNumberAnnotationModel(
                    pad_index=pad_index,
                    pad=pad_name,
                    text=pad_name,
                    layer=text_layer,
                )
            )
        return out

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

    def _extract_pad_hole(self, pad) -> HoleModel | None:
        drill = getattr(pad, "drill", None)
        if drill is None:
            return None
        size_x = _safe_float(getattr(drill, "size_x", None))
        size_y = _safe_float(getattr(drill, "size_y", None))
        if size_x is None and size_y is None:
            return None
        if size_x is None:
            size_x = size_y
        if size_y is None:
            size_y = size_x
        if size_x is None or size_y is None or size_x <= 0 or size_y <= 0:
            return None

        offset_obj = getattr(drill, "offset", None)
        offset: Point2 | None = None
        ox = _safe_float(getattr(offset_obj, "x", None))
        oy = _safe_float(getattr(offset_obj, "y", None))
        if ox is not None or oy is not None:
            offset = Point2(x=ox or 0.0, y=oy or 0.0)

        plated = None
        pad_type = str(getattr(pad, "type", "") or "")
        if pad_type:
            plated = pad_type != "np_thru_hole"

        return HoleModel(
            shape=_normalize_hole_shape(getattr(drill, "shape", None), size_x, size_y),
            size_x=size_x,
            size_y=size_y,
            offset=offset,
            plated=plated,
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
        drill = _safe_float(getattr(via, "drill", None)) or 0.0
        return ViaModel(
            at=Point2(x=via.at.x, y=via.at.y),
            size=via.size,
            drill=drill,
            hole=self._extract_via_hole(via, drill),
            layers=list(via.layers),
            net=via.net,
            uuid=via.uuid,
        )

    def _extract_via_hole(self, via, drill: float) -> HoleModel | None:
        if drill <= 0:
            return None
        return HoleModel(
            shape=_normalize_hole_shape(getattr(via, "drillshape", None), drill, drill),
            size_x=drill,
            size_y=drill,
            offset=None,
            plated=True,
        )

    def _synthesize_via_drawings(
        self, vias: list[ViaModel], copper_layers: list[str]
    ) -> list[DrawingModel]:
        drawings: list[DrawingModel] = []
        for via in vias:
            hole = via.hole
            if hole is None and via.drill > 0:
                hole = HoleModel(
                    shape="circle",
                    size_x=via.drill,
                    size_y=via.drill,
                    offset=None,
                    plated=True,
                )

            outer_diameter = _safe_float(via.size) or 0.0
            drill_diameter = 0.0
            if hole is not None:
                hx = _safe_float(hole.size_x) or 0.0
                hy = _safe_float(hole.size_y) or hx
                drill_diameter = max(hx, hy)
            if drill_diameter <= 0:
                drill_diameter = _safe_float(via.drill) or 0.0

            for copper_layer in _expand_copper_layers(
                via.layers,
                all_copper_layers=copper_layers,
                include_between=True,
            ):
                if outer_diameter <= 0:
                    continue
                if drill_diameter > 0 and outer_diameter > drill_diameter:
                    annulus_thickness = (outer_diameter - drill_diameter) / 2.0
                    centerline_radius = (outer_diameter + drill_diameter) / 4.0
                    if annulus_thickness > 0 and centerline_radius > 0:
                        drawings.append(
                            DrawingModel(
                                type="circle",
                                center=Point2(x=via.at.x, y=via.at.y),
                                end=Point2(x=via.at.x + centerline_radius, y=via.at.y),
                                width=annulus_thickness,
                                layer=copper_layer,
                                filled=False,
                            )
                        )
                        continue
                drawings.append(
                    DrawingModel(
                        type="circle",
                        center=Point2(x=via.at.x, y=via.at.y),
                        end=Point2(x=via.at.x + outer_diameter / 2.0, y=via.at.y),
                        width=0.0,
                        layer=copper_layer,
                        filled=True,
                    )
                )

            if hole is None:
                continue
            for drill_layer in _drill_layers_from_copper_layers(
                via.layers,
                all_copper_layers=copper_layers,
                include_between=True,
            ):
                drawings.extend(
                    _drill_hole_drawings(
                        cx=via.at.x,
                        cy=via.at.y,
                        rotation_deg=0.0,
                        hole=hole,
                        layer=drill_layer,
                    )
                )
        return drawings

    def _synthesize_th_pad_copper_drawings(
        self, pads: list, copper_layer_stack: list[str]
    ) -> list[DrawingModel]:
        drawings: list[DrawingModel] = []
        for pad in pads:
            pad_type = str(getattr(pad, "type", "") or "")
            if pad_type != "thru_hole":
                continue

            pad_at = getattr(pad, "at", None)
            pad_size = getattr(pad, "size", None)
            if pad_at is None or pad_size is None:
                continue

            cx = _safe_float(getattr(pad_at, "x", None))
            cy = _safe_float(getattr(pad_at, "y", None))
            if cx is None or cy is None:
                continue

            pad_w = _safe_float(getattr(pad_size, "w", None))
            pad_h = _safe_float(getattr(pad_size, "h", None))
            if pad_w is None:
                continue
            if pad_h is None:
                pad_h = pad_w
            if pad_w <= 0 or pad_h <= 0:
                continue

            pad_rotation = _safe_float(getattr(pad_at, "r", None)) or 0.0
            pad_shape = str(getattr(pad, "shape", "") or "").strip().lower()
            pad_copper_layers = _expand_copper_layers(
                list(getattr(pad, "layers", []) or []),
                all_copper_layers=copper_layer_stack,
                include_between=True,
            )
            if not pad_copper_layers:
                continue

            hole = self._extract_pad_hole(pad)
            hole_diameter = 0.0
            if hole is not None:
                sx = _safe_float(hole.size_x) or 0.0
                sy = _safe_float(hole.size_y) or sx
                hole_diameter = max(sx, sy)

            for copper_layer in pad_copper_layers:
                if pad_shape == "circle":
                    outer_diameter = max(pad_w, pad_h)
                    if hole_diameter > 0 and outer_diameter > hole_diameter:
                        annulus_thickness = (outer_diameter - hole_diameter) / 2.0
                        centerline_radius = (outer_diameter + hole_diameter) / 4.0
                        if annulus_thickness > 0 and centerline_radius > 0:
                            drawings.append(
                                DrawingModel(
                                    type="circle",
                                    center=Point2(x=cx, y=cy),
                                    end=Point2(x=cx + centerline_radius, y=cy),
                                    width=annulus_thickness,
                                    layer=copper_layer,
                                    filled=False,
                                )
                            )
                            continue
                    drawings.append(
                        DrawingModel(
                            type="circle",
                            center=Point2(x=cx, y=cy),
                            end=Point2(x=cx + outer_diameter / 2.0, y=cy),
                            width=0.0,
                            layer=copper_layer,
                            filled=True,
                        )
                    )
                    continue

                if pad_shape == "oval":
                    major = max(pad_w, pad_h)
                    minor = min(pad_w, pad_h)
                    if hole is not None:
                        hsx = _safe_float(hole.size_x) or 0.0
                        hsy = _safe_float(hole.size_y) or hsx
                        inner_major = max(hsx, hsy)
                        inner_minor = min(hsx, hsy)
                        if (
                            inner_major > 0
                            and inner_minor > 0
                            and major > inner_major
                            and minor > inner_minor
                        ):
                            delta_major = major - inner_major
                            delta_minor = minor - inner_minor
                            if abs(delta_major - delta_minor) <= 1e-3:
                                # `delta_*` are diameter deltas and line width is
                                # full stroke width. Annulus radial thickness is
                                # delta/2, so stroke width is delta/2.
                                annulus_thickness = (delta_major + delta_minor) / 4.0
                                center_major = (major + inner_major) / 2.0
                                center_minor = (minor + inner_minor) / 2.0
                                if (
                                    annulus_thickness > 0
                                    and center_major > 0
                                    and center_minor > 0
                                ):
                                    ring_points_local = _capsule_outline_points(
                                        center_major,
                                        center_minor,
                                        horizontal=pad_w >= pad_h,
                                    )
                                    ring_points = []
                                    for pt in ring_points_local:
                                        rx, ry = _rotate_kicad_xy(
                                            pt[0], pt[1], pad_rotation
                                        )
                                        ring_points.append(Point2(x=cx + rx, y=cy + ry))
                                    drawings.append(
                                        DrawingModel(
                                            type="curve",
                                            points=ring_points,
                                            width=annulus_thickness,
                                            layer=copper_layer,
                                            filled=False,
                                        )
                                    )
                                    continue

                    focal = max(0.0, (major - minor) / 2.0)
                    if pad_w >= pad_h:
                        p1_local = (-focal, 0.0)
                        p2_local = (focal, 0.0)
                    else:
                        p1_local = (0.0, -focal)
                        p2_local = (0.0, focal)
                    p1r = _rotate_kicad_xy(p1_local[0], p1_local[1], pad_rotation)
                    p2r = _rotate_kicad_xy(p2_local[0], p2_local[1], pad_rotation)
                    drawings.append(
                        DrawingModel(
                            type="line",
                            start=Point2(x=cx + p1r[0], y=cy + p1r[1]),
                            end=Point2(x=cx + p2r[0], y=cy + p2r[1]),
                            width=minor,
                            layer=copper_layer,
                        )
                    )
                    continue

                hw = pad_w / 2.0
                hh = pad_h / 2.0
                corners_local = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
                points: list[Point2] = []
                for lx, ly in corners_local:
                    rx, ry = _rotate_kicad_xy(lx, ly, pad_rotation)
                    points.append(Point2(x=cx + rx, y=cy + ry))
                drawings.append(
                    DrawingModel(
                        type="polygon",
                        points=points,
                        width=0.0,
                        layer=copper_layer,
                        filled=True,
                    )
                )

        return drawings

    def _synthesize_pad_drill_drawings(
        self, pads: list, copper_layers: list[str]
    ) -> list[DrawingModel]:
        drawings: list[DrawingModel] = []
        for pad in pads:
            hole = self._extract_pad_hole(pad)
            if hole is None:
                continue

            pad_at = getattr(pad, "at", None)
            if pad_at is None:
                continue
            offset = hole.offset or Point2(x=0.0, y=0.0)
            pad_rotation = _safe_float(getattr(pad_at, "r", None)) or 0.0
            rox, roy = _rotate_kicad_xy(offset.x, offset.y, pad_rotation)
            cx = (_safe_float(getattr(pad_at, "x", None)) or 0.0) + rox
            cy = (_safe_float(getattr(pad_at, "y", None)) or 0.0) + roy
            for drill_layer in _drill_layers_from_copper_layers(
                list(getattr(pad, "layers", []) or []),
                all_copper_layers=copper_layers,
                include_between=True,
            ):
                drawings.extend(
                    _drill_hole_drawings(
                        cx=cx,
                        cy=cy,
                        rotation_deg=pad_rotation,
                        hole=hole,
                        layer=drill_layer,
                    )
                )
        return drawings

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


def _estimate_stroke_text_advance(text: str) -> float:
    """Approximate Newstroke advance units for a single-line label."""
    if not text:
        return 0.6

    narrow = set("1Iil|!.,:;'`")
    wide = set("MW@%#")
    advance = 0.0
    for ch in text:
        if ch == " ":
            advance += 0.6
        elif ch in narrow:
            advance += 0.45
        elif ch in wide:
            advance += 0.95
        else:
            advance += 0.72
    return max(advance, 0.6)


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


def _fit_text_inside_pad(
    text: str, pad_w: float, pad_h: float
) -> tuple[float, float, float] | None:
    """Return (char_w, char_h, thickness) fitted to pad size."""
    if pad_w <= 0 or pad_h <= 0:
        return None

    # Keep margin so labels do not touch pad boundaries.
    usable_w = max(0.0, pad_w * PAD_NET_FIT_MARGIN)
    usable_h = max(0.0, pad_h * PAD_NET_FIT_MARGIN)
    if usable_w <= 0 or usable_h <= 0:
        return None

    # Fit text against the longer/shorter pad dimensions, leaving margin.
    vertical = usable_h > usable_w
    major = usable_h if vertical else usable_w
    minor = usable_w if vertical else usable_h

    char_w_ratio = PAD_NET_CHAR_W_RATIO
    advance_units = _estimate_stroke_text_advance(text)
    max_h_by_width = major / max(advance_units * char_w_ratio, 1e-6)
    # Fit first, then downscale so text sits comfortably inside pads like KiCad.
    char_h = min(minor * PAD_NET_MINOR_FIT, max_h_by_width * PAD_NET_MAJOR_FIT)
    # Larger baseline for readability while still fitting within pads.
    char_h *= PAD_NET_CHAR_SCALE

    # Tiny text is unreadable and expensive to draw at scale.
    if char_h < PAD_NET_MIN_CHAR_H:
        return None

    char_w = char_h * char_w_ratio
    thickness = min(
        PAD_NET_STROKE_MAX,
        max(PAD_NET_STROKE_MIN, char_h * PAD_NET_STROKE_SCALE),
    )
    return (char_w, char_h, thickness)


def _fit_pad_net_text(
    text: str, pad_w: float, pad_h: float
) -> tuple[str, tuple[float, float, float]] | None:
    for candidate in _pad_net_text_candidates(text):
        fitted = _fit_text_inside_pad(candidate, pad_w, pad_h)
        if fitted is not None:
            return (candidate, fitted)
    return None


def _pad_net_text_candidates(text: str) -> list[str]:
    base = text.strip()
    if not base:
        return []

    candidates: list[str] = []
    seen: set[str] = set()

    def add(candidate: str) -> None:
        token = candidate.strip()
        if not token or token in seen:
            return
        seen.add(token)
        candidates.append(token)

    add(base)

    normalized = base
    for prefix in PAD_NET_PREFIXES:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
    add(normalized)

    tokens = [t for t in normalized.replace("/", "-").split("-") if t.strip()]
    for token in reversed(tokens):
        if token.lower() in PAD_NET_GENERIC_TOKENS:
            continue
        add(token)
        add(token.replace("[", "").replace("]", ""))

    for max_len in PAD_NET_TRUNCATE_LENGTHS:
        if len(normalized) > max_len:
            add(normalized[:max_len])

    return candidates


def _pad_net_text_layer(pad_layers: list[str] | None) -> str | None:
    if not pad_layers:
        return None
    for layer in pad_layers:
        if layer.endswith(".Cu"):
            return layer[:-3] + ".Nets"
    return None


def _pad_number_text_layer(pad_layers: list[str] | None) -> str | None:
    if not pad_layers:
        return None
    for layer in pad_layers:
        if layer.endswith(".Cu"):
            return layer[:-3] + ".PadNumbers"
    return None


def _pad_net_text_rotation(
    total_pad_rotation_deg: float, pad_w: float, pad_h: float
) -> float:
    """Snap pad net label rotation to world 0 or +90 degrees.

    - Symmetric pads always return 0.
    - Non-symmetric pads consider total pad rotation (footprint + pad).
    """
    if pad_w <= 0 or pad_h <= 0:
        return 0.0
    if abs(pad_w - pad_h) <= 1e-6:
        return 0.0

    long_axis_deg = (
        total_pad_rotation_deg if pad_w > pad_h else total_pad_rotation_deg + 90.0
    )
    axis_x = abs(math.cos(math.radians(long_axis_deg)))
    axis_y = abs(math.sin(math.radians(long_axis_deg)))
    return 90.0 if axis_y > axis_x else 0.0


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
    for layer in getattr(pcb, "layers", []) or []:
        name = str(getattr(layer, "name", "") or "")
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


def _capsule_outline_points(
    major: float,
    minor: float,
    *,
    horizontal: bool,
    arc_steps: int = 12,
) -> list[tuple[float, float]]:
    major = max(0.0, major)
    minor = max(0.0, minor)
    if major <= 0 or minor <= 0:
        return []

    radius = minor / 2.0
    half_span = max(0.0, (major - minor) / 2.0)

    points: list[tuple[float, float]] = []
    for i in range(arc_steps + 1):
        angle = math.pi / 2.0 - (math.pi * i / arc_steps)
        x = half_span + radius * math.cos(angle)
        y = radius * math.sin(angle)
        points.append((x, y))
    for i in range(arc_steps + 1):
        angle = -math.pi / 2.0 + (math.pi * i / arc_steps)
        # Left cap must bulge to negative X; use mirrored cosine term.
        x = -half_span - radius * math.cos(angle)
        y = radius * math.sin(angle)
        points.append((x, y))

    if not horizontal:
        points = [(-y, x) for x, y in points]

    if points and points[0] != points[-1]:
        points.append(points[0])
    return points


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
            DrawingModel(
                type="circle",
                center=Point2(x=cx, y=cy),
                end=Point2(x=cx + sx / 2.0, y=cy),
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
        DrawingModel(
            type="line",
            start=Point2(x=cx + p1r[0], y=cy + p1r[1]),
            end=Point2(x=cx + p2r[0], y=cy + p2r[1]),
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
