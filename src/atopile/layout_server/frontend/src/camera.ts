import { Vec2, Matrix3, BBox } from "./math";

/** 2D camera with pan, zoom, and viewport management */
export class Camera2 {
    viewport_size: Vec2 = new Vec2(0, 0);
    center: Vec2 = new Vec2(0, 0);
    zoom: number = 1;

    get matrix(): Matrix3 {
        const mx = this.viewport_size.x / 2;
        const my = this.viewport_size.y / 2;
        const dx = this.center.x - this.center.x * this.zoom;
        const dy = this.center.y - this.center.y * this.zoom;
        const left = -(this.center.x - mx) + dx;
        const top = -(this.center.y - my) + dy;
        return Matrix3.identity()
            .translate_self(left, top)
            .scale_self(this.zoom, this.zoom);
    }

    get bbox(): BBox {
        const m = this.matrix.inverse();
        const start = m.transform(new Vec2(0, 0));
        const end = m.transform(new Vec2(this.viewport_size.x, this.viewport_size.y));
        return new BBox(start.x, start.y, end.x - start.x, end.y - start.y);
    }

    set bbox(bbox: BBox) {
        const zoom_w = this.viewport_size.x / bbox.w;
        const zoom_h = this.viewport_size.y / bbox.h;
        this.zoom = Math.min(zoom_w, zoom_h);
        this.center = bbox.center;
    }

    translate(delta: Vec2): void {
        this.center = this.center.add(delta);
    }

    screen_to_world(v: Vec2): Vec2 {
        return this.matrix.inverse().transform(v);
    }

    world_to_screen(v: Vec2): Vec2 {
        return this.matrix.transform(v);
    }
}
