import { Vec2, BBox } from "./math";
import { Renderer, RenderLayer } from "./webgl/renderer";
import { fpTransform, padTransform, rotatedRectExtents } from "./geometry";
import {
    getLayerColor,
    getPadColor,
    ZONE_COLOR_ALPHA,
} from "./colors";
import type {
    RenderModel,
    FootprintModel,
    PadModel,
    TrackModel,
    DrawingModel,
    Point2,
    Point3,
    LayerModel,
} from "./types";
import { layoutKicadStrokeLine } from "./kicad_stroke_font";
import { footprintBBox } from "./hit-test";

const DEG_TO_RAD = Math.PI / 180;
const HOLE_SEGMENTS = 36;
const PAD_ANNOTATION_BOX_RATIO = 0.78;
const PAD_ANNOTATION_MAJOR_FIT = 0.96;
const PAD_ANNOTATION_MINOR_FIT = 0.88;
const PAD_ANNOTATION_CHAR_SCALE = 0.60;
const PAD_ANNOTATION_MIN_CHAR_H = 0.08;
const PAD_ANNOTATION_CHAR_W_RATIO = 0.72;
const PAD_ANNOTATION_STROKE_SCALE = 0.22;
const PAD_ANNOTATION_STROKE_MIN = 0.02;
const PAD_ANNOTATION_STROKE_MAX = 0.16;
const PAD_NAME_GENERIC_TOKENS = new Set(["input", "output", "line", "net"]);
const PAD_NAME_PREFIXES = ["power_in-", "power_vbus-", "power-"];
const PAD_NAME_TRUNCATE_LENGTHS = [16, 12, 10, 8, 6, 5, 4, 3, 2];
const PAD_NAME_TARGET_CHAR_H = 0.14;
const PAD_NUMBER_BADGE_SIZE_RATIO = 0.36;
const PAD_NUMBER_BADGE_MARGIN_RATIO = 0.05;
const PAD_NUMBER_CHAR_SCALE = 0.80;
const PAD_NUMBER_MIN_CHAR_H = 0.04;
const SELECTION_STROKE_WIDTH = 0.12;
const GROUP_SELECTION_STROKE_WIDTH = 0.1;
const HOVER_SELECTION_STROKE_WIDTH = 0.08;
const SELECTION_GROW = 0.2;
const GROUP_SELECTION_GROW = 0.16;
const HOVER_SELECTION_GROW = 0.12;


function p2v(p: Point2): Vec2 {
    return new Vec2(p.x, p.y);
}

/** Approximate a 3-point arc with line segments */
function arcToPoints(start: Point2, mid: Point2, end: Point2, segments = 32): Vec2[] {
    const ax = start.x, ay = start.y;
    const bx = mid.x, by = mid.y;
    const cx = end.x, cy = end.y;

    const D = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by));
    if (Math.abs(D) < 1e-10) {
        return [new Vec2(ax, ay), new Vec2(bx, by), new Vec2(cx, cy)];
    }

    const ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / D;
    const uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / D;
    const radius = Math.sqrt((ax - ux) ** 2 + (ay - uy) ** 2);
    const startAngle = Math.atan2(ay - uy, ax - ux);
    const midAngle = Math.atan2(by - uy, bx - ux);
    const endAngle = Math.atan2(cy - uy, cx - ux);

    let da1 = midAngle - startAngle;
    while (da1 > Math.PI) da1 -= 2 * Math.PI;
    while (da1 < -Math.PI) da1 += 2 * Math.PI;

    const clockwise = da1 < 0;
    let sweep = endAngle - startAngle;
    if (clockwise) {
        while (sweep > 0) sweep -= 2 * Math.PI;
    } else {
        while (sweep < 0) sweep += 2 * Math.PI;
    }

    const points: Vec2[] = [];
    for (let i = 0; i <= segments; i++) {
        const t = i / segments;
        const angle = startAngle + sweep * t;
        points.push(new Vec2(ux + radius * Math.cos(angle), uy + radius * Math.sin(angle)));
    }
    return points;
}

function circleToPoints(cx: number, cy: number, radius: number, segments = HOLE_SEGMENTS): Vec2[] {
    const points: Vec2[] = [];
    if (radius <= 0) return points;
    for (let i = 0; i <= segments; i++) {
        const angle = (i / segments) * 2 * Math.PI;
        points.push(new Vec2(cx + radius * Math.cos(angle), cy + radius * Math.sin(angle)));
    }
    return points;
}

