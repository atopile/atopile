import { Vec2, Matrix3, BBox } from "./math";
import { Renderer, RenderLayer } from "./webgl/renderer";
import { getLayerColor, getPadColor, VIA_COLOR, VIA_DRILL_COLOR, SELECTION_COLOR, ZONE_COLOR_ALPHA } from "./colors";
import type { RenderModel, FootprintModel, PadModel, TrackModel, ViaModel, DrawingModel, ZoneModel } from "./types";

const DEG_TO_RAD = Math.PI / 180;

/** Transform a point relative to a footprint (apply fp position + rotation) */
function fpTransform(fpAt: [number, number, number], localX: number, localY: number): Vec2 {
    const rad = -(fpAt[2] || 0) * DEG_TO_RAD;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);
    const rx = localX * cos - localY * sin;
    const ry = localX * sin + localY * cos;
    return new Vec2(fpAt[0] + rx, fpAt[1] + ry);
}

/** Transform a point with both pad rotation and footprint rotation */
function padTransform(fpAt: [number, number, number], padAt: [number, number, number], localX: number, localY: number): Vec2 {
    // First apply pad rotation
    const padRad = -(padAt[2] || 0) * DEG_TO_RAD;
    const pc = Math.cos(padRad), ps = Math.sin(padRad);
    const px = localX * pc - localY * ps;
    const py = localX * ps + localY * pc;
    // Then offset by pad position and apply fp transform
    return fpTransform(fpAt, padAt[0] + px, padAt[1] + py);
}

/** Approximate an arc (start, mid, end) with line segments */
function arcToPoints(start: [number, number], mid: [number, number], end: [number, number], segments = 32): Vec2[] {
    // Find center of circle through 3 points
    const ax = start[0], ay = start[1];
    const bx = mid[0], by = mid[1];
    const cx = end[0], cy = end[1];

    const D = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by));
    if (Math.abs(D) < 1e-10) {
        return [new Vec2(ax, ay), new Vec2(bx, by), new Vec2(cx, cy)];
    }

    const ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / D;
    const uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / D;

    const radius = Math.sqrt((ax - ux) ** 2 + (ay - uy) ** 2);
    let startAngle = Math.atan2(ay - uy, ax - ux);
    const midAngle = Math.atan2(by - uy, bx - ux);
    let endAngle = Math.atan2(cy - uy, cx - ux);

    // Determine direction
    let da1 = midAngle - startAngle;
    let da2 = endAngle - midAngle;
    while (da1 > Math.PI) da1 -= 2 * Math.PI;
    while (da1 < -Math.PI) da1 += 2 * Math.PI;
    while (da2 > Math.PI) da2 -= 2 * Math.PI;
    while (da2 < -Math.PI) da2 += 2 * Math.PI;

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

/** Paint the entire render model into renderer layers */
export function paintAll(renderer: Renderer, model: RenderModel): void {
    renderer.dispose_layers();

    // 1. Board edges
    paintBoardEdges(renderer, model);

    // 2. Zones (filled)
    paintZones(renderer, model);

    // 3. Tracks
    paintTracks(renderer, model);

    // 4. Vias
    paintVias(renderer, model);

    // 5. Footprints (pads + drawings)
    for (const fp of model.footprints) {
        paintFootprint(renderer, fp);
    }
}

function paintBoardEdges(renderer: Renderer, model: RenderModel) {
    const layer = renderer.start_layer("Edge.Cuts");
    const [r, g, b, a] = getLayerColor("Edge.Cuts");

    for (const edge of model.board.edges) {
        if (edge.type === "line" && edge.start && edge.end) {
            layer.geometry.add_polyline(
                [new Vec2(edge.start[0], edge.start[1]), new Vec2(edge.end[0], edge.end[1])],
                0.15, r, g, b, a,
            );
        } else if (edge.type === "arc" && edge.start && edge.mid && edge.end) {
            const pts = arcToPoints(edge.start, edge.mid, edge.end);
            layer.geometry.add_polyline(pts, 0.15, r, g, b, a);
        } else if (edge.type === "circle" && edge.center && edge.end) {
            const cx = edge.center[0], cy = edge.center[1];
            const ex = edge.end[0], ey = edge.end[1];
            const rad = Math.sqrt((ex - cx) ** 2 + (ey - cy) ** 2);
            const pts: Vec2[] = [];
            const segs = 64;
            for (let i = 0; i <= segs; i++) {
                const angle = (i / segs) * 2 * Math.PI;
                pts.push(new Vec2(cx + rad * Math.cos(angle), cy + rad * Math.sin(angle)));
            }
            layer.geometry.add_polyline(pts, 0.15, r, g, b, a);
        } else if (edge.type === "rect" && edge.start && edge.end) {
            const [x1, y1] = edge.start;
            const [x2, y2] = edge.end;
            layer.geometry.add_polyline([
                new Vec2(x1, y1), new Vec2(x2, y1), new Vec2(x2, y2), new Vec2(x1, y2), new Vec2(x1, y1),
            ], 0.15, r, g, b, a);
        }
    }
    renderer.end_layer();
}

