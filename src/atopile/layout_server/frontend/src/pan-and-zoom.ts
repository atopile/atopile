import { Camera2 } from "./camera";
import { Vec2 } from "./math";

const zoom_speed = 0.005;
const pan_speed = 1;
const line_delta_multiplier = 8;
const page_delta_multiplier = 24;

export type PanAndZoomCallback = () => void;

/** Interactive pan and zoom attached to an HTML element */
export class PanAndZoom {
    private readonly onWheel: (e: WheelEvent) => void;
    private readonly onMouseDown: (e: MouseEvent) => void;
    private readonly onMouseMove: (e: MouseEvent) => void;
    private readonly onMouseUp: (e: MouseEvent) => void;
    private readonly onContextMenu: (e: Event) => void;
    private readonly onTouchStart: (e: TouchEvent) => void;
    private readonly onTouchMove: (e: TouchEvent) => void;
    private readonly onTouchEnd: () => void;

    constructor(
        public readonly target: HTMLElement,
        public camera: Camera2,
        public callback: PanAndZoomCallback,
        public min_zoom = 0.1,
        public max_zoom = 400,
    ) {
        let dragStart: Vec2 | null = null;
        let dragging = false;
        let touchStart: TouchList | null = null;
        let pinchDist: number | null = null;

        this.onWheel = (e) => this.#on_wheel(e);
        this.onMouseDown = (e: MouseEvent) => {
            if (e.button === 1 || e.button === 2) {
                e.preventDefault();
                dragging = true;
                dragStart = new Vec2(e.clientX, e.clientY);
            }
        };
        this.onMouseMove = (e: MouseEvent) => {
            if (dragging && dragStart) {
                const cur = new Vec2(e.clientX, e.clientY);
                const delta = cur.sub(dragStart);
                this.#handle_pan(-delta.x, -delta.y);
                dragStart = cur;
            }
        };
        this.onMouseUp = (e: MouseEvent) => {
            if (e.button === 1 || e.button === 2) {
                dragging = false;
                dragStart = null;
            }
        };
        this.onContextMenu = (e) => e.preventDefault();
        this.onTouchStart = (e: TouchEvent) => {
            if (e.touches.length === 2) {
                pinchDist = this.#touchDistance(e.touches);
            } else if (e.touches.length === 1) {
                touchStart = e.touches;
            }
        };
        this.onTouchMove = (e: TouchEvent) => {
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
        };
        this.onTouchEnd = () => {
            pinchDist = null;
            touchStart = null;
        };

        this.target.addEventListener("wheel", this.onWheel, { passive: false });
        this.target.addEventListener("mousedown", this.onMouseDown);
        this.target.addEventListener("mousemove", this.onMouseMove);
        window.addEventListener("mouseup", this.onMouseUp);
        this.target.addEventListener("contextmenu", this.onContextMenu);
        this.target.addEventListener("touchstart", this.onTouchStart);
        this.target.addEventListener("touchmove", this.onTouchMove);
        this.target.addEventListener("touchend", this.onTouchEnd);
    }

    dispose() {
        this.target.removeEventListener("wheel", this.onWheel);
        this.target.removeEventListener("mousedown", this.onMouseDown);
        this.target.removeEventListener("mousemove", this.onMouseMove);
        window.removeEventListener("mouseup", this.onMouseUp);
        this.target.removeEventListener("contextmenu", this.onContextMenu);
        this.target.removeEventListener("touchstart", this.onTouchStart);
        this.target.removeEventListener("touchmove", this.onTouchMove);
        this.target.removeEventListener("touchend", this.onTouchEnd);
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
        // Capture world position under cursor BEFORE zoom change
        const worldBefore = mouse ? this.camera.screen_to_world(mouse) : null;

        this.camera.zoom *= Math.exp(delta * -zoom_speed);
        this.camera.zoom = Math.min(this.max_zoom, Math.max(this.camera.zoom, this.min_zoom));

        // Adjust center so the world point under cursor stays fixed
        if (worldBefore && mouse) {
            const worldAfter = this.camera.screen_to_world(mouse);
            this.camera.translate(worldBefore.sub(worldAfter));
        }

        this.callback();
    }
}