function drawFootprintSelectionBox(
    layer: RenderLayer,
    fp: FootprintModel,
    strokeWidth: number,
    strokeAlpha: number,
    grow: number,
    fillAlpha = 0,
) {
    const bbox = footprintBBox(fp).grow(grow);
    if (bbox.w <= 0 || bbox.h <= 0) return;
    const corners = [
        new Vec2(bbox.x, bbox.y),
        new Vec2(bbox.x2, bbox.y),
        new Vec2(bbox.x2, bbox.y2),
        new Vec2(bbox.x, bbox.y2),
        new Vec2(bbox.x, bbox.y),
    ];
    if (fillAlpha > 0) {
        layer.geometry.add_polygon(corners.slice(0, 4), 1.0, 1.0, 1.0, fillAlpha);
    }
    layer.geometry.add_polyline(corners, strokeWidth, 1.0, 1.0, 1.0, strokeAlpha);
}

function estimateStrokeTextAdvance(text: string): number {
    if (!text) return 0.6;
    const narrow = new Set(["1", "I", "i", "l", "|", "!", ".", ",", ":", ";", "'", "`"]);
    const wide = new Set(["M", "W", "@", "%", "#"]);
    let advance = 0;
    for (const ch of text) {
        if (ch === " ") advance += 0.6;
        else if (narrow.has(ch)) advance += 0.45;
        else if (wide.has(ch)) advance += 0.95;
        else advance += 0.72;
    }
    return Math.max(advance, 0.6);
}

function fitTextInsideBox(
    text: string,
    boxW: number,
    boxH: number,
    minCharH = PAD_ANNOTATION_MIN_CHAR_H,
    charScale = PAD_ANNOTATION_CHAR_SCALE,
): [number, number, number] | null {
    if (boxW <= 0 || boxH <= 0) return null;
    const usableW = Math.max(0, boxW * PAD_ANNOTATION_BOX_RATIO);
    const usableH = Math.max(0, boxH * PAD_ANNOTATION_BOX_RATIO);
    if (usableW <= 0 || usableH <= 0) return null;
    const vertical = usableH > usableW;
    const major = vertical ? usableH : usableW;
    const minor = vertical ? usableW : usableH;
    const advance = estimateStrokeTextAdvance(text);
    const maxHByWidth = major / Math.max(advance * PAD_ANNOTATION_CHAR_W_RATIO, 1e-6);
    let charH = Math.min(minor * PAD_ANNOTATION_MINOR_FIT, maxHByWidth * PAD_ANNOTATION_MAJOR_FIT);
    charH *= charScale;
    if (charH < minCharH) return null;
    const charW = charH * PAD_ANNOTATION_CHAR_W_RATIO;
    const thickness = Math.min(
        PAD_ANNOTATION_STROKE_MAX,
        Math.max(PAD_ANNOTATION_STROKE_MIN, charH * PAD_ANNOTATION_STROKE_SCALE),
    );
    return [charW, charH, thickness];
}

function padNameCandidates(text: string): string[] {
    const base = text.trim();
    if (!base) return [];
    const out: string[] = [];
    const seen = new Set<string>();
    const add = (v: string) => {
        const t = v.trim();
        if (!t || seen.has(t)) return;
        seen.add(t);
        out.push(t);
    };

    add(base);
    let normalized = base;
    for (const prefix of PAD_NAME_PREFIXES) {
        if (normalized.startsWith(prefix)) normalized = normalized.slice(prefix.length);
    }
    add(normalized);

    const tokens = normalized.replaceAll("/", "-").split("-").map(t => t.trim()).filter(Boolean);
    for (let idx = tokens.length - 1; idx >= 0; idx--) {
        const token = tokens[idx]!;
        if (PAD_NAME_GENERIC_TOKENS.has(token.toLowerCase())) continue;
        add(token);
        add(token.replaceAll("[", "").replaceAll("]", ""));
    }

    for (const maxLen of PAD_NAME_TRUNCATE_LENGTHS) {
        if (normalized.length > maxLen) add(normalized.slice(0, maxLen));
    }

    return out;
}

function fitPadNameLabel(text: string, boxW: number, boxH: number): [string, [number, number, number]] | null {
    let fallback: [string, [number, number, number]] | null = null;
    for (const candidate of padNameCandidates(text)) {
        const fit = fitTextInsideBox(candidate, boxW, boxH);
        if (!fit) continue;
        if (!fallback || fit[1] > fallback[1][1]) {
            fallback = [candidate, fit];
        }
        if (fit[1] >= PAD_NAME_TARGET_CHAR_H) {
            return [candidate, fit];
        }
    }
    return fallback;
}

function padLabelWorldRotation(totalPadRotationDeg: number, padW: number, padH: number): number {
    if (padW <= 0 || padH <= 0) return 0;
    if (Math.abs(padW - padH) <= 1e-6) return 0;
    const longAxisDeg = padW > padH ? totalPadRotationDeg : totalPadRotationDeg + 90;
    const axisX = Math.abs(Math.cos(longAxisDeg * DEG_TO_RAD));
    const axisY = Math.abs(Math.sin(longAxisDeg * DEG_TO_RAD));
    return axisY > axisX ? 90 : 0;
}

