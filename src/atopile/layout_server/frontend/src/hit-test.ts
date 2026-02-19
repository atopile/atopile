import { Vec2, BBox } from "./math";
import type { FootprintModel, Point3 } from "./types";

const DEG_TO_RAD = Math.PI / 180;

function fpTransform(fpAt: Point3, localX: number, localY: number): Vec2 {
    const rad = -(fpAt.r || 0) * DEG_TO_RAD;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);
    return new Vec2(
        fpAt.x + localX * cos - localY * sin,
        fpAt.y + localX * sin + localY * cos,
    );
}

function padTransform(fpAt: Point3, padAt: Point3, lx: number, ly: number): Vec2 {
    const padRad = -(padAt.r || 0) * DEG_TO_RAD;
    const pc = Math.cos(padRad), ps = Math.sin(padRad);
    const px = lx * pc - ly * ps;
    const py = lx * ps + ly * pc;
    return fpTransform(fpAt, padAt.x + px, padAt.y + py);
}

/** Compute bounding box for a footprint in world coords */
export function footprintBBox(fp: FootprintModel): BBox {
    const points: Vec2[] = [];
    for (const pad of fp.pads) {
        const hw = pad.size.w / 2;
        const hh = pad.size.h / 2;
        // Transform all four corners through pad + footprint rotation
        points.push(padTransform(fp.at, pad.at, -hw, -hh));
        points.push(padTransform(fp.at, pad.at, hw, -hh));
        points.push(padTransform(fp.at, pad.at, hw, hh));
        points.push(padTransform(fp.at, pad.at, -hw, hh));
    }
    for (const drawing of fp.drawings) {
        if (drawing.start) points.push(fpTransform(fp.at, drawing.start.x, drawing.start.y));
        if (drawing.end) points.push(fpTransform(fp.at, drawing.end.x, drawing.end.y));
        if (drawing.center) points.push(fpTransform(fp.at, drawing.center.x, drawing.center.y));
        if (drawing.points) {
            for (const p of drawing.points) {
                points.push(fpTransform(fp.at, p.x, p.y));
            }
        }
    }
    if (points.length === 0) {
        return new BBox(fp.at.x - 1, fp.at.y - 1, 2, 2);
    }
    return BBox.from_points(points).grow(0.2);
}

/** Find the footprint under a world-space point, returns index or -1 */
export function hitTestFootprints(worldPos: Vec2, footprints: FootprintModel[]): number {
    for (let i = footprints.length - 1; i >= 0; i--) {
        const bbox = footprintBBox(footprints[i]!);
        if (bbox.contains_point(worldPos)) {
            return i;
        }
    }
    return -1;
}

function bboxIntersects(a: BBox, b: BBox): boolean {
    return !(a.x2 < b.x || b.x2 < a.x || a.y2 < b.y || b.y2 < a.y);
}

/** Find all footprints intersecting a world-space selection box. */
export function hitTestFootprintsInBox(selectionBox: BBox, footprints: FootprintModel[]): number[] {
    const hits: number[] = [];
    for (let i = 0; i < footprints.length; i++) {
        const bbox = footprintBBox(footprints[i]!);
        if (bboxIntersects(selectionBox, bbox)) {
            hits.push(i);
        }
    }
    return hits;
}
