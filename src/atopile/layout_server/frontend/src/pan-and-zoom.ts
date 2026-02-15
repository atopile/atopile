import { Camera2 } from "./camera";
import { Vec2 } from "./math";

const zoom_speed = 0.005;
const pan_speed = 1;
const line_delta_multiplier = 8;
const page_delta_multiplier = 24;

export type PanAndZoomCallback = () => void;

/** Interactive pan and zoom attached to an HTML element */
export class PanAndZoom {
    constructor(
        public readonly target: HTMLElement,
        public camera: Camera2,
        public callback: PanAndZoomCallback,
        public min_zoom = 0.1,
        public max_zoom = 100,
    ) {
        this.target.addEventListener("wheel", (e) => this.#on_wheel(e), { passive: false });

        let dragStart: Vec2 | null = null;
        let dragging = false;

        this.target.addEventListener("mousedown", (e: MouseEvent) => {
            if (e.button === 1 || e.button === 2) {
                e.preventDefault();
                dragging = true;
                dragStart = new Vec2(e.clientX, e.clientY);
            }
        });

        this.target.addEventListener("mousemove", (e: MouseEvent) => {
            if (dragging && dragStart) {
                const cur = new Vec2(e.clientX, e.clientY);
                const delta = cur.sub(dragStart);
                this.#handle_pan(-delta.x, -delta.y);
                dragStart = cur;
            }
        });

        this.target.addEventListener("mouseup", (e: MouseEvent) => {
            if (e.button === 1 || e.button === 2) {
                dragging = false;
                dragStart = null;
            }
        });

        this.target.addEventListener("contextmenu", (e) => e.preventDefault());

        // Touch support
        let touchStart: TouchList | null = null;
        let pinchDist: number | null = null;

        this.target.addEventListener("touchstart", (e: TouchEvent) => {
            if (e.touches.length === 2) {
                pinchDist = this.#touchDistance(e.touches);
            } else if (e.touches.length === 1) {
                touchStart = e.touches;
            }
        });

        this.target.addEventListener("touchmove", (e: TouchEvent) => {
            if (e.touches.length === 2 && pinchDist !== null) {
                const cur = this.#touchDistance(e.touches);
                const scale = (cur / pinchDist) * 4;
                this.#handle_zoom(pinchDist < cur ? -scale : scale);
                pinchDist = cur;
            } else if (e.touches.length === 1 && touchStart !== null) {
                const sx = touchStart[0]!.clientX, sy = touchStart[0]!.clientY;
                const ex = e.touches[0]!.clientX, ey = e.touches[0]!.clientY;
                this.#handle_pan(sx - ex, sy - ey);
                touchStart = e.touches;
            }
        });

        this.target.addEventListener("touchend", () => {
            pinchDist = null;
            touchStart = null;
        });
    }

    #touchDistance(touches: TouchList): number {
        const dx = touches[0]!.clientX - touches[1]!.clientX;
        const dy = touches[0]!.clientY - touches[1]!.clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    #on_wheel(e: WheelEvent): void {
        e.preventDefault();
        let dy = e.deltaY;
        if (e.deltaMode === WheelEvent.DOM_DELTA_LINE) dy *= line_delta_multiplier;
        else if (e.deltaMode === WheelEvent.DOM_DELTA_PAGE) dy *= page_delta_multiplier;
        dy = Math.sign(dy) * Math.min(page_delta_multiplier, Math.abs(dy));

        if (e.ctrlKey || e.shiftKey) {
            let dx = e.deltaX;
            if (e.deltaMode === WheelEvent.DOM_DELTA_LINE) dx *= line_delta_multiplier;
            dx = Math.sign(dx) * Math.min(page_delta_multiplier, Math.abs(dx));
            this.#handle_pan(dx, dy);
        } else {
            const rect = this.target.getBoundingClientRect();
            const mouse = new Vec2(e.clientX - rect.left, e.clientY - rect.top);
            this.#handle_zoom(dy, mouse);
        }
    }

    #handle_pan(dx: number, dy: number): void {
        const delta = new Vec2(dx * pan_speed, dy * pan_speed).multiply(1 / this.camera.zoom);
        this.camera.translate(delta);
        this.callback();
    }

    #handle_zoom(delta: number, mouse?: Vec2): void {
        const oldZoom = this.camera.zoom;
        this.camera.zoom *= Math.exp(delta * -zoom_speed);
        this.camera.zoom = Math.min(this.max_zoom, Math.max(this.camera.zoom, this.min_zoom));

        // Zoom toward mouse position
        if (mouse) {
            const worldBefore = this.camera.screen_to_world(mouse);
            // Zoom already changed, so screen_to_world gives new position
            const worldAfter = this.camera.screen_to_world(mouse);
            const correction = worldBefore.sub(worldAfter);
            this.camera.translate(correction);
        }

        this.callback();
    }
}