function drawStrokeTextGeometry(
    layer: RenderLayer,
    text: string,
    x: number,
    y: number,
    rotationDeg: number,
    charW: number,
    charH: number,
    thickness: number,
    color: [number, number, number, number],
) {
    const layout = layoutKicadStrokeLine(text, charW, charH);
    if (layout.strokes.length === 0) return;

    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const stroke of layout.strokes) {
        for (const pt of stroke) {
            if (pt.x < minX) minX = pt.x;
            if (pt.y < minY) minY = pt.y;
            if (pt.x > maxX) maxX = pt.x;
            if (pt.y > maxY) maxY = pt.y;
        }
    }
    if (!Number.isFinite(minX) || !Number.isFinite(minY)) return;
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const theta = -(rotationDeg || 0) * DEG_TO_RAD;
    const cos = Math.cos(theta);
    const sin = Math.sin(theta);

    const [r, g, b, a] = color;
    for (const stroke of layout.strokes) {
        if (stroke.length < 2) continue;
        const points: Vec2[] = [];
        for (const pt of stroke) {
            const lx = pt.x - cx;
            const ly = pt.y - cy;
            points.push(
                new Vec2(
                    x + lx * cos - ly * sin,
                    y + lx * sin + ly * cos,
                ),
            );
        }
        layer.geometry.add_polyline(points, thickness, r, g, b, a);
    }
}

function buildLayerMap(model: RenderModel): Map<string, LayerModel> {
    const layerById = new Map<string, LayerModel>();
    for (const layer of model.layers) {
        layerById.set(layer.id, layer);
    }
    return layerById;
}

function layerPaintOrder(layerName: string, layerById: Map<string, LayerModel>): number {
    return layerById.get(layerName)?.paint_order ?? Number.MAX_SAFE_INTEGER;
}

function layerKind(layerName: string, layerById: Map<string, LayerModel>): string {
    return (layerById.get(layerName)?.kind ?? "").toLowerCase();
}

function sortedLayerEntries<T>(
    layerMap: Map<string, T>,
    layerById: Map<string, LayerModel>,
): Array<[string, T]> {
    return [...layerMap.entries()].sort(([a], [b]) => {
        const orderDiff = layerPaintOrder(a, layerById) - layerPaintOrder(b, layerById);
        if (orderDiff !== 0) return orderDiff;
        return a.localeCompare(b);
    });
}

/** Paint the entire render model into renderer layers */
export function paintAll(renderer: Renderer, model: RenderModel, hiddenLayers?: Set<string>): void {
    const hidden = hiddenLayers ?? new Set<string>();
    const layerById = buildLayerMap(model);
    renderer.dispose_layers();
    if (!hidden.has("Edge.Cuts")) paintBoardEdges(renderer, model, layerById);
    paintGlobalDrawings(renderer, model, hidden, "non_copper", layerById);
    paintZones(renderer, model, hidden, layerById);
    paintTracks(renderer, model, hidden, layerById);
    paintGlobalDrawings(renderer, model, hidden, "copper", layerById);
    const orderedFootprints = [...model.footprints].sort(
        (a, b) => layerPaintOrder(a.layer, layerById) - layerPaintOrder(b.layer, layerById),
    );
    for (const fp of orderedFootprints) {
        paintFootprint(renderer, fp, hidden, layerById);
    }
    paintGlobalDrawings(renderer, model, hidden, "drill", layerById);
}

function paintBoardEdges(renderer: Renderer, model: RenderModel, layerById: Map<string, LayerModel>) {
    const layer = renderer.start_layer("Edge.Cuts");
    const [r, g, b, a] = getLayerColor("Edge.Cuts", layerById);

    for (const edge of model.board.edges) {
        if (edge.type === "line" && edge.start && edge.end) {
            layer.geometry.add_polyline([p2v(edge.start), p2v(edge.end)], 0.15, r, g, b, a);
        } else if (edge.type === "arc" && edge.start && edge.mid && edge.end) {
            layer.geometry.add_polyline(arcToPoints(edge.start, edge.mid, edge.end), 0.15, r, g, b, a);
        } else if (edge.type === "circle" && edge.center && edge.end) {
            const cx = edge.center.x, cy = edge.center.y;
            const rad = Math.sqrt((edge.end.x - cx) ** 2 + (edge.end.y - cy) ** 2);
            const pts: Vec2[] = [];
            for (let i = 0; i <= 64; i++) {
                const angle = (i / 64) * 2 * Math.PI;
                pts.push(new Vec2(cx + rad * Math.cos(angle), cy + rad * Math.sin(angle)));
            }
            layer.geometry.add_polyline(pts, 0.15, r, g, b, a);
        } else if (edge.type === "rect" && edge.start && edge.end) {
            const s = edge.start, e = edge.end;
            layer.geometry.add_polyline([
                new Vec2(s.x, s.y), new Vec2(e.x, s.y), new Vec2(e.x, e.y), new Vec2(s.x, e.y), new Vec2(s.x, s.y),
            ], 0.15, r, g, b, a);
        }
    }
    renderer.end_layer();
}

