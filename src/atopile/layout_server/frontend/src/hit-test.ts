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

/** Find which pad within a footprint is under a world-space point, returns pad index or -1 */
export function hitTestPads(worldPos: Vec2, footprint: FootprintModel): number {
    const fpAt = footprint.at;
    // Transform worldPos into footprint-local coordinates
    const DEG_TO_RAD = Math.PI / 180;
    const rad = -(fpAt.r || 0) * DEG_TO_RAD;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);
    const dx = worldPos.x - fpAt.x;
    const dy = worldPos.y - fpAt.y;
    // Inverse rotation
    const localX = dx * cos + dy * sin;
    const localY = -dx * sin + dy * cos;

    for (let i = footprint.pads.length - 1; i >= 0; i--) {
        const pad = footprint.pads[i]!;
        // Transform into pad-local coordinates
        const padRad = -(pad.at.r || 0) * DEG_TO_RAD;
        const pc = Math.cos(padRad), ps = Math.sin(padRad);
        const pdx = localX - pad.at.x;
        const pdy = localY - pad.at.y;
        const plx = pdx * pc + pdy * ps;
        const ply = -pdx * ps + pdy * pc;

        const hw = pad.size.w / 2;
        const hh = pad.size.h / 2;

        if (pad.shape === "circle") {
            if (plx * plx + ply * ply <= hw * hw) return i;
        } else {
            // rect, roundrect, oval — bounding box test
            if (plx >= -hw && plx <= hw && ply >= -hh && ply <= hh) return i;
        }
    }
    return -1;
}
