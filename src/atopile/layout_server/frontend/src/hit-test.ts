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

/** Compute bounding box for a footprint in world coords */
export function footprintBBox(fp: FootprintModel): BBox {
    const points: Vec2[] = [];
    for (const pad of fp.pads) {
        const center = fpTransform(fp.at, pad.at.x, pad.at.y);
        const hw = pad.size.w / 2;
        const hh = pad.size.h / 2;
        points.push(center.add(new Vec2(-hw, -hh)));
        points.push(center.add(new Vec2(hw, hh)));
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