function paintZones(
    renderer: Renderer,
    model: RenderModel,
    hidden: Set<string>,
    layerById: Map<string, LayerModel>,
) {
    for (const zone of model.zones) {
        const sortedFilledPolygons = [...zone.filled_polygons].sort(
            (a, b) => layerPaintOrder(a.layer, layerById) - layerPaintOrder(b.layer, layerById),
        );
        for (const filled of sortedFilledPolygons) {
            if (hidden.has(filled.layer)) continue;
            const [r, g, b] = getLayerColor(filled.layer, layerById);
            const layer = renderer.start_layer(`zone_${zone.uuid ?? ""}:${filled.layer}`);
            const pts = filled.points.map(p2v);
            if (pts.length >= 3) {
                layer.geometry.add_polygon(pts, r, g, b, ZONE_COLOR_ALPHA);
            }
            renderer.end_layer();
        }

        const zoneLayersRaw = zone.layers.length > 0
            ? zone.layers
            : [...new Set(zone.filled_polygons.map(fp => fp.layer))];
        const zoneLayers = [...new Set(zoneLayersRaw)].sort(
            (a, b) => layerPaintOrder(a, layerById) - layerPaintOrder(b, layerById),
        );

        const shouldDrawFillFromOutline = (
            !zone.keepout
            && zone.fill_enabled !== false
            && zone.filled_polygons.length === 0
            && zone.outline.length >= 3
        );
        if (shouldDrawFillFromOutline) {
            const outlinePts = zone.outline.map(p2v);
            for (const layerName of zoneLayers) {
                if (!layerName || hidden.has(layerName)) continue;
                const [r, g, b] = getLayerColor(layerName, layerById);
                const layer = renderer.start_layer(`zone_outline_fill_${zone.uuid ?? ""}:${layerName}`);
                layer.geometry.add_polygon(outlinePts, r, g, b, ZONE_COLOR_ALPHA);
                renderer.end_layer();
            }
        }

        const shouldDrawKeepout = zone.keepout || zone.fill_enabled === false;
        if (!shouldDrawKeepout || zone.outline.length < 3) continue;

        const outlinePts = zone.outline.map(p2v);
        const closedOutline = [...outlinePts, outlinePts[0]!.copy()];
        const hatchPitch = zone.hatch_pitch && zone.hatch_pitch > 0 ? zone.hatch_pitch : 0.5;
        const hatchSegments = hatchSegmentsForPolygon(outlinePts, hatchPitch);
        for (const layerName of zoneLayers) {
            if (!layerName || hidden.has(layerName)) continue;
            const [r, g, b, a] = getLayerColor(layerName, layerById);
            const layer = renderer.start_layer(`zone_keepout_${zone.uuid ?? ""}:${layerName}`);
            layer.geometry.add_polyline(closedOutline, 0.1, r, g, b, Math.max(a, 0.8));
            for (const [start, end] of hatchSegments) {
                layer.geometry.add_polyline([start, end], 0.06, r, g, b, Math.max(a * 0.65, 0.45));
            }
            renderer.end_layer();
        }
    }
}

function hatchSegmentsForPolygon(points: Vec2[], pitch: number): Array<[Vec2, Vec2]> {
    if (points.length < 3 || pitch <= 0) return [];
    const eps = 1e-6;
    const closed = [...points, points[0]!];
    let minV = Infinity;
    let maxV = -Infinity;
    for (const p of points) {
        const v = p.y - p.x;
        if (v < minV) minV = v;
        if (v > maxV) maxV = v;
    }

    const segments: Array<[Vec2, Vec2]> = [];
    for (let c = minV - pitch; c <= maxV + pitch; c += pitch) {
        const rawIntersections: Vec2[] = [];
        for (let i = 0; i < closed.length - 1; i++) {
            const a = closed[i]!;
            const b = closed[i + 1]!;
            const fa = a.y - a.x - c;
            const fb = b.y - b.x - c;
            if ((fa > eps && fb > eps) || (fa < -eps && fb < -eps)) continue;
            const denom = fa - fb;
            if (Math.abs(denom) < eps) continue;
            const t = fa / denom;
            if (t < -eps || t > 1 + eps) continue;
            rawIntersections.push(
                new Vec2(
                    a.x + (b.x - a.x) * t,
                    a.y + (b.y - a.y) * t,
                ),
            );
        }

        rawIntersections.sort((p, q) => (p.x - q.x) || (p.y - q.y));
        const intersections: Vec2[] = [];
        for (const p of rawIntersections) {
            const last = intersections[intersections.length - 1];
            if (!last || Math.abs(last.x - p.x) > eps || Math.abs(last.y - p.y) > eps) {
                intersections.push(p);
            }
        }
        for (let i = 0; i + 1 < intersections.length; i += 2) {
            segments.push([intersections[i]!, intersections[i + 1]!]);
        }
    }
    return segments;
}

