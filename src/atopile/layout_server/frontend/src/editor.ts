import { Vec2 } from "./math";
import { Camera2 } from "./camera";
import { PanAndZoom } from "./pan-and-zoom";
import { Renderer } from "./webgl/renderer";
import { paintAll, paintSelection, computeBBox } from "./painter";
import { hitTestFootprints } from "./hit-test";
import type { RenderModel, FootprintModel } from "./types";

export class Editor {
    private canvas: HTMLCanvasElement;
    private renderer: Renderer;
    private camera: Camera2;
    private panAndZoom: PanAndZoom;
    private model: RenderModel | null = null;
    private baseUrl: string;
    private ws: WebSocket | null = null;

    // Selection & drag state
    private selectedFpIndex = -1;
    private isDragging = false;
    private dragStartWorld: Vec2 | null = null;
    private dragStartFpPos: [number, number] | null = null;
    private needsRedraw = true;

    constructor(canvas: HTMLCanvasElement, baseUrl: string) {
        this.canvas = canvas;
        this.baseUrl = baseUrl;
        this.renderer = new Renderer(canvas);
        this.camera = new Camera2();
        this.panAndZoom = new PanAndZoom(canvas, this.camera, () => this.requestRedraw());

        this.setupMouseHandlers();
        this.renderer.setup();
        this.startRenderLoop();
    }

    async init() {
        await this.fetchAndPaint();
        this.connectWebSocket();
    }

    private async fetchAndPaint() {
        const resp = await fetch(`${this.baseUrl}/api/render-model`);
        this.model = await resp.json();
        this.paint();

        // Fit view to board
        const bbox = computeBBox(this.model!);
        this.camera.viewport_size = new Vec2(this.canvas.clientWidth, this.canvas.clientHeight);
        this.camera.bbox = bbox;
        this.requestRedraw();
    }

    private paint() {
        if (!this.model) return;
        paintAll(this.renderer, this.model);

        // Re-add selection if any
        if (this.selectedFpIndex >= 0 && this.selectedFpIndex < this.model.footprints.length) {
            paintSelection(this.renderer, this.model.footprints[this.selectedFpIndex]!);
        }
    }

    private connectWebSocket() {
        const wsUrl = this.baseUrl.replace(/^http/, "ws") + "/ws";
        this.ws = new WebSocket(wsUrl);
        this.ws.onmessage = async (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === "layout_updated") {
                await this.fetchAndPaint();
            }
        };
        this.ws.onclose = () => {
            // Reconnect after delay
            setTimeout(() => this.connectWebSocket(), 2000);
        };
    }

    private setupMouseHandlers() {
        this.canvas.addEventListener("mousedown", (e: MouseEvent) => {
            if (e.button !== 0) return; // Only left click

            const rect = this.canvas.getBoundingClientRect();
            const screenPos = new Vec2(e.clientX - rect.left, e.clientY - rect.top);
            const worldPos = this.camera.screen_to_world(screenPos);

            if (!this.model) return;

            const hitIdx = hitTestFootprints(worldPos, this.model.footprints);

            if (hitIdx >= 0) {
                this.selectedFpIndex = hitIdx;
                const fp = this.model.footprints[hitIdx]!;
                this.isDragging = true;
                this.dragStartWorld = worldPos;
                this.dragStartFpPos = [fp.at[0], fp.at[1]];
                this.repaintWithSelection();
            } else {
                if (this.selectedFpIndex >= 0) {
                    this.selectedFpIndex = -1;
                    this.paint();
                    this.requestRedraw();
                }
            }
        });

        this.canvas.addEventListener("mousemove", (e: MouseEvent) => {
            if (!this.isDragging || !this.model || this.selectedFpIndex < 0) return;

            const rect = this.canvas.getBoundingClientRect();
            const screenPos = new Vec2(e.clientX - rect.left, e.clientY - rect.top);
            const worldPos = this.camera.screen_to_world(screenPos);

            const delta = worldPos.sub(this.dragStartWorld!);
            const fp = this.model.footprints[this.selectedFpIndex]!;
            fp.at[0] = this.dragStartFpPos![0] + delta.x;
            fp.at[1] = this.dragStartFpPos![1] + delta.y;

            this.paint();
            this.requestRedraw();
        });

        this.canvas.addEventListener("mouseup", async (e: MouseEvent) => {
            if (e.button !== 0 || !this.isDragging) return;
            this.isDragging = false;

            if (!this.model || this.selectedFpIndex < 0) return;
            const fp = this.model.footprints[this.selectedFpIndex]!;

            // Send move to server
            try {
                await fetch(`${this.baseUrl}/api/move-footprint`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        uuid: fp.uuid,
                        x: fp.at[0],
                        y: fp.at[1],
                        r: fp.at[2] || null,
                    }),
                });
            } catch (err) {
                console.error("Failed to save footprint position:", err);
            }
        });
    }

    private repaintWithSelection() {
        this.paint();
        this.requestRedraw();
    }

    private requestRedraw() {
        this.needsRedraw = true;
    }

    private startRenderLoop() {
        const loop = () => {
            if (this.needsRedraw) {
                this.needsRedraw = false;
                this.camera.viewport_size = new Vec2(this.canvas.clientWidth, this.canvas.clientHeight);
                this.renderer.draw(this.camera.matrix);
            }
            requestAnimationFrame(loop);
        };
        requestAnimationFrame(loop);
    }
}
