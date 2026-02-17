import { Vec2 } from "./math";
import { Camera2 } from "./camera";
import { PanAndZoom } from "./pan-and-zoom";
import { Renderer } from "./webgl/renderer";
import { paintAll, paintSelection, computeBBox } from "./painter";
import { hitTestFootprints } from "./hit-test";
import { getLayerColor } from "./colors";
import type { RenderModel } from "./types";

const DEG_TO_RAD = Math.PI / 180;

export class Editor {
    private canvas: HTMLCanvasElement;
    private textOverlay: HTMLCanvasElement;
    private textCtx: CanvasRenderingContext2D | null;
    private renderer: Renderer;
    private camera: Camera2;
    private panAndZoom: PanAndZoom;
    private model: RenderModel | null = null;
    private baseUrl: string;
    private apiPrefix: string;
    private wsPath: string;
    private ws: WebSocket | null = null;

    // Selection & drag state
    private selectedFpIndex = -1;
    private isDragging = false;
    private dragStartWorld: Vec2 | null = null;
    private dragStartFpPos: { x: number; y: number } | null = null;
    private needsRedraw = true;

    // Layer visibility
    private hiddenLayers: Set<string> = new Set();
    private defaultLayerVisibilityInitialized = false;
    private onLayersChanged: (() => void) | null = null;

    // Track current mouse position
    private lastMouseScreen: Vec2 = new Vec2(0, 0);

    // Mouse coordinate callback
    private onMouseMoveCallback: ((x: number, y: number) => void) | null = null;

    constructor(canvas: HTMLCanvasElement, baseUrl: string, apiPrefix = "/api", wsPath = "/ws") {
        this.canvas = canvas;
        this.textOverlay = this.createTextOverlay();
        this.textCtx = this.textOverlay.getContext("2d");
        this.baseUrl = baseUrl;
        this.apiPrefix = apiPrefix;
        this.wsPath = wsPath;
        this.renderer = new Renderer(canvas);
        this.camera = new Camera2();
        this.panAndZoom = new PanAndZoom(canvas, this.camera, () => this.requestRedraw());

        this.setupMouseHandlers();
        this.setupKeyboardHandlers();
        this.setupResizeHandler();
        this.renderer.setup();
        this.startRenderLoop();
    }

    private createTextOverlay(): HTMLCanvasElement {
        const existing = document.getElementById("editor-text-overlay");
        if (existing instanceof HTMLCanvasElement) {
            return existing;
        }

        const overlay = document.createElement("canvas");
        overlay.id = "editor-text-overlay";
        overlay.style.position = "fixed";
        overlay.style.top = "0";
        overlay.style.left = "0";
        overlay.style.width = "100vw";
        overlay.style.height = "100vh";
        overlay.style.pointerEvents = "none";
        overlay.style.zIndex = "9";
        document.body.appendChild(overlay);
        return overlay;
    }

    async init() {
        await this.fetchAndPaint();
        this.connectWebSocket();
    }

    private async fetchAndPaint() {
        const resp = await fetch(`${this.baseUrl}${this.apiPrefix}/render-model`);
        this.applyModel(await resp.json(), true);
    }

    private applyModel(model: RenderModel, fitToView = false) {
        this.model = model;
        this.applyDefaultLayerVisibility();
        this.paint();

        this.camera.viewport_size = new Vec2(this.canvas.clientWidth, this.canvas.clientHeight);
        if (fitToView) {
            this.camera.bbox = computeBBox(this.model);
        }
        this.requestRedraw();
        if (this.onLayersChanged) this.onLayersChanged();
    }

    private applyDefaultLayerVisibility() {
        if (!this.model || this.defaultLayerVisibilityInitialized) return;
        this.defaultLayerVisibilityInitialized = true;
        for (const layerName of this.getLayers()) {
            if (layerName.endsWith(".Fab")) {
                this.hiddenLayers.add(layerName);
            }
        }
    }

    private paint() {
        if (!this.model) return;
        paintAll(this.renderer, this.model, this.hiddenLayers);

        if (this.selectedFpIndex >= 0 && this.selectedFpIndex < this.model.footprints.length) {
            paintSelection(this.renderer, this.model.footprints[this.selectedFpIndex]!);
        }
    }