function paintTracks(
    renderer: Renderer,
    model: RenderModel,
    hidden: Set<string>,
    layerById: Map<string, LayerModel>,
) {
    const byLayer = new Map<string, TrackModel[]>();
    for (const track of model.tracks) {
        const ln = track.layer;
        if (!ln) continue;
        if (hidden.has(ln)) continue;
        let arr = byLayer.get(ln);
        if (!arr) { arr = []; byLayer.set(ln, arr); }
        arr.push(track);
    }
    for (const [layerName, tracks] of sortedLayerEntries(byLayer, layerById)) {
        const [r, g, b, a] = getLayerColor(layerName, layerById);
        const layer = renderer.start_layer(`tracks:${layerName}`);
        for (const track of tracks) {
            layer.geometry.add_polyline([p2v(track.start), p2v(track.end)], track.width, r, g, b, a);
        }
        renderer.end_layer();
    }
    if (model.arcs.length > 0) {
        const arcByLayer = new Map<string, typeof model.arcs>();
        for (const arc of model.arcs) {
            const ln = arc.layer;
            if (!ln) continue;
            if (hidden.has(ln)) continue;
            let arr = arcByLayer.get(ln);
            if (!arr) { arr = []; arcByLayer.set(ln, arr); }
            arr.push(arc);
        }
        for (const [layerName, arcs] of sortedLayerEntries(arcByLayer, layerById)) {
            const [r, g, b, a] = getLayerColor(layerName, layerById);
            const layer = renderer.start_layer(`arc_tracks:${layerName}`);
            for (const arc of arcs) {
                layer.geometry.add_polyline(arcToPoints(arc.start, arc.mid, arc.end), arc.width, r, g, b, a);
            }
            renderer.end_layer();
        }
    }
}

function isDrillLayer(layerName: string | null | undefined, layerById: Map<string, LayerModel>): boolean {
    return layerName !== null && layerName !== undefined && layerKind(layerName, layerById) === "drill";
}

function isCopperLayer(layerName: string | null | undefined, layerById: Map<string, LayerModel>): boolean {
    return layerName !== null && layerName !== undefined && layerKind(layerName, layerById) === "cu";
}

type GlobalDrawingPaintMode = "drill" | "copper" | "non_copper";

function shouldPaintGlobalDrawing(
    layerName: string,
    mode: GlobalDrawingPaintMode,
    layerById: Map<string, LayerModel>,
): boolean {
    const drill = isDrillLayer(layerName, layerById);
    const copper = isCopperLayer(layerName, layerById);
    if (mode === "drill") return drill;
    if (mode === "copper") return !drill && copper;
    return !drill && !copper;
}

function paintGlobalDrawings(
    renderer: Renderer,
    model: RenderModel,
    hidden: Set<string>,
    mode: GlobalDrawingPaintMode,
    layerById: Map<string, LayerModel>,
) {
    const byLayer = new Map<string, DrawingModel[]>();
    for (const drawing of model.drawings) {
        const ln = drawing.layer;
        if (!ln) continue;
        if (!shouldPaintGlobalDrawing(ln, mode, layerById)) continue;
        if (hidden.has(ln)) continue;
        let arr = byLayer.get(ln);
        if (!arr) { arr = []; byLayer.set(ln, arr); }
        arr.push(drawing);
    }
    const worldAt: Point3 = { x: 0, y: 0, r: 0 };
    for (const [layerName, drawings] of sortedLayerEntries(byLayer, layerById)) {
        const [r, g, b, a] = getLayerColor(layerName, layerById);
        const layer = renderer.start_layer(`global:${layerName}`);
        for (const drawing of drawings) {
            paintDrawing(layer, worldAt, drawing, r, g, b, a);
        }
        renderer.end_layer();
    }
}

