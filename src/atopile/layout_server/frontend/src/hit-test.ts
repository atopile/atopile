import { Vec2, BBox } from "./math";
import type { FootprintModel } from "./types";

const DEG_TO_RAD = Math.PI / 180;

function fpTransform(fpAt: [number, number, number], localX: number, localY: number): Vec2 {
    const rad = -(fpAt[2] || 0) * DEG_TO_RAD;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);
    return new Vec2(fpAt[0] + localX * cos - localY * sin, fpAt[1] + localX * sin + localY * cos);
}

/** Compute bounding box for a footprint in world coords */
export function footprintBBox(fp: FootprintModel): BBox {
    const points: Vec2[] = [];
    for (const pad of fp.pads) {
        const center = fpTransform(fp.at, pad.at[0], pad.at[1]);
        const hw = pad.size[0] / 2;
        const hh = pad.size[1] / 2;
        points.push(center.add(new Vec2(-hw, -hh)));
        points.push(center.add(new Vec2(hw, hh)));
    }
    for (const drawing of fp.drawings) {
        if (drawing.start) points.push(fpTransform(fp.at, drawing.start[0], drawing.start[1]));
        if (drawing.end) points.push(fpTransform(fp.at, drawing.end[0], drawing.end[1]));
        if (drawing.center) points.push(fpTransform(fp.at, drawing.center[0], drawing.center[1]));
        if (drawing.points) {
            for (const [x, y] of drawing.points) {
                points.push(fpTransform(fp.at, x, y));
            }
        }
    }
    if (points.length === 0) {
        return new BBox(fp.at[0] - 1, fp.at[1] - 1, 2, 2);
    }
    return BBox.from_points(points).grow(0.2);
}

/** Find the footprint under a world-space point, returns index or -1 */
export function hitTestFootprints(worldPos: Vec2, footprints: FootprintModel[]): number {
    // Search in reverse order (last painted = on top)
    for (let i = footprints.length - 1; i >= 0; i--) {
        const bbox = footprintBBox(footprints[i]!);
        if (bbox.contains_point(worldPos)) {
            return i;
        }
    }
    return -1;
}
