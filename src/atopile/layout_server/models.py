"""Pydantic models for the layout server API."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# --- Geometry primitives ---


class PointXY(BaseModel):
    x: float
    y: float


class PointXYR(BaseModel):
    x: float
    y: float
    r: float = 0


class Size2(BaseModel):
    w: float
    h: float


class PcbObjectModel(BaseModel):
    uuid: str | None = None
    at: PointXYR


# --- Board ---


class EdgeModel(BaseModel):
    type: str  # "line" | "arc" | "circle" | "rect"
    start: PointXY | None = None
    end: PointXY | None = None
    mid: PointXY | None = None
    center: PointXY | None = None


class BoardModel(BaseModel):
    edges: list[EdgeModel]
    width: float
    height: float
    origin: PointXY


# --- Footprint internals ---


class HoleModel(BaseModel):
    shape: str | None = None
    size_x: float
    size_y: float
    offset: PointXY | None = None
    plated: bool | None = None


class PadModel(BaseModel):
    name: str
    at: PointXYR
    size: Size2
    shape: str
    type: str
    layers: list[str]
    net: int = 0
    hole: HoleModel | None = None
    roundrect_rratio: float | None = None


class _DrawingBase(BaseModel):
    width: float = 0.12
    layer: str | None = None
    filled: bool = False
    uuid: str | None = None


class LineDrawingModel(_DrawingBase):
    type: Literal["line"] = "line"
    start: PointXY
    end: PointXY


class ArcDrawingModel(_DrawingBase):
    type: Literal["arc"] = "arc"
    start: PointXY
    mid: PointXY
    end: PointXY


class CircleDrawingModel(_DrawingBase):
    type: Literal["circle"] = "circle"
    center: PointXY
    end: PointXY


class RectDrawingModel(_DrawingBase):
    type: Literal["rect"] = "rect"
    start: PointXY
    end: PointXY


class PolygonDrawingModel(_DrawingBase):
    type: Literal["polygon"] = "polygon"
    points: list[PointXY]


class CurveDrawingModel(_DrawingBase):
    type: Literal["curve"] = "curve"
    points: list[PointXY]


DrawingModel = Annotated[
    LineDrawingModel
    | ArcDrawingModel
    | CircleDrawingModel
    | RectDrawingModel
    | PolygonDrawingModel
    | CurveDrawingModel,
    Field(discriminator="type"),
]


class TextModel(BaseModel):
    text: str
    at: PointXYR
    layer: str | None = None
    size: Size2 | None = None
    thickness: float | None = None
    justify: list[str] | None = None
    uuid: str | None = None


class PadNameAnnotationModel(BaseModel):
    pad_index: int
    pad: str
    text: str
    layer_ids: list[str]


class PadNumberAnnotationModel(BaseModel):
    pad_index: int
    pad: str
    text: str
    layer_ids: list[str]


class FootprintModel(PcbObjectModel):
    name: str
    reference: str | None
    value: str | None
    layer: str
    pads: list[PadModel]
    drawings: list[DrawingModel]
    texts: list[TextModel]
    pad_names: list[PadNameAnnotationModel]
    pad_numbers: list[PadNumberAnnotationModel]


class FootprintGroupModel(PcbObjectModel):
    name: str | None = None
    member_uuids: list[str]
    track_member_uuids: list[str] = Field(default_factory=list)
    via_member_uuids: list[str] = Field(default_factory=list)
    graphic_member_uuids: list[str] = Field(default_factory=list)
    text_member_uuids: list[str] = Field(default_factory=list)
    zone_member_uuids: list[str] = Field(default_factory=list)


# --- Tracks ---


class TrackModel(BaseModel):
    start: PointXY
    end: PointXY
    mid: PointXY | None = None
    width: float
    layer: str | None = None
    net: int = 0
    uuid: str | None = None


# --- Vias ---


class ViaModel(BaseModel):
    uuid: str | None = None
    at: PointXY
    size: float  # outer diameter
    drill: float  # drill diameter (0 = no drill)
    copper_layers: list[str]  # expanded copper layers for annular ring / filled circle
    drill_layers: list[str]  # drill visualisation layer IDs


# --- Zones ---


class FilledPolygonModel(BaseModel):
    layer: str
    points: list[PointXY]


class ZoneModel(BaseModel):
    net: int
    net_name: str
    layers: list[str]
    name: str | None = None
    uuid: str | None = None
    keepout: bool = False
    hatch_mode: str | None = None
    hatch_pitch: float | None = None
    fill_enabled: bool | None = None
    outline: list[PointXY]
    filled_polygons: list[FilledPolygonModel]


class LayerModel(BaseModel):
    id: str
    root: str | None = None
    kind: str | None = None
    group: str | None = None
    label: str | None = None
    panel_order: int
    paint_order: int
    color: tuple[float, float, float, float]
    default_visible: bool = True


# --- Top-level render model ---


class RenderModel(BaseModel):
    board: BoardModel
    layers: list[LayerModel] = Field(default_factory=list)
    drawings: list[DrawingModel]
    texts: list[TextModel]
    footprints: list[FootprintModel]
    footprint_groups: list[FootprintGroupModel] = Field(default_factory=list)
    tracks: list[TrackModel]
    vias: list[ViaModel] = Field(default_factory=list)
    zones: list[ZoneModel]


# --- Footprint summary (for /api/footprints) ---


class FootprintSummary(BaseModel):
    uuid: str | None
    reference: str | None
    value: str | None
    x: float
    y: float
    r: float
    layer: str


# --- Request / Response models ---


class _StrictCommandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MoveCommand(_StrictCommandModel):
    command: Literal["move"]
    uuids: list[str] = Field(min_length=1)
    dx: float
    dy: float


class RotateCommand(_StrictCommandModel):
    command: Literal["rotate"]
    uuids: list[str] = Field(min_length=1)
    delta_degrees: float


class FlipCommand(_StrictCommandModel):
    command: Literal["flip"]
    uuids: list[str] = Field(min_length=1)


class UndoCommand(_StrictCommandModel):
    command: Literal["undo"]


class RedoCommand(_StrictCommandModel):
    command: Literal["redo"]


ActionRequest = Annotated[
    MoveCommand | RotateCommand | FlipCommand | UndoCommand | RedoCommand,
    Field(discriminator="command"),
]


class StatusResponse(BaseModel):
    status: Literal["ok", "error"]
    code: str
    message: str | None = None
    model: RenderModel | None = None


class WsMessage(BaseModel):
    type: str
    model: RenderModel | None = None
