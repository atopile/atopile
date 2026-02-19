import { Vec2 } from "./math";
import { Camera2 } from "./camera";
import { PanAndZoom } from "./pan-and-zoom";
import { Renderer } from "./webgl/renderer";
import { paintAll, paintSelection, paintFootprint, computeBBox } from "./painter";
import { hitTestFootprints, hitTestPads } from "./hit-test";
import type { Color } from "./colors";
import type { RenderModel } from "./types";

export class Editor {
    private canvas: HTMLCanvasElement;
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
    private onLayersChanged: (() => void) | null = null;

    // Track current mouse position
    private lastMouseScreen: Vec2 = new Vec2(0, 0);

    // Mouse coordinate callback
    private onMouseMoveCallback: ((x: number, y: number) => void) | null = null;

    // Pinout viewer mode
    private readOnly = false;
    private padColorOverrides: Map<string, Color> | undefined;
    private highlightedPads: Set<string> | undefined;
    private onPadClickCallback: ((padName: string) => void) | null = null;
    private outlinePads: Set<string> | undefined;
    private externalModel = false;

    constructor(canvas: HTMLCanvasElement, baseUrl: string, apiPrefix = "/api", wsPath = "/ws") {
        this.canvas = canvas;
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

    async init() {
        if (this.externalModel) return;
        await this.fetchAndPaint();
        this.connectWebSocket();
    }

    /** Inject a model externally (for pinout viewer use) */
    setModel(model: RenderModel, fitToView = true) {
        this.externalModel = true;
        this.applyModel(model, fitToView);
    }

    /** Set read-only mode (disables drag, keyboard, footprint selection) */
    setReadOnly(readOnly: boolean) {
        this.readOnly = readOnly;
    }

    /** Set per-pad color overrides (pad name → color) */
    setPadColorOverrides(overrides: Map<string, Color>) {
        this.padColorOverrides = overrides;
        this.paint();
        this.requestRedraw();
    }

    /** Set which pads should be highlighted */
    setHighlightedPads(padNames: Set<string>) {
        this.highlightedPads = padNames;
        this.paint();
        this.requestRedraw();
    }

    /** Set which pads should be drawn as outlines (unconnected) */
    setOutlinePads(padNames: Set<string>) {
        this.outlinePads = padNames;
        this.paint();
        this.requestRedraw();
    }

    /** Set callback when a pad is clicked (read-only mode) */
    setOnPadClick(cb: ((padName: string) => void) | null) {
        this.onPadClickCallback = cb;
    }

    private async fetchAndPaint() {
        const resp = await fetch(`${this.baseUrl}${this.apiPrefix}/render-model`);
        this.applyModel(await resp.json(), true);
    }

    private applyModel(model: RenderModel, fitToView = false) {
        this.model = model;
        this.paint();

        this.camera.viewport_size = new Vec2(this.canvas.clientWidth, this.canvas.clientHeight);
        if (fitToView) {
            this.camera.bbox = computeBBox(this.model);
        }
        this.requestRedraw();
        if (this.onLayersChanged) this.onLayersChanged();
    }

    private paint() {
        if (!this.model) return;

        if (this.padColorOverrides || this.highlightedPads || this.outlinePads) {
            // Pinout mode: paint with per-pad overrides
            const hidden = this.hiddenLayers;
            const concreteLayers = new Set<string>();
            for (const fp of this.model.footprints) {
                concreteLayers.add(fp.layer);
                for (const pad of fp.pads) for (const l of pad.layers) concreteLayers.add(l);
                for (const d of fp.drawings) if (d.layer) concreteLayers.add(d.layer);
            }
            for (const l of concreteLayers) {
                if (l.includes("*") || l.includes("&")) concreteLayers.delete(l);
            }
            this.renderer.dispose_layers();
            for (const fp of this.model.footprints) {
                paintFootprint(this.renderer, fp, hidden, concreteLayers,
                    this.padColorOverrides, this.highlightedPads, this.outlinePads);
            }
        } else {
            paintAll(this.renderer, this.model, this.hiddenLayers);
        }

        if (this.selectedFpIndex >= 0 && this.selectedFpIndex < this.model.footprints.length) {
            paintSelection(this.renderer, this.model.footprints[this.selectedFpIndex]!);
        }
    }

    private connectWebSocket() {
        if (!this.wsPath) return;
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

            // Read-only mode: pad-level hit testing only
            if (this.readOnly) {
                if (this.onPadClickCallback && this.model.footprints.length > 0) {
                    for (const fp of this.model.footprints) {
                        const padIdx = hitTestPads(worldPos, fp);
                        if (padIdx >= 0) {
                            this.onPadClickCallback(fp.pads[padIdx]!.name);
                            return;
                        }
                    }
                }
                return;
            }

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

            if (this.readOnly || !this.isDragging || !this.model || this.selectedFpIndex < 0) return;

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
            if (this.readOnly) return;
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

    private startRenderLoop() {
        const loop = () => {
            if (this.needsRedraw) {
                this.needsRedraw = false;
                this.camera.viewport_size = new Vec2(this.canvas.clientWidth, this.canvas.clientHeight);
                this.renderer.updateGrid(this.camera.bbox, 1.0);
                this.renderer.draw(this.camera.matrix);
            }
            requestAnimationFrame(loop);
        };
        requestAnimationFrame(loop);
    }
}
