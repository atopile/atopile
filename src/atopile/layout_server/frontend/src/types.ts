export interface RenderModel {
    board: BoardModel;
    footprints: FootprintModel[];
    tracks: TrackModel[];
    arcs: ArcTrackModel[];
    vias: ViaModel[];
    zones: ZoneModel[];
    nets: NetModel[];
}

export interface BoardModel {
    edges: EdgeModel[];
    width: number;
    height: number;
    origin: [number, number];
}

export interface EdgeModel {
    type: "line" | "arc" | "circle" | "rect";
    start?: [number, number];
    end?: [number, number];
    mid?: [number, number];
    center?: [number, number];
}

export interface FootprintModel {
    uuid: string;
    name: string;
    reference: string | null;
    value: string | null;
    at: [number, number, number]; // x, y, rotation_degrees
    layer: string;
    pads: PadModel[];
    drawings: DrawingModel[];
}

export interface PadModel {
    name: string;
    at: [number, number, number];
    size: [number, number];
    shape: string;
    type: string;
    layers: string[];
    net: number;
    roundrect_rratio: number | null;
    drill: { shape: string | null; size_x: number | null; size_y: number | null } | null;
}

export interface DrawingModel {
    type: "line" | "arc" | "circle" | "rect" | "polygon";
    start?: [number, number];
    end?: [number, number];
    mid?: [number, number];
    center?: [number, number];
    width: number;
    layer: string | null;
    points?: [number, number][];
}

export interface TrackModel {
    start: [number, number];
    end: [number, number];
    width: number;
    layer: string | null;
    net: number;
    uuid: string | null;
}

export interface ArcTrackModel {
    start: [number, number];
    mid: [number, number];
    end: [number, number];
    width: number;
    layer: string | null;
    net: number;
    uuid: string | null;
}

export interface ViaModel {
    at: [number, number];
    size: number;
    drill: number;
    layers: string[];
    net: number;
    uuid: string | null;
}

export interface ZoneModel {
    net: number;
    net_name: string;
    layers: string[];
    name: string | null;
    uuid: string | null;
    outline: [number, number][];
    filled_polygons: { layer: string; points: [number, number][] }[];
}

export interface NetModel {
    number: number;
    name: string | null;
}
