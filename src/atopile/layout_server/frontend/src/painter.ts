import { Vec2, BBox } from "./math";
import { Renderer, RenderLayer } from "./webgl/renderer";
import { getLayerColor, getPadColor, VIA_COLOR, VIA_DRILL_COLOR, SELECTION_COLOR, ZONE_COLOR_ALPHA } from "./colors";
import type { RenderModel, FootprintModel, PadModel, TrackModel, DrawingModel, Point2, Point3 } from "./types";

const DEG_TO_RAD = Math.PI / 180;

function p2v(p: Point2): Vec2 {
    return new Vec2(p.x, p.y);
}

/** Transform a local point by a footprint's position + rotation */
function fpTransform(fpAt: Point3, localX: number, localY: number): Vec2 {
    const rad = -(fpAt.r || 0) * DEG_TO_RAD;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);
    return new Vec2(
        fpAt.x + localX * cos - localY * sin,
        fpAt.y + localX * sin + localY * cos,
    );
}

/** Transform by pad rotation, then footprint rotation */
function padTransform(fpAt: Point3, padAt: Point3, lx: number, ly: number): Vec2 {
    const padRad = -(padAt.r || 0) * DEG_TO_RAD;
    const pc = Math.cos(padRad), ps = Math.sin(padRad);
    const px = lx * pc - ly * ps;
    const py = lx * ps + ly * pc;
    return fpTransform(fpAt, padAt.x + px, padAt.y + py);
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

/**
 * Check if a pad layer (possibly a wildcard) has any visible concrete layer.
 * Wildcards: "*.Cu" matches all layers ending in ".Cu",
 *            "F&B.Cu" matches "F.Cu" and "B.Cu".
 */
function isPadLayerVisible(padLayer: string, hidden: Set<string>, concreteLayers: Set<string>): boolean {
    if (padLayer.includes("*")) {
        // *.Suffix — visible if any concrete layer with that suffix is not hidden
        const suffix = padLayer.substring(padLayer.indexOf("."));
        for (const l of concreteLayers) {
            if (l.endsWith(suffix) && !hidden.has(l)) return true;
        }
        return false;
    }
    if (padLayer.includes("&")) {
        // A&B.Suffix — expand to A.Suffix, B.Suffix
        const dotIdx = padLayer.indexOf(".");
        if (dotIdx >= 0) {
            const prefixes = padLayer.substring(0, dotIdx).split("&");
            const suffix = padLayer.substring(dotIdx);
            return prefixes.some(p => !hidden.has(p + suffix));
        }
    }
    return !hidden.has(padLayer);
}

/** Collect all concrete (non-wildcard) layer names from the model */
function collectConcreteLayers(model: RenderModel): Set<string> {
    const layers = new Set<string>();
    for (const d of model.drawings) if (d.layer) layers.add(d.layer);
    for (const t of model.texts) if (t.layer) layers.add(t.layer);
    for (const fp of model.footprints) {
        layers.add(fp.layer);
        for (const pad of fp.pads) {
            for (const l of pad.layers) layers.add(l);
        }
        for (const d of fp.drawings) if (d.layer) layers.add(d.layer);
        for (const t of fp.texts) if (t.layer) layers.add(t.layer);
    }
    for (const t of model.tracks) if (t.layer) layers.add(t.layer);
    for (const a of model.arcs) if (a.layer) layers.add(a.layer);
    for (const z of model.zones) {
        for (const f of z.filled_polygons) layers.add(f.layer);
    }
    for (const l of layers) {
        if (l.includes("*") || l.includes("&")) layers.delete(l);
    }
    return layers;
}

/** Paint the entire render model into renderer layers */
export function paintAll(renderer: Renderer, model: RenderModel, hiddenLayers?: Set<string>): void {
    const hidden = hiddenLayers ?? new Set<string>();
    const concreteLayers = collectConcreteLayers(model);
    renderer.dispose_layers();
    if (!hidden.has("Edge.Cuts")) paintBoardEdges(renderer, model);
    paintGlobalDrawings(renderer, model, hidden);
    paintZones(renderer, model, hidden);
    paintTracks(renderer, model, hidden);
    if (!hidden.has("Vias")) paintVias(renderer, model);
    for (const fp of model.footprints) {
        paintFootprint(renderer, fp, hidden, concreteLayers);
    }
}

function paintBoardEdges(renderer: Renderer, model: RenderModel) {
    const layer = renderer.start_layer("Edge.Cuts");
    const [r, g, b, a] = getLayerColor("Edge.Cuts");

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

function paintZones(renderer: Renderer, model: RenderModel, hidden: Set<string>) {
    for (const zone of model.zones) {
        for (const filled of zone.filled_polygons) {
            if (hidden.has(filled.layer)) continue;
            const [r, g, b] = getLayerColor(filled.layer);
            const layer = renderer.start_layer(`zone_${zone.uuid ?? ""}:${filled.layer}`);
            const pts = filled.points.map(p2v);
            if (pts.length >= 3) {
                layer.geometry.add_polygon(pts, r, g, b, ZONE_COLOR_ALPHA);
            }
            renderer.end_layer();
        }

        const shouldDrawKeepout = zone.keepout || zone.filled_polygons.length === 0 || zone.fill_enabled === false;
        if (!shouldDrawKeepout || zone.outline.length < 3) continue;

        const zoneLayers = zone.layers.length > 0
            ? zone.layers
            : [...new Set(zone.filled_polygons.map(fp => fp.layer))];
        const outlinePts = zone.outline.map(p2v);
        const closedOutline = [...outlinePts, outlinePts[0]!.copy()];
        const hatchPitch = zone.hatch_pitch && zone.hatch_pitch > 0 ? zone.hatch_pitch : 0.5;
        const hatchSegments = hatchSegmentsForPolygon(outlinePts, hatchPitch);
        for (const layerName of zoneLayers) {
            if (!layerName || hidden.has(layerName)) continue;
            const [r, g, b, a] = getLayerColor(layerName);
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

function paintTracks(renderer: Renderer, model: RenderModel, hidden: Set<string>) {
    const byLayer = new Map<string, TrackModel[]>();
    for (const track of model.tracks) {
        const ln = track.layer ?? "F.Cu";
        if (hidden.has(ln)) continue;
        let arr = byLayer.get(ln);
        if (!arr) { arr = []; byLayer.set(ln, arr); }
        arr.push(track);
    }
    for (const [layerName, tracks] of byLayer) {
        const [r, g, b, a] = getLayerColor(layerName);
        const layer = renderer.start_layer(`tracks:${layerName}`);
        for (const track of tracks) {
            layer.geometry.add_polyline([p2v(track.start), p2v(track.end)], track.width, r, g, b, a);
        }
        renderer.end_layer();
    }
    if (model.arcs.length > 0) {
        const arcByLayer = new Map<string, typeof model.arcs>();
        for (const arc of model.arcs) {
            const ln = arc.layer ?? "F.Cu";
            if (hidden.has(ln)) continue;
            let arr = arcByLayer.get(ln);
            if (!arr) { arr = []; arcByLayer.set(ln, arr); }
            arr.push(arc);
        }
        for (const [layerName, arcs] of arcByLayer) {
            const [r, g, b, a] = getLayerColor(layerName);
            const layer = renderer.start_layer(`arc_tracks:${layerName}`);
            for (const arc of arcs) {
                layer.geometry.add_polyline(arcToPoints(arc.start, arc.mid, arc.end), arc.width, r, g, b, a);
            }
            renderer.end_layer();
        }
    }
}

function paintVias(renderer: Renderer, model: RenderModel) {
    if (model.vias.length === 0) return;
    const layer = renderer.start_layer("vias");
    for (const via of model.vias) {
        const [vr, vg, vb, va] = VIA_COLOR;
        layer.geometry.add_circle(via.at.x, via.at.y, via.size / 2, vr, vg, vb, va);
        const [dr, dg, db, da] = VIA_DRILL_COLOR;
        layer.geometry.add_circle(via.at.x, via.at.y, via.drill / 2, dr, dg, db, da);
    }
    renderer.end_layer();
}

function paintGlobalDrawings(renderer: Renderer, model: RenderModel, hidden: Set<string>) {
    const byLayer = new Map<string, DrawingModel[]>();
    for (const drawing of model.drawings) {
        const ln = drawing.layer ?? "Dwgs.User";
        if (hidden.has(ln)) continue;
        let arr = byLayer.get(ln);
        if (!arr) { arr = []; byLayer.set(ln, arr); }
        arr.push(drawing);
    }
    const worldAt: Point3 = { x: 0, y: 0, r: 0 };
    for (const [layerName, drawings] of byLayer) {
        const [r, g, b, a] = getLayerColor(layerName);
        const layer = renderer.start_layer(`global:${layerName}`);
        for (const drawing of drawings) {
            paintDrawing(layer, worldAt, drawing, r, g, b, a);
        }
        renderer.end_layer();
    }
}

function paintFootprint(renderer: Renderer, fp: FootprintModel, hidden: Set<string>, concreteLayers: Set<string>) {
    const drawingsByLayer = new Map<string, DrawingModel[]>();
    for (const drawing of fp.drawings) {
        const ln = drawing.layer ?? "F.SilkS";
        if (hidden.has(ln)) continue;
        let arr = drawingsByLayer.get(ln);
        if (!arr) { arr = []; drawingsByLayer.set(ln, arr); }
        arr.push(drawing);
    }
    for (const [layerName, drawings] of drawingsByLayer) {
        const [r, g, b, a] = getLayerColor(layerName);
        const layer = renderer.start_layer(`fp:${fp.uuid}:${layerName}`);
        for (const drawing of drawings) {
            paintDrawing(layer, fp.at, drawing, r, g, b, a);
        }
        renderer.end_layer();
    }
    if (fp.pads.length > 0) {
        // Check if any pad layer is visible (expanding wildcards)
        const anyVisible = fp.pads.some(pad =>
            pad.layers.some(l => isPadLayerVisible(l, hidden, concreteLayers))
        );
        if (anyVisible) {
            const layer = renderer.start_layer(`fp:${fp.uuid}:pads`);
            for (const pad of fp.pads) {
                if (pad.layers.some(l => isPadLayerVisible(l, hidden, concreteLayers))) {
                    paintPad(layer, fp.at, pad);
                }
            }
            renderer.end_layer();
        }
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

function paintPad(layer: RenderLayer, fpAt: Point3, pad: PadModel) {
    const [cr, cg, cb, ca] = getPadColor(pad.layers);
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

    if (pad.drill && pad.type === "thru_hole") {
        const center = fpTransform(fpAt, pad.at.x, pad.at.y);
        const drillR = (pad.drill.size_x ?? pad.size.w * 0.5) / 2;
        layer.geometry.add_circle(center.x, center.y, drillR, 0.15, 0.15, 0.15, 1.0);
    }
}

/** Paint a selection highlight around a footprint */
export function paintSelection(renderer: Renderer, fp: FootprintModel): RenderLayer {
    const layer = renderer.start_layer("selection");
    const [r, g, b, a] = SELECTION_COLOR;

    const allPoints: Vec2[] = [];
    for (const pad of fp.pads) {
        const center = fpTransform(fp.at, pad.at.x, pad.at.y);
        const hw = pad.size.w / 2, hh = pad.size.h / 2;
        allPoints.push(center.add(new Vec2(-hw, -hh)));
        allPoints.push(center.add(new Vec2(hw, hh)));
    }
    for (const drawing of fp.drawings) {
        if (drawing.start) allPoints.push(fpTransform(fp.at, drawing.start.x, drawing.start.y));
        if (drawing.end) allPoints.push(fpTransform(fp.at, drawing.end.x, drawing.end.y));
        if (drawing.center) allPoints.push(fpTransform(fp.at, drawing.center.x, drawing.center.y));
    }
    for (const text of fp.texts) {
        allPoints.push(fpTransform(fp.at, text.at.x, text.at.y));
    }

    if (allPoints.length > 0) {
        const bbox = BBox.from_points(allPoints).grow(0.5);
        layer.geometry.add_polygon([
            new Vec2(bbox.x, bbox.y), new Vec2(bbox.x2, bbox.y),
            new Vec2(bbox.x2, bbox.y2), new Vec2(bbox.x, bbox.y2),
        ], r, g, b, a);
    }

    renderer.end_layer();
    return layer;
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
    for (const via of model.vias) {
        points.push(p2v(via.at));
    }
    if (points.length === 0) return new BBox(0, 0, 100, 100);
    return BBox.from_points(points).grow(5);
}
