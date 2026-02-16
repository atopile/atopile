import earcut from "earcut";
import { Vec2 } from "../math";

const VERTS_PER_QUAD = 6;

/** Convert quad corners to 2 triangles (6 vertices) */
function quad_to_triangles(a: Vec2, b: Vec2, c: Vec2, d: Vec2): number[] {
    return [a.x, a.y, c.x, c.y, b.x, b.y, b.x, b.y, c.x, c.y, d.x, d.y];
}

function fill_color(dest: Float32Array, r: number, g: number, b: number, a: number, offset: number, count: number) {
    for (let i = 0; i < count; i++) {
        dest[offset + i * 4] = r;
        dest[offset + i * 4 + 1] = g;
        dest[offset + i * 4 + 2] = b;
        dest[offset + i * 4 + 3] = a;
    }
}

export interface TessPolylineResult {
    positions: Float32Array;
    caps: Float32Array;
    colors: Float32Array;
    vertexCount: number;
}

/** Tessellate a polyline (array of points + width) into quads with round caps */
export function tessellate_polyline(
    points: Vec2[],
    width: number,
    r: number, g: number, b: number, a: number,
): TessPolylineResult {
    const segCount = points.length - 1;
    const maxVerts = segCount * VERTS_PER_QUAD;
    const positions = new Float32Array(maxVerts * 2);
    const caps = new Float32Array(maxVerts);
    const colors = new Float32Array(maxVerts * 4);
    let vi = 0;

    for (let i = 1; i < points.length; i++) {
        const p1 = points[i - 1]!;
        const p2 = points[i]!;
        const line = p2.sub(p1);
        const len = line.magnitude;
        if (len === 0) continue;

        const norm = line.normal.normalize();
        const n = norm.multiply(width / 2);
        const n2 = n.normal;

        const qa = p1.add(n).add(n2);
        const qb = p1.sub(n).add(n2);
        const qc = p2.add(n).sub(n2);
        const qd = p2.sub(n).sub(n2);

        const cap_region = width / (len + width);

        positions.set(quad_to_triangles(qa, qb, qc, qd), vi * 2);
        for (let j = 0; j < VERTS_PER_QUAD; j++) caps[vi + j] = cap_region;
        fill_color(colors, r, g, b, a, vi * 4, VERTS_PER_QUAD);
        vi += VERTS_PER_QUAD;
    }

    return {
        positions: positions.subarray(0, vi * 2),
        caps: caps.subarray(0, vi),
        colors: colors.subarray(0, vi * 4),
        vertexCount: vi,
    };
}

export interface TessCircleResult {
    positions: Float32Array;
    caps: Float32Array;
    colors: Float32Array;
    vertexCount: number;
}

/** Tessellate a filled circle into a quad (rendered as SDF in the polyline shader) */
export function tessellate_circle(
    cx: number, cy: number, radius: number,
    r: number, g: number, b: number, a: number,
): TessCircleResult {
    const positions = new Float32Array(VERTS_PER_QUAD * 2);
    const caps = new Float32Array(VERTS_PER_QUAD);
    const colors = new Float32Array(VERTS_PER_QUAD * 4);

    const n = new Vec2(radius, 0);
    const n2 = n.normal;
    const c = new Vec2(cx, cy);

    const qa = c.add(n).add(n2);
    const qb = c.sub(n).add(n2);
    const qc = c.add(n).sub(n2);
    const qd = c.sub(n).sub(n2);

    positions.set(quad_to_triangles(qa, qb, qc, qd), 0);
    for (let i = 0; i < VERTS_PER_QUAD; i++) caps[i] = 1.0;
    fill_color(colors, r, g, b, a, 0, VERTS_PER_QUAD);

    return { positions, caps, colors, vertexCount: VERTS_PER_QUAD };
}

export interface TessPolygonResult {
    positions: Float32Array;
    colors: Float32Array;
    vertexCount: number;
}

/** Triangulate a polygon using earcut */
export function triangulate_polygon(
    points: Vec2[],
    r: number, g: number, b: number, a: number,
): TessPolygonResult {
    const flat = new Array(points.length * 2);
    for (let i = 0; i < points.length; i++) {
        flat[i * 2] = points[i]!.x;
        flat[i * 2 + 1] = points[i]!.y;
    }

    const indices = earcut(flat);
    const positions = new Float32Array(indices.length * 2);
    for (let i = 0; i < indices.length; i++) {
        positions[i * 2] = flat[indices[i]! * 2]!;
        positions[i * 2 + 1] = flat[indices[i]! * 2 + 1]!;
    }

    const vertexCount = indices.length;
    const colors = new Float32Array(vertexCount * 4);
    fill_color(colors, r, g, b, a, 0, vertexCount);

    return { positions, colors, vertexCount };
}