function paintFootprint(
    renderer: Renderer,
    fp: FootprintModel,
    hidden: Set<string>,
    layerById: Map<string, LayerModel>,
) {
    const drawingsByLayer = new Map<string, DrawingModel[]>();
    const drillDrawingsByLayer = new Map<string, DrawingModel[]>();
    for (const drawing of fp.drawings) {
        const ln = drawing.layer;
        if (!ln) continue;
        if (hidden.has(ln)) continue;
        const map = isDrillLayer(ln, layerById) ? drillDrawingsByLayer : drawingsByLayer;
        let arr = map.get(ln);
        if (!arr) {
            arr = [];
            map.set(ln, arr);
        }
        arr.push(drawing);
    }
    for (const [layerName, drawings] of sortedLayerEntries(drawingsByLayer, layerById)) {
        const [r, g, b, a] = getLayerColor(layerName, layerById);
        const layer = renderer.start_layer(`fp:${fp.uuid}:${layerName}`);
        for (const drawing of drawings) {
            paintDrawing(layer, fp.at, drawing, r, g, b, a);
        }
        renderer.end_layer();
    }
    if (fp.pads.length > 0) {
        const anyVisible = fp.pads.some(pad =>
            pad.layers.some(layerName => !hidden.has(layerName))
        );
        if (anyVisible) {
            const layer = renderer.start_layer(`fp:${fp.uuid}:pads`);
            const visiblePads = fp.pads.filter(pad =>
                pad.layers.some(layerName => !hidden.has(layerName))
            );
            for (const pad of visiblePads) {
                paintPad(layer, fp.at, pad, layerById);
            }
            renderer.end_layer();
        }
    }
    for (const [layerName, drawings] of sortedLayerEntries(drillDrawingsByLayer, layerById)) {
        const [r, g, b, a] = getLayerColor(layerName, layerById);
        const layer = renderer.start_layer(`fp:${fp.uuid}:${layerName}`);
        for (const drawing of drawings) {
            paintDrawing(layer, fp.at, drawing, r, g, b, a);
        }
        renderer.end_layer();
    }
    paintPadAnnotations(renderer, fp, hidden, layerById);
}

function paintPadAnnotations(
    renderer: Renderer,
    fp: FootprintModel,
    hidden: Set<string>,
    layerById: Map<string, LayerModel>,
) {
    if (fp.pads.length === 0) return;
    if (fp.pad_names.length === 0 && fp.pad_numbers.length === 0) return;

    const resolvePad = (padIndex: number, padName: string): PadModel | null => {
        const byIndex = fp.pads[padIndex];
        if (byIndex && byIndex.name === padName) {
            return byIndex;
        }
        return null;
    };

    type NameGeometry = {
        text: string;
        x: number;
        y: number;
        rotation: number;
        charW: number;
        charH: number;
        thickness: number;
    };
    type NumberGeometry = {
        text: string;
        badgeCenterX: number;
        badgeCenterY: number;
        badgeRadius: number;
        labelFit: [number, number, number] | null;
    };
    type LayerAnnotationGeometry = {
        names: NameGeometry[];
        numbers: NumberGeometry[];
    };

    const layerGeometry = new Map<string, LayerAnnotationGeometry>();
    const ensureLayerGeometry = (layerName: string): LayerAnnotationGeometry => {
        let entry = layerGeometry.get(layerName);
        if (!entry) {
            entry = { names: [], numbers: [] };
            layerGeometry.set(layerName, entry);
        }
        return entry;
    };

    for (const annotation of fp.pad_names) {
        if (!annotation.text.trim()) continue;
        const pad = resolvePad(annotation.pad_index, annotation.pad);
        if (!pad) continue;
        const totalRotation = (fp.at.r || 0) + (pad.at.r || 0);
        const [bboxW, bboxH] = rotatedRectExtents(pad.size.w, pad.size.h, totalRotation);
        const fitted = fitPadNameLabel(annotation.text, bboxW, bboxH);
        if (!fitted) continue;
        const [displayText, [charW, charH, thickness]] = fitted;
        const worldCenter = fpTransform(fp.at, pad.at.x, pad.at.y);
        const textRotation = padLabelWorldRotation(totalRotation, pad.size.w, pad.size.h);
        for (const layerName of annotation.layer_ids) {
            if (hidden.has(layerName)) continue;
            ensureLayerGeometry(layerName).names.push({
                text: displayText,
                x: worldCenter.x,
                y: worldCenter.y,
                rotation: textRotation,
                charW,
                charH,
                thickness,
            });
        }
    }

    for (const annotation of fp.pad_numbers) {
        if (!annotation.text.trim()) continue;
        const pad = resolvePad(annotation.pad_index, annotation.pad);
        if (!pad) continue;
        const totalRotation = (fp.at.r || 0) + (pad.at.r || 0);
        const [bboxW, bboxH] = rotatedRectExtents(pad.size.w, pad.size.h, totalRotation);
        const badgeDiameter = Math.max(Math.min(bboxW, bboxH) * PAD_NUMBER_BADGE_SIZE_RATIO, 0.18);
        const badgeRadius = badgeDiameter / 2;
        const margin = Math.max(Math.min(bboxW, bboxH) * PAD_NUMBER_BADGE_MARGIN_RATIO, 0.03);
        const worldCenter = fpTransform(fp.at, pad.at.x, pad.at.y);
        const badgeCenterX = worldCenter.x - (bboxW / 2) + margin + badgeRadius;
        const badgeCenterY = worldCenter.y - (bboxH / 2) + margin + badgeRadius;
        const labelFit = fitTextInsideBox(
            annotation.text,
            badgeDiameter * 0.92,
            badgeDiameter * 0.92,
            PAD_NUMBER_MIN_CHAR_H,
            PAD_NUMBER_CHAR_SCALE,
        );
        for (const layerName of annotation.layer_ids) {
            if (hidden.has(layerName)) continue;
            ensureLayerGeometry(layerName).numbers.push({
                text: annotation.text,
                badgeCenterX,
                badgeCenterY,
                badgeRadius,
                labelFit,
            });
        }
    }

    const orderedAnnotationLayers = [...layerGeometry.keys()].sort(
        (a, b) => layerPaintOrder(a, layerById) - layerPaintOrder(b, layerById),
    );
    for (const layerName of orderedAnnotationLayers) {
        const geometry = layerGeometry.get(layerName);
        if (!geometry) continue;
        const layer = renderer.start_layer(`fp:${fp.uuid}:annotations:${layerName}`);
        const [r, g, b, a] = getLayerColor(layerName, layerById);

        for (const name of geometry.names) {
            drawStrokeTextGeometry(
                layer,
                name.text,
                name.x,
                name.y,
                name.rotation,
                name.charW,
                name.charH,
                name.thickness,
                [r, g, b, a],
            );
        }

        for (const number of geometry.numbers) {
            layer.geometry.add_circle(number.badgeCenterX, number.badgeCenterY, number.badgeRadius, r, g, b, Math.max(a, 0.98));
            const outlinePoints = circleToPoints(number.badgeCenterX, number.badgeCenterY, number.badgeRadius);
            if (outlinePoints.length > 1) {
                layer.geometry.add_polyline(outlinePoints, Math.max(number.badgeRadius * 0.18, 0.04), 0.05, 0.08, 0.12, 0.8);
            }
            if (number.labelFit) {
                const [charW, charH, thickness] = number.labelFit;
                drawStrokeTextGeometry(
                    layer,
                    number.text,
                    number.badgeCenterX,
                    number.badgeCenterY,
                    0,
                    charW,
                    charH,
                    thickness,
                    [0.05, 0.08, 0.12, 0.98],
                );
            }
        }

        renderer.end_layer();
    }
}

