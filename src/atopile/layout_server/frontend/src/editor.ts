import { Vec2 } from "./math";
import { Camera2 } from "./camera";
import { PanAndZoom } from "./pan-and-zoom";
import { Renderer } from "./webgl/renderer";
import { paintAll, paintSelection, computeBBox } from "./painter";
import { hitTestFootprints } from "./hit-test";
import type { RenderModel } from "./types";

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
    private dragStartFpPos: { x: number; y: number } | null = null;
    private needsRedraw = true;

    // Layer visibility
    private hiddenLayers: Set<string> = new Set();
    private onLayersChanged: (() => void) | null = null;

    // Track current mouse position
    private lastMouseScreen: Vec2 = new Vec2(0, 0);

    constructor(canvas: HTMLCanvasElement, baseUrl: string) {
        this.canvas = canvas;
        this.baseUrl = baseUrl;
        this.renderer = new Renderer(canvas);
        this.camera = new Camera2();
        this.panAndZoom = new PanAndZoom(canvas, this.camera, () => this.requestRedraw());

        this.setupMouseHandlers();
        this.setupKeyboardHandlers();
        this.setupResizeHandler();
        this.renderer.setup();
        this.startRenderLoop();
    }

    async init() {
        await this.fetchAndPaint();
        this.connectWebSocket();
    }

    private async fetchAndPaint() {
        const resp = await fetch(`${this.baseUrl}/api/render-model`);
        this.applyModel(await resp.json());
    }

    private applyModel(model: RenderModel) {
        this.model = model;
        this.paint();

        const bbox = computeBBox(this.model);
        this.camera.viewport_size = new Vec2(this.canvas.clientWidth, this.canvas.clientHeight);
        this.camera.bbox = bbox;
        this.requestRedraw();
    }

    private paint() {
        if (!this.model) return;
        paintAll(this.renderer, this.model, this.hiddenLayers);

        if (this.selectedFpIndex >= 0 && this.selectedFpIndex < this.model.footprints.length) {
            paintSelection(this.renderer, this.model.footprints[this.selectedFpIndex]!);
        }
    }

    private connectWebSocket() {
        const wsUrl = this.baseUrl.replace(/^http/, "ws") + "/ws";
        this.ws = new WebSocket(wsUrl);
        this.ws.onopen = () => console.log("WS connected");
        this.ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === "layout_updated" && msg.model) {
                this.applyModel(msg.model);
            }
        };
        this.ws.onerror = (err) => console.error("WS error:", err);
        this.ws.onclose = () => {
            setTimeout(() => this.connectWebSocket(), 2000);
        };
    }

    private setupMouseHandlers() {
        this.canvas.addEventListener("mousedown", (e: MouseEvent) => {
            if (e.button !== 0) return;

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
                this.dragStartFpPos = { x: fp.at.x, y: fp.at.y };
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
            const rect = this.canvas.getBoundingClientRect();
            this.lastMouseScreen = new Vec2(e.clientX - rect.left, e.clientY - rect.top);

            if (!this.isDragging || !this.model || this.selectedFpIndex < 0) return;

            const worldPos = this.camera.screen_to_world(this.lastMouseScreen);
            const delta = worldPos.sub(this.dragStartWorld!);
            const fp = this.model.footprints[this.selectedFpIndex]!;
            fp.at.x = this.dragStartFpPos!.x + delta.x;
            fp.at.y = this.dragStartFpPos!.y + delta.y;

            this.paint();
            this.requestRedraw();
        });

        this.canvas.addEventListener("mouseup", async (e: MouseEvent) => {
            if (e.button !== 0 || !this.isDragging) return;
            this.isDragging = false;

            if (!this.model || this.selectedFpIndex < 0 || !this.dragStartFpPos) return;
            const fp = this.model.footprints[this.selectedFpIndex]!;

            // Skip noop moves
            const dx = fp.at.x - this.dragStartFpPos.x;
            const dy = fp.at.y - this.dragStartFpPos.y;
            if (Math.abs(dx) < 0.001 && Math.abs(dy) < 0.001) return;

            await this.executeAction("move", {
                uuid: fp.uuid,
                x: fp.at.x,
                y: fp.at.y,
                r: fp.at.r || null,
            });
        });
    }

    private setupKeyboardHandlers() {
        window.addEventListener("keydown", async (e: KeyboardEvent) => {
            // R — rotate selected footprint by 90 degrees
            if (e.key === "r" || e.key === "R") {
                if (e.ctrlKey || e.metaKey || e.altKey) return;
                await this.actionOnSelected("rotate", (fp) => ({ uuid: fp.uuid, delta_degrees: 90 }));
                return;
            }

            // F — flip selected footprint
            if (e.key === "f" || e.key === "F") {
                if (e.ctrlKey || e.metaKey || e.altKey) return;
                await this.actionOnSelected("flip", (fp) => ({ uuid: fp.uuid }));
                return;
            }

            // Ctrl+Z — undo
            if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
                e.preventDefault();
                await this.serverAction("/api/undo");
                return;
            }

            // Ctrl+Shift+Z or Ctrl+Y — redo
            if (((e.ctrlKey || e.metaKey) && e.key === "z" && e.shiftKey) ||
                ((e.ctrlKey || e.metaKey) && e.key === "y")) {
                e.preventDefault();
                await this.serverAction("/api/redo");
                return;
            }
        });
    }

    private setupResizeHandler() {
        window.addEventListener("resize", () => {
            this.requestRedraw();
        });
    }

    private async actionOnSelected(
        type: string,
        detailsFn: (fp: RenderModel["footprints"][0]) => Record<string, unknown>,
    ) {
        if (!this.model || this.selectedFpIndex < 0) return;
        const fp = this.model.footprints[this.selectedFpIndex]!;
        await this.executeAction(type, detailsFn(fp));
    }

    private async executeAction(type: string, details: Record<string, unknown>) {
        try {
            await fetch(`${this.baseUrl}/api/execute-action`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ type, details }),
            });
        } catch (err) {
            console.error("Failed to execute action:", err);
        }
    }

    private async serverAction(endpoint: string) {
        try {
            await fetch(`${this.baseUrl}${endpoint}`, { method: "POST" });
        } catch (err) {
            console.error(`Failed ${endpoint}:`, err);
        }
    }

    // --- Layer visibility ---

    setLayerVisible(layer: string, visible: boolean) {
        if (visible) {
            this.hiddenLayers.delete(layer);
        } else {
            this.hiddenLayers.add(layer);
        }
        this.paint();
        this.requestRedraw();
    }

    isLayerVisible(layer: string): boolean {
        return !this.hiddenLayers.has(layer);
    }

    getLayers(): string[] {
        if (!this.model) return [];
        const layers = new Set<string>();
        for (const fp of this.model.footprints) {
            layers.add(fp.layer);
            for (const pad of fp.pads) {
                for (const l of pad.layers) layers.add(l);
            }
            for (const d of fp.drawings) {
                if (d.layer) layers.add(d.layer);
            }
        }
        for (const t of this.model.tracks) {
            if (t.layer) layers.add(t.layer);
        }
        for (const a of this.model.arcs) {
            if (a.layer) layers.add(a.layer);
        }
        for (const z of this.model.zones) {
            for (const fp of z.filled_polygons) layers.add(fp.layer);
        }
        layers.add("Edge.Cuts");
        layers.add("Vias");
        return [...layers].sort();
    }

    setOnLayersChanged(cb: () => void) {
        this.onLayersChanged = cb;
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
