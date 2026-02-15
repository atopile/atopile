"""Manages loading, extracting render models, and editing a KiCad PCB file."""

from __future__ import annotations

import abc
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

    def _find(self, pcb: kicad.pcb.KicadPcb):
        for fp in pcb.footprints:
            if fp.uuid == self.uuid:
                return fp
        raise ValueError(f"Footprint with uuid {self.uuid!r} not found")

    def execute(self, pcb: kicad.pcb.KicadPcb) -> None:
        fp = self._find(pcb)
        fp.at.r = ((fp.at.r or 0) + self.delta_degrees) % 360

    def undo(self, pcb: kicad.pcb.KicadPcb) -> None:
        fp = self._find(pcb)
        fp.at.r = ((fp.at.r or 0) - self.delta_degrees) % 360


# --- PcbManager ---


class PcbManager:
    def __init__(self) -> None:
        self._path: Path | None = None
        self._pcb_file: kicad.pcb.PcbFile | None = None
        self._undo_stack: list[Action] = []
        self._redo_stack: list[Action] = []

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

    def save(self) -> None:
        assert self._path is not None and self._pcb_file is not None
        kicad.dumps(self._pcb_file, self._path)

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

        return FootprintModel(
            uuid=fp.uuid,
            name=fp.name,
            reference=ref,
            value=value,
            at=Point3(x=fp.at.x, y=fp.at.y, r=fp.at.r or 0),
            layer=fp.layer,
            pads=pads,
            drawings=drawings,
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