function paintZones(renderer: Renderer, model: RenderModel) {
    for (const zone of model.zones) {
        for (const filled of zone.filled_polygons) {
            const layerName = filled.layer;
            const [r, g, b] = getLayerColor(layerName);
            const layer = renderer.start_layer(`zone_${zone.uuid ?? ""}:${layerName}`);
            const pts = filled.points.map(([x, y]) => new Vec2(x, y));
            if (pts.length >= 3) {
                layer.geometry.add_polygon(pts, r, g, b, ZONE_COLOR_ALPHA);
            }
            renderer.end_layer();
        }
    }
}

function paintTracks(renderer: Renderer, model: RenderModel) {
    // Group tracks by layer for efficiency
    const byLayer = new Map<string, TrackModel[]>();
    for (const track of model.tracks) {
        const layerName = track.layer ?? "F.Cu";
        let arr = byLayer.get(layerName);
        if (!arr) { arr = []; byLayer.set(layerName, arr); }
        arr.push(track);
    }

    for (const [layerName, tracks] of byLayer) {
        const [r, g, b, a] = getLayerColor(layerName);
        const layer = renderer.start_layer(`tracks:${layerName}`);
        for (const track of tracks) {
            layer.geometry.add_polyline(
                [new Vec2(track.start[0], track.start[1]), new Vec2(track.end[0], track.end[1])],
                track.width, r, g, b, a,
            );
        }
        renderer.end_layer();
    }

    // Arc tracks
    if (model.arcs.length > 0) {
        const arcByLayer = new Map<string, typeof model.arcs>();
        for (const arc of model.arcs) {
            const ln = arc.layer ?? "F.Cu";
            let arr = arcByLayer.get(ln);
            if (!arr) { arr = []; arcByLayer.set(ln, arr); }
            arr.push(arc);
        }
        for (const [layerName, arcs] of arcByLayer) {
            const [r, g, b, a] = getLayerColor(layerName);
            const layer = renderer.start_layer(`arc_tracks:${layerName}`);
            for (const arc of arcs) {
                const pts = arcToPoints(arc.start, arc.mid, arc.end);
                layer.geometry.add_polyline(pts, arc.width, r, g, b, a);
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
        layer.geometry.add_circle(via.at[0], via.at[1], via.size / 2, vr, vg, vb, va);
        const [dr, dg, db, da] = VIA_DRILL_COLOR;
        layer.geometry.add_circle(via.at[0], via.at[1], via.drill / 2, dr, dg, db, da);
    }
    renderer.end_layer();
}

function paintFootprint(renderer: Renderer, fp: FootprintModel) {
    // Paint drawings (silkscreen, fab, courtyard lines)
    const drawingsByLayer = new Map<string, DrawingModel[]>();
    for (const drawing of fp.drawings) {
        const ln = drawing.layer ?? "F.SilkS";
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

    // Paint pads
    if (fp.pads.length > 0) {
        const layer = renderer.start_layer(`fp:${fp.uuid}:pads`);
        for (const pad of fp.pads) {
            paintPad(layer, fp.at, pad);
        }
        renderer.end_layer();
    }
}

function paintDrawing(layer: RenderLayer, fpAt: [number, number, number], drawing: DrawingModel, r: number, g: number, b: number, a: number) {
    const w = drawing.width || 0.12;

    if (drawing.type === "line" && drawing.start && drawing.end) {
        const p1 = fpTransform(fpAt, drawing.start[0], drawing.start[1]);
        const p2 = fpTransform(fpAt, drawing.end[0], drawing.end[1]);
        layer.geometry.add_polyline([p1, p2], w, r, g, b, a);
    } else if (drawing.type === "arc" && drawing.start && drawing.mid && drawing.end) {
        const localPts = arcToPoints(drawing.start, drawing.mid, drawing.end);
        const worldPts = localPts.map(p => fpTransform(fpAt, p.x, p.y));
        layer.geometry.add_polyline(worldPts, w, r, g, b, a);
    } else if (drawing.type === "circle" && drawing.center && drawing.end) {
        const cx = drawing.center[0], cy = drawing.center[1];
        const ex = drawing.end[0], ey = drawing.end[1];
        const rad = Math.sqrt((ex - cx) ** 2 + (ey - cy) ** 2);
        const pts: Vec2[] = [];
        const segs = 48;
        for (let i = 0; i <= segs; i++) {
            const angle = (i / segs) * 2 * Math.PI;
            pts.push(new Vec2(cx + rad * Math.cos(angle), cy + rad * Math.sin(angle)));
        }
        const worldPts = pts.map(p => fpTransform(fpAt, p.x, p.y));
        layer.geometry.add_polyline(worldPts, w, r, g, b, a);
    } else if (drawing.type === "rect" && drawing.start && drawing.end) {
        const [x1, y1] = drawing.start;
        const [x2, y2] = drawing.end;
        const corners = [
            fpTransform(fpAt, x1, y1),
            fpTransform(fpAt, x2, y1),
            fpTransform(fpAt, x2, y2),
            fpTransform(fpAt, x1, y2),
            fpTransform(fpAt, x1, y1),
        ];
        layer.geometry.add_polyline(corners, w, r, g, b, a);
    } else if (drawing.type === "polygon" && drawing.points) {
        const worldPts = drawing.points.map(([x, y]) => fpTransform(fpAt, x, y));
        // Close the polygon
        if (worldPts.length >= 3) {
            worldPts.push(worldPts[0]!.copy());
            layer.geometry.add_polyline(worldPts, w, r, g, b, a);
        }
    }
}

function paintPad(layer: RenderLayer, fpAt: [number, number, number], pad: PadModel) {
    const [cr, cg, cb, ca] = getPadColor(pad.layers);
    const hw = pad.size[0] / 2;
    const hh = pad.size[1] / 2;

    if (pad.shape === "circle") {
        const center = fpTransform(fpAt, pad.at[0], pad.at[1]);
        layer.geometry.add_circle(center.x, center.y, hw, cr, cg, cb, ca);
    } else if (pad.shape === "oval") {
        // Approximate oval as a thick line between the two focal points
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
        // rect, roundrect, trapezoid, custom → draw as filled polygon
        const corners = [
            padTransform(fpAt, pad.at, -hw, -hh),
            padTransform(fpAt, pad.at, hw, -hh),
            padTransform(fpAt, pad.at, hw, hh),
            padTransform(fpAt, pad.at, -hw, hh),
        ];
        layer.geometry.add_polygon(corners, cr, cg, cb, ca);
    }

    // Draw drill hole for through-hole pads
    if (pad.drill && pad.type === "thru_hole") {
        const center = fpTransform(fpAt, pad.at[0], pad.at[1]);
        const drillR = (pad.drill.size_x ?? pad.size[0] * 0.5) / 2;
        layer.geometry.add_circle(center.x, center.y, drillR, 0.15, 0.15, 0.15, 1.0);
    }
}

/** Paint a selection highlight around a footprint */
export function paintSelection(renderer: Renderer, fp: FootprintModel): RenderLayer {
    const layer = renderer.start_layer("selection");
    const [r, g, b, a] = SELECTION_COLOR;

    // Compute bounding box from pads and drawings
    const allPoints: Vec2[] = [];
    for (const pad of fp.pads) {
        const center = fpTransform(fp.at, pad.at[0], pad.at[1]);
        const hw = pad.size[0] / 2;
        const hh = pad.size[1] / 2;
        allPoints.push(center.add(new Vec2(-hw, -hh)));
        allPoints.push(center.add(new Vec2(hw, hh)));
    }
    for (const drawing of fp.drawings) {
        if (drawing.start) allPoints.push(fpTransform(fp.at, drawing.start[0], drawing.start[1]));
        if (drawing.end) allPoints.push(fpTransform(fp.at, drawing.end[0], drawing.end[1]));
        if (drawing.center) allPoints.push(fpTransform(fp.at, drawing.center[0], drawing.center[1]));
    }

    if (allPoints.length > 0) {
        const bbox = BBox.from_points(allPoints).grow(0.5);
        const corners = [
            new Vec2(bbox.x, bbox.y),
            new Vec2(bbox.x2, bbox.y),
            new Vec2(bbox.x2, bbox.y2),
            new Vec2(bbox.x, bbox.y2),
        ];
        layer.geometry.add_polygon(corners, r, g, b, a);
    }

    renderer.end_layer();
    return layer;
}

/** Compute a bounding box for the full render model */
export function computeBBox(model: RenderModel): BBox {
    const points: Vec2[] = [];

    for (const edge of model.board.edges) {
        if (edge.start) points.push(new Vec2(edge.start[0], edge.start[1]));
        if (edge.end) points.push(new Vec2(edge.end[0], edge.end[1]));
        if (edge.mid) points.push(new Vec2(edge.mid[0], edge.mid[1]));
        if (edge.center) points.push(new Vec2(edge.center[0], edge.center[1]));
    }
    for (const fp of model.footprints) {
        points.push(new Vec2(fp.at[0], fp.at[1]));
        for (const pad of fp.pads) {
            const center = fpTransform(fp.at, pad.at[0], pad.at[1]);
            points.push(center);
        }
    }
    for (const track of model.tracks) {
        points.push(new Vec2(track.start[0], track.start[1]));
        points.push(new Vec2(track.end[0], track.end[1]));
    }
    for (const via of model.vias) {
        points.push(new Vec2(via.at[0], via.at[1]));
    }

    if (points.length === 0) return new BBox(0, 0, 100, 100);
    return BBox.from_points(points).grow(5);
}