    private connectWebSocket() {
        const wsUrl = this.baseUrl.replace(/^http/, "ws") + this.wsPath;
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

            if (this.onMouseMoveCallback) {
                const worldPos = this.camera.screen_to_world(this.lastMouseScreen);
                this.onMouseMoveCallback(worldPos.x, worldPos.y);
            }

            if (!this.isDragging || !this.model || this.selectedFpIndex < 0) return;

            const worldPos = this.camera.screen_to_world(this.lastMouseScreen);
            const delta = worldPos.sub(this.dragStartWorld!);
            const fp = this.model.footprints[this.selectedFpIndex]!;
            fp.at.x = this.dragStartFpPos!.x + delta.x;
            fp.at.y = this.dragStartFpPos!.y + delta.y;

            this.paint();
            this.requestRedraw();
        });

        window.addEventListener("mouseup", async (e: MouseEvent) => {
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
                await this.serverAction("/undo");
                return;
            }

            // Ctrl+Shift+Z or Ctrl+Y — redo
            if (((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z" && e.shiftKey) ||
                ((e.ctrlKey || e.metaKey) && e.key === "y")) {
                e.preventDefault();
                await this.serverAction("/redo");
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
            const resp = await fetch(`${this.baseUrl}${this.apiPrefix}/execute-action`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ type, details }),
            });
            const data = await resp.json();
            if (data.model) this.applyModel(data.model);
        } catch (err) {
            console.error("Failed to execute action:", err);
        }
    }

    private async serverAction(path: string) {
        try {
            const resp = await fetch(`${this.baseUrl}${this.apiPrefix}${path}`, { method: "POST" });
            const data = await resp.json();
            if (data.model) this.applyModel(data.model);
        } catch (err) {
            console.error(`Failed ${path}:`, err);
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

    setLayersVisible(layers: string[], visible: boolean) {
        for (const layer of layers) {
            if (visible) {
                this.hiddenLayers.delete(layer);
            } else {
                this.hiddenLayers.add(layer);
            }
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
            for (const t of fp.texts) {
                if (t.layer) layers.add(t.layer);
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
        // Filter out wildcard layers (*.Cu, F&B.Cu, etc.)
        for (const l of layers) {
            if (l.includes("*") || l.includes("&")) layers.delete(l);
        }
        return [...layers].sort();
    }

    setOnLayersChanged(cb: () => void) {
        this.onLayersChanged = cb;
    }

    setOnMouseMove(cb: (x: number, y: number) => void) {
        this.onMouseMoveCallback = cb;
    }

    private repaintWithSelection() {
        this.paint();
        this.requestRedraw();
    }

    private requestRedraw() {
        this.needsRedraw = true;
    }

    private drawTextOverlay() {
        if (!this.textCtx) return;

        const width = this.canvas.clientWidth;
        const height = this.canvas.clientHeight;
        const dpr = window.devicePixelRatio || 1;
        const pixelWidth = Math.max(1, Math.round(width * dpr));
        const pixelHeight = Math.max(1, Math.round(height * dpr));
        if (
            this.textOverlay.width !== pixelWidth
            || this.textOverlay.height !== pixelHeight
        ) {
            this.textOverlay.width = pixelWidth;
            this.textOverlay.height = pixelHeight;
        }

        this.textCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
        this.textCtx.clearRect(0, 0, width, height);
        if (!this.model || this.camera.zoom < 0.2) return;

        this.textCtx.textAlign = "center";
        this.textCtx.textBaseline = "middle";
        for (const fp of this.model.footprints) {
            for (const text of fp.texts) {
                if (text.hide || !text.text.trim()) continue;
                const layerName = text.layer ?? fp.layer;
                if (this.hiddenLayers.has(layerName)) continue;

                const worldPos = this.transformFootprintPoint(fp.at, text.at.x, text.at.y);
                const screenPos = this.camera.world_to_screen(worldPos);
                if (
                    screenPos.x < -200 || screenPos.x > width + 200
                    || screenPos.y < -50 || screenPos.y > height + 50
                ) {
                    continue;
                }

                const textHeight = text.size?.h ?? 1;
                const screenFontSize = textHeight * this.camera.zoom;
                if (screenFontSize < 2) continue;
                const fontPx = Math.max(8, Math.min(screenFontSize, 64));

                const [r, g, b, a] = getLayerColor(layerName);
                const rotation = -((fp.at.r || 0) + (text.at.r || 0)) * DEG_TO_RAD;
                this.textCtx.save();
                this.textCtx.translate(screenPos.x, screenPos.y);
                this.textCtx.rotate(rotation);
                this.textCtx.font = `${fontPx}px monospace`;
                this.textCtx.fillStyle = `rgba(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)}, ${Math.max(a, 0.55)})`;
                this.textCtx.fillText(text.text, 0, 0);
                this.textCtx.restore();
            }
        }
    }

    private transformFootprintPoint(
        fpAt: { x: number; y: number; r: number },
        localX: number,
        localY: number,
    ): Vec2 {
        const rad = -(fpAt.r || 0) * DEG_TO_RAD;
        const cos = Math.cos(rad);
        const sin = Math.sin(rad);
        return new Vec2(
            fpAt.x + localX * cos - localY * sin,
            fpAt.y + localX * sin + localY * cos,
        );
    }

    private startRenderLoop() {
        const loop = () => {
            if (this.needsRedraw) {
                this.needsRedraw = false;
                this.camera.viewport_size = new Vec2(this.canvas.clientWidth, this.canvas.clientHeight);
                this.renderer.updateGrid(this.camera.bbox, 1.0);
                this.renderer.draw(this.camera.matrix);
                this.drawTextOverlay();
            }
            requestAnimationFrame(loop);
        };
        requestAnimationFrame(loop);
    }
}
