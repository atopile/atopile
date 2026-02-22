export interface Point2 {
    x: number;
    y: number;
}

export interface Point3 {
    x: number;
    y: number;
    r: number;
}

export interface Size2 {
    w: number;
    h: number;
}

export interface RenderModel {
    board: BoardModel;
    layers: LayerModel[];
    drawings: DrawingModel[];
    texts: TextModel[];
    footprints: FootprintModel[];
    footprint_groups: FootprintGroupModel[];
    tracks: TrackModel[];
    zones: ZoneModel[];
}

export interface BoardModel {
    edges: EdgeModel[];
    width: number;
    height: number;
    origin: Point2;
}

export interface EdgeModel {
    type: "line" | "arc" | "circle" | "rect";
    start?: Point2;
    end?: Point2;
    mid?: Point2;
    center?: Point2;
}

export interface FootprintModel {
    uuid: string | null;
    name: string;
    reference: string | null;
    value: string | null;
    at: Point3;
    layer: string;
    pads: PadModel[];
    drawings: DrawingModel[];
    texts: TextModel[];
    pad_names: PadNameAnnotationModel[];
    pad_numbers: PadNumberAnnotationModel[];
}

export interface FootprintGroupModel {
    uuid: string | null;
    name: string | null;
    member_uuids: string[];
}

export interface TextModel {
    text: string;
    at: Point3;
    layer: string | null;
    size: Size2 | null;
    thickness: number | null;
    justify: string[] | null;
}

export interface PadNameAnnotationModel {
    pad_index: number;
    pad: string;
    text: string;
    layer_ids: string[];
}

export interface PadNumberAnnotationModel {
    pad_index: number;
    pad: string;
    text: string;
    layer_ids: string[];
}

export interface PadModel {
    name: string;
    at: Point3;
    size: Size2;
    shape: string;
    type: string;
    layers: string[];
    net: number;
    hole: HoleModel | null;
    roundrect_rratio: number | null;
}

export interface HoleModel {
    shape: string | null;
    size_x: number;
    size_y: number;
    offset: Point2 | null;
    plated: boolean | null;
}

interface DrawingBase {
    width: number;
    layer: string | null;
    filled: boolean;
}

export interface LineDrawingModel extends DrawingBase {
    type: "line";
    start: Point2;
    end: Point2;
}

export interface ArcDrawingModel extends DrawingBase {
    type: "arc";
    start: Point2;
    mid: Point2;
    end: Point2;
}

export interface CircleDrawingModel extends DrawingBase {
    type: "circle";
    center: Point2;
    end: Point2;
}

export interface RectDrawingModel extends DrawingBase {
    type: "rect";
    start: Point2;
    end: Point2;
}

export interface PolygonDrawingModel extends DrawingBase {
    type: "polygon";
    points: Point2[];
}

export interface CurveDrawingModel extends DrawingBase {
    type: "curve";
    points: Point2[];
}

export type DrawingModel =
    | LineDrawingModel
    | ArcDrawingModel
    | CircleDrawingModel
    | RectDrawingModel
    | PolygonDrawingModel
    | CurveDrawingModel;

export interface TrackModel {
    start: Point2;
    end: Point2;
    mid?: Point2;
    width: number;
    layer: string | null;
    net: number;
    uuid: string | null;
}

export interface ZoneModel {
    net: number;
    net_name: string;
    layers: string[];
    name: string | null;
    uuid: string | null;
    keepout: boolean;
    hatch_mode: string | null;
    hatch_pitch: number | null;
    fill_enabled: boolean | null;
    outline: Point2[];
    filled_polygons: FilledPolygonModel[];
}

export interface FilledPolygonModel {
    layer: string;
    points: Point2[];
}

export interface LayerModel {
    id: string;
    root: string | null;
    kind: string | null;
    group: string | null;
    label: string | null;
    panel_order: number;
    paint_order: number;
    color: [number, number, number, number];
    default_visible: boolean;
}

export interface StatusResponse {
    status: "ok" | "error";
    code: string;
    message: string | null;
    model: RenderModel | null;
}

export interface MoveFootprintCommand {
    command: "move_footprint";
    uuid: string;
    x: number;
    y: number;
    r?: number | null;
}

export interface RotateFootprintCommand {
    command: "rotate_footprint";
    uuid: string;
    delta_degrees: number;
}

export interface FlipFootprintCommand {
    command: "flip_footprint";
    uuid: string;
}

export interface MoveFootprintsCommand {
    command: "move_footprints";
    uuids: string[];
    dx: number;
    dy: number;
}

export interface RotateFootprintsCommand {
    command: "rotate_footprints";
    uuids: string[];
    delta_degrees: number;
}

export interface FlipFootprintsCommand {
    command: "flip_footprints";
    uuids: string[];
}

export interface UndoCommand {
    command: "undo";
}

export interface RedoCommand {
    command: "redo";
}

export type ActionCommand =
    | MoveFootprintCommand
    | RotateFootprintCommand
    | FlipFootprintCommand
    | MoveFootprintsCommand
    | RotateFootprintsCommand
    | FlipFootprintsCommand
    | UndoCommand
    | RedoCommand;