function paintDrawing(layer: RenderLayer, fpAt: Point3, drawing: DrawingModel, r: number, g: number, b: number, a: number) {
    const rawWidth = Number.isFinite(drawing.width) ? drawing.width : 0;
    const strokeWidth = rawWidth > 0 ? rawWidth : (drawing.filled ? 0 : 0.12);

    if (drawing.type === "line" && drawing.start && drawing.end) {
        const p1 = fpTransform(fpAt, drawing.start.x, drawing.start.y);
        const p2 = fpTransform(fpAt, drawing.end.x, drawing.end.y);
        layer.geometry.add_polyline([p1, p2], strokeWidth, r, g, b, a);
    } else if (drawing.type === "arc" && drawing.start && drawing.mid && drawing.end) {
        const localPts = arcToPoints(drawing.start, drawing.mid, drawing.end);
        const worldPts = localPts.map(p => fpTransform(fpAt, p.x, p.y));
        layer.geometry.add_polyline(worldPts, strokeWidth, r, g, b, a);
    } else if (drawing.type === "circle" && drawing.center && drawing.end) {
        const cx = drawing.center.x, cy = drawing.center.y;
        const rad = Math.sqrt((drawing.end.x - cx) ** 2 + (drawing.end.y - cy) ** 2);
        const pts: Vec2[] = [];
        for (let i = 0; i <= 48; i++) {
            const angle = (i / 48) * 2 * Math.PI;
            pts.push(new Vec2(cx + rad * Math.cos(angle), cy + rad * Math.sin(angle)));
        }
        const worldPts = pts.map(p => fpTransform(fpAt, p.x, p.y));
        if (drawing.filled && worldPts.length >= 3) {
            layer.geometry.add_polygon(worldPts, r, g, b, a);
        }
        if (strokeWidth > 0) {
            layer.geometry.add_polyline(worldPts, strokeWidth, r, g, b, a);
        }
    } else if (drawing.type === "rect" && drawing.start && drawing.end) {
        const s = drawing.start, e = drawing.end;
        const corners = [
            fpTransform(fpAt, s.x, s.y), fpTransform(fpAt, e.x, s.y),
            fpTransform(fpAt, e.x, e.y), fpTransform(fpAt, s.x, e.y),
        ];
        if (drawing.filled) {
            layer.geometry.add_polygon(corners, r, g, b, a);
        }
        if (strokeWidth > 0) {
            layer.geometry.add_polyline([...corners, corners[0]!.copy()], strokeWidth, r, g, b, a);
        }
    } else if (drawing.type === "polygon" && drawing.points) {
        const worldPts = drawing.points.map(p => fpTransform(fpAt, p.x, p.y));
        if (worldPts.length >= 3) {
            if (drawing.filled) {
                layer.geometry.add_polygon(worldPts, r, g, b, a);
            }
            if (strokeWidth > 0) {
                layer.geometry.add_polyline([...worldPts, worldPts[0]!.copy()], strokeWidth, r, g, b, a);
            }
        }
    } else if (drawing.type === "curve" && drawing.points) {
        const worldPts = drawing.points.map(p => fpTransform(fpAt, p.x, p.y));
        if (worldPts.length >= 2) {
            layer.geometry.add_polyline(worldPts, strokeWidth, r, g, b, a);
        }
    }
}

