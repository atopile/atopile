/** 2D vector */
export class Vec2 {
    x: number;
    y: number;

    constructor(x: number = 0, y: number = 0) {
        this.x = x;
        this.y = y;
    }

    copy(): Vec2 {
        return new Vec2(this.x, this.y);
    }

    *[Symbol.iterator]() {
        yield this.x;
        yield this.y;
    }

    get magnitude(): number {
        return Math.sqrt(this.x ** 2 + this.y ** 2);
    }

    get normal(): Vec2 {
        return new Vec2(-this.y, this.x);
    }

    normalize(): Vec2 {
        const l = this.magnitude;
        if (l === 0) return new Vec2(0, 0);
        return new Vec2(this.x / l, this.y / l);
    }

    add(b: Vec2): Vec2 {
        return new Vec2(this.x + b.x, this.y + b.y);
    }

    sub(b: Vec2): Vec2 {
        return new Vec2(this.x - b.x, this.y - b.y);
    }

    multiply(s: number): Vec2 {
        return new Vec2(this.x * s, this.y * s);
    }
}

type ElementArray = [number, number, number, number, number, number, number, number, number];

/** 3x3 transformation matrix (column-major) */
export class Matrix3 {
    elements: Float32Array;

    constructor(elements: ElementArray | Float32Array) {
        this.elements = new Float32Array(elements);
    }

    static identity(): Matrix3 {
        return new Matrix3([1, 0, 0, 0, 1, 0, 0, 0, 1]);
    }

    static orthographic(width: number, height: number): Matrix3 {
        return new Matrix3([2 / width, 0, 0, 0, -2 / height, 0, -1, 1, 1]);
    }

    static translation(x: number, y: number): Matrix3 {
        return new Matrix3([1, 0, 0, 0, 1, 0, x, y, 1]);
    }

    static scaling(x: number, y: number): Matrix3 {
        return new Matrix3([x, 0, 0, 0, y, 0, 0, 0, 1]);
    }

    static rotation(radians: number): Matrix3 {
        const c = Math.cos(radians);
        const s = Math.sin(radians);
        return new Matrix3([c, -s, 0, s, c, 0, 0, 0, 1]);
    }

    copy(): Matrix3 {
        return new Matrix3(this.elements);
    }

    transform(vec: Vec2): Vec2 {
        const e = this.elements;
        const x = vec.x * e[0]! + vec.y * e[3]! + e[6]!;
        const y = vec.x * e[1]! + vec.y * e[4]! + e[7]!;
        return new Vec2(x, y);
    }

    multiply_self(b: Matrix3): Matrix3 {
        const a = this.elements;
        const be = b.elements;
        const a00 = a[0]!, a01 = a[1]!, a02 = a[2]!;
        const a10 = a[3]!, a11 = a[4]!, a12 = a[5]!;
        const a20 = a[6]!, a21 = a[7]!, a22 = a[8]!;
        const b00 = be[0]!, b01 = be[1]!, b02 = be[2]!;
        const b10 = be[3]!, b11 = be[4]!, b12 = be[5]!;
        const b20 = be[6]!, b21 = be[7]!, b22 = be[8]!;

        a[0] = b00 * a00 + b01 * a10 + b02 * a20;
        a[1] = b00 * a01 + b01 * a11 + b02 * a21;
        a[2] = b00 * a02 + b01 * a12 + b02 * a22;
        a[3] = b10 * a00 + b11 * a10 + b12 * a20;
        a[4] = b10 * a01 + b11 * a11 + b12 * a21;
        a[5] = b10 * a02 + b11 * a12 + b12 * a22;
        a[6] = b20 * a00 + b21 * a10 + b22 * a20;
        a[7] = b20 * a01 + b21 * a11 + b22 * a21;
        a[8] = b20 * a02 + b21 * a12 + b22 * a22;
        return this;
    }

    multiply(b: Matrix3): Matrix3 {
        return this.copy().multiply_self(b);
    }

    translate_self(x: number, y: number): Matrix3 {
        return this.multiply_self(Matrix3.translation(x, y));
    }

    scale_self(x: number, y: number): Matrix3 {
        return this.multiply_self(Matrix3.scaling(x, y));
    }

    inverse(): Matrix3 {
        const e = this.elements;
        const a00 = e[0]!, a01 = e[1]!, a02 = e[2]!;
        const a10 = e[3]!, a11 = e[4]!, a12 = e[5]!;
        const a20 = e[6]!, a21 = e[7]!, a22 = e[8]!;

        const b01 = a22 * a11 - a12 * a21;
        const b11 = -a22 * a10 + a12 * a20;
        const b21 = a21 * a10 - a11 * a20;

        const det = a00 * b01 + a01 * b11 + a02 * b21;
        const inv = 1.0 / det;

        return new Matrix3([
            b01 * inv,
            (-a22 * a01 + a02 * a21) * inv,
            (a12 * a01 - a02 * a11) * inv,
            b11 * inv,
            (a22 * a00 - a02 * a20) * inv,
            (-a12 * a00 + a02 * a10) * inv,
            b21 * inv,
            (-a21 * a00 + a01 * a20) * inv,
            (a11 * a00 - a01 * a10) * inv,
        ]);
    }
}

/** Axis-aligned bounding box */
export class BBox {
    constructor(
        public x: number = 0,
        public y: number = 0,
        public w: number = 0,
        public h: number = 0,
    ) {
        if (this.w < 0) { this.w *= -1; this.x -= this.w; }
        if (this.h < 0) { this.h *= -1; this.y -= this.h; }
    }

    get x2(): number { return this.x + this.w; }
    get y2(): number { return this.y + this.h; }
    get center(): Vec2 { return new Vec2(this.x + this.w / 2, this.y + this.h / 2); }

    static from_points(points: Vec2[]): BBox {
        if (points.length === 0) return new BBox();
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (const p of points) {
            if (p.x < minX) minX = p.x;
            if (p.y < minY) minY = p.y;
            if (p.x > maxX) maxX = p.x;
            if (p.y > maxY) maxY = p.y;
        }
        return new BBox(minX, minY, maxX - minX, maxY - minY);
    }

    static combine(boxes: BBox[]): BBox {
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (const b of boxes) {
            if (b.w === 0 && b.h === 0) continue;
            if (b.x < minX) minX = b.x;
            if (b.y < minY) minY = b.y;
            if (b.x2 > maxX) maxX = b.x2;
            if (b.y2 > maxY) maxY = b.y2;
        }
        if (minX === Infinity) return new BBox();
        return new BBox(minX, minY, maxX - minX, maxY - minY);
    }

    contains_point(v: Vec2): boolean {
        return v.x >= this.x && v.x <= this.x2 && v.y >= this.y && v.y <= this.y2;
    }

    grow(d: number): BBox {
        return new BBox(this.x - d, this.y - d, this.w + d * 2, this.h + d * 2);
    }
}
