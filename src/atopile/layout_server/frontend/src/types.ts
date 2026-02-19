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
    drawings: DrawingModel[];
    texts: TextModel[];
    footprints: FootprintModel[];
    tracks: TrackModel[];
    arcs: ArcTrackModel[];
    zones: ZoneModel[];
    nets: NetModel[];
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
    layer: string;
}

export interface PadNumberAnnotationModel {
    pad_index: number;
    pad: string;
    text: string;
    layer: string;
}

export interface PadModel {
    name: string;
    at: Point3;
    size: Size2;
    shape: string;
    type: string;
    layers: string[];
    net: number;
    roundrect_rratio: number | null;
}

export interface DrawingModel {
    type: "line" | "arc" | "circle" | "rect" | "polygon" | "curve";
    start?: Point2;
    end?: Point2;
    mid?: Point2;
    center?: Point2;
    width: number;
    layer: string | null;
    points?: Point2[];
    filled: boolean;
}

export interface TrackModel {
    start: Point2;
    end: Point2;
    width: number;
    layer: string | null;
    net: number;
    uuid: string | null;
}

export interface ArcTrackModel {
    start: Point2;
    mid: Point2;
    end: Point2;
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

export interface NetModel {
    number: number;
    name: string | null;
}
