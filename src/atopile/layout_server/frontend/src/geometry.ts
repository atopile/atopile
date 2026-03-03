import { Vec2 } from "./math";
import type { Point3 } from "./types";

const DEG_TO_RAD = Math.PI / 180;

/** Transform a local point by a footprint's position + rotation. */
export function fpTransform(fpAt: Point3, localX: number, localY: number): Vec2 {
    const rad = -(fpAt.r || 0) * DEG_TO_RAD;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);
    return new Vec2(
        fpAt.x + localX * cos - localY * sin,
        fpAt.y + localX * sin + localY * cos,
    );
}

/** Transform by pad rotation, then footprint rotation. */
export function padTransform(fpAt: Point3, padAt: Point3, localX: number, localY: number): Vec2 {
    const padRad = -(padAt.r || 0) * DEG_TO_RAD;
    const cos = Math.cos(padRad);
    const sin = Math.sin(padRad);
    const px = localX * cos - localY * sin;
    const py = localX * sin + localY * cos;
    return fpTransform(fpAt, padAt.x + px, padAt.y + py);
}

/** Axis-aligned extents of a rotated width/height rectangle. */
export function rotatedRectExtents(width: number, height: number, rotationDeg: number): [number, number] {
    const theta = -(rotationDeg || 0) * DEG_TO_RAD;
    const absCos = Math.abs(Math.cos(theta));
    const absSin = Math.abs(Math.sin(theta));
    return [
        width * absCos + height * absSin,
        width * absSin + height * absCos,
    ];
}