function paintPad(
    layer: RenderLayer,
    fpAt: Point3,
    pad: PadModel,
    layerById: Map<string, LayerModel>,
) {
    if (pad.layers.length === 0) {
        return;
    }
    const [cr, cg, cb, ca] = getPadColor(pad.layers, layerById);
    const hw = pad.size.w / 2;
    const hh = pad.size.h / 2;

    if (pad.shape === "circle") {
        const center = fpTransform(fpAt, pad.at.x, pad.at.y);
        layer.geometry.add_circle(center.x, center.y, hw, cr, cg, cb, ca);
    } else if (pad.shape === "oval") {
        const longAxis = Math.max(hw, hh);
        const shortAxis = Math.min(hw, hh);
        const focalDist = longAxis - shortAxis;
        let p1: Vec2, p2: Vec2;
        if (hw >= hh) {
            p1 = padTransform(fpAt, pad.at, -focalDist, 0);
            p2 = padTransform(fpAt, pad.at, focalDist, 0);
        } else {
            p1 = padTransform(fpAt, pad.at, 0, -focalDist);
            p2 = padTransform(fpAt, pad.at, 0, focalDist);
        }
        layer.geometry.add_polyline([p1, p2], shortAxis * 2, cr, cg, cb, ca);
    } else {
        const corners = [
            padTransform(fpAt, pad.at, -hw, -hh), padTransform(fpAt, pad.at, hw, -hh),
            padTransform(fpAt, pad.at, hw, hh), padTransform(fpAt, pad.at, -hw, hh),
        ];
        layer.geometry.add_polygon(corners, cr, cg, cb, ca);
    }

    // Pad holes are rendered in dedicated depth layers (see paintFootprint).
}

/** Paint a selection highlight around a footprint */
export function paintSelection(renderer: Renderer, fp: FootprintModel): void {
    const layer = renderer.start_layer("selection");
    drawFootprintSelectionBox(layer, fp, SELECTION_STROKE_WIDTH, 0.85, SELECTION_GROW, 0.12);
    renderer.end_layer();
}

/** Paint per-member halos for a selected/hovered footprint group. */
export function paintGroupHalos(
    renderer: Renderer,
    footprints: FootprintModel[],
    memberIndices: number[],
    mode: "selected" | "hover",
): null {
    if (memberIndices.length === 0) return null;
    const layer = renderer.start_layer(mode === "selected" ? "group-selection" : "group-hover");
    const strokeWidth = mode === "selected" ? GROUP_SELECTION_STROKE_WIDTH : HOVER_SELECTION_STROKE_WIDTH;
    const alpha = mode === "selected" ? 0.7 : 0.45;
    const grow = mode === "selected" ? GROUP_SELECTION_GROW : HOVER_SELECTION_GROW;
    const fillAlpha = mode === "selected" ? 0.09 : 0.055;
    for (const index of memberIndices) {
        const fp = footprints[index];
        if (!fp) continue;
        drawFootprintSelectionBox(layer, fp, strokeWidth, alpha, grow, fillAlpha);
    }
    renderer.end_layer();
    return null;
}

/** Compute a bounding box for the full render model */
export function computeBBox(model: RenderModel): BBox {
    const points: Vec2[] = [];
    for (const edge of model.board.edges) {
        if (edge.start) points.push(p2v(edge.start));
        if (edge.end) points.push(p2v(edge.end));
        if (edge.mid) points.push(p2v(edge.mid));
        if (edge.center) points.push(p2v(edge.center));
    }
    for (const drawing of model.drawings) {
        if (drawing.start) points.push(p2v(drawing.start));
        if (drawing.end) points.push(p2v(drawing.end));
        if (drawing.mid) points.push(p2v(drawing.mid));
        if (drawing.center) points.push(p2v(drawing.center));
        if (drawing.points) {
            for (const p of drawing.points) points.push(p2v(p));
        }
    }
    for (const text of model.texts) {
        points.push(new Vec2(text.at.x, text.at.y));
    }
    for (const fp of model.footprints) {
        points.push(new Vec2(fp.at.x, fp.at.y));
        for (const pad of fp.pads) {
            points.push(fpTransform(fp.at, pad.at.x, pad.at.y));
        }
        for (const text of fp.texts) {
            points.push(fpTransform(fp.at, text.at.x, text.at.y));
        }
    }
    for (const track of model.tracks) {
        points.push(p2v(track.start));
        points.push(p2v(track.end));
    }
    if (points.length === 0) return new BBox(0, 0, 100, 100);
    return BBox.from_points(points).grow(5);
}
