/**
 * Type declarations for the layout editor modules.
 * tsc uses these declarations (via tsconfig paths).
 * Vite resolves to the real .ts source files (via vite.config.ts alias).
 */

declare module '@layout-editor/editor' {
  export class Editor {
    constructor(canvas: HTMLCanvasElement, baseUrl: string, apiPrefix?: string, wsPath?: string);
    init(): Promise<void>;
    loadRenderModel(footprintUuid?: string | null, fitToView?: boolean): Promise<void>;
    setReadOnly(readOnly: boolean): void;
    setPadColorOverrides(overrides: Map<string, import('@layout-editor/colors').Color>): void;
    setHighlightedPads(padNames: Set<string>): void;
    setOutlinePads(padNames: Set<string>): void;
    setOnPadClick(cb: ((padName: string) => void) | null): void;
  }
}

declare module '@layout-editor/colors' {
  export type Color = [number, number, number, number];
  export type SignalType = "digital" | "analog" | "power" | "ground" | "nc";
  export const SIGNAL_TYPE_COLORS: Record<SignalType, { pad: Color; badgeBg: string; badgeFg: string }>;
  export const UNCONNECTED_PAD_COLOR: Color;
  export const PAD_HIGHLIGHT_COLOR: Color;
  export function getSignalColors(signalType: string | null | undefined): { pad: Color; badgeBg: string; badgeFg: string };
}

declare module '@layout-editor/types' {
  export interface Point2 { x: number; y: number; }
  export interface Point3 { x: number; y: number; r: number; }
  export interface Size2 { w: number; h: number; }
  export interface RenderModel {
    board: BoardModel;
    footprints: FootprintModel[];
    tracks: TrackModel[];
    arcs: ArcTrackModel[];
    vias: ViaModel[];
    zones: ZoneModel[];
    nets: NetModel[];
  }
  export interface BoardModel { edges: EdgeModel[]; width: number; height: number; origin: Point2; }
  export interface EdgeModel { type: "line" | "arc" | "circle" | "rect"; start?: Point2; end?: Point2; mid?: Point2; center?: Point2; }
  export interface FootprintModel { uuid: string | null; name: string; reference: string | null; value: string | null; at: Point3; layer: string; pads: PadModel[]; drawings: DrawingModel[]; }
  export type PadShape = "circle" | "oval" | "rect" | "roundrect" | "trapezoid" | "custom";
  export interface PadModel { name: string; at: Point3; size: Size2; shape: PadShape; type: string; layers: string[]; net: number; roundrect_rratio: number | null; drill: DrillModel | null; }
  export interface DrillModel { shape: string | null; size_x: number | null; size_y: number | null; }
  export interface DrawingModel { type: "line" | "arc" | "circle" | "rect" | "polygon"; start?: Point2; end?: Point2; mid?: Point2; center?: Point2; width: number; layer: string | null; points?: Point2[]; }
  export interface TrackModel { start: Point2; end: Point2; width: number; layer: string | null; net: number; uuid: string | null; }
  export interface ArcTrackModel { start: Point2; mid: Point2; end: Point2; width: number; layer: string | null; net: number; uuid: string | null; }
  export interface ViaModel { at: Point2; size: number; drill: number; layers: string[]; net: number; uuid: string | null; }
  export interface ZoneModel { net: number; net_name: string; layers: string[]; name: string | null; uuid: string | null; outline: Point2[]; filled_polygons: FilledPolygonModel[]; }
  export interface FilledPolygonModel { layer: string; points: Point2[]; }
  export interface NetModel { number: number; name: string | null; }
}
