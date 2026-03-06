import { Vec2, BBox } from "./math";
import { Camera2 } from "./camera";
import { PanAndZoom } from "./pan-and-zoom";
import { Renderer } from "./webgl/renderer";
import { paintStaticBoard, computeBBox } from "./painter";
import { renderTextOverlay } from "./text_overlay";
import { RenderLoop } from "./render_loop";
import type { EdgeModel, LayerModel, Point2, RenderModel } from "./types";

export interface StaticLayoutViewerOptions {
    minZoom?: number;
    maxZoom?: number;
}

function pushPoint(points: Vec2[], point?: Point2 | null): void {
    if (!point) return;
    points.push(new Vec2(point.x, point.y));
}

function computeBoardEdgeBBox(model: RenderModel): BBox | null {
    const points: Vec2[] = [];
    for (const edge of model.board.edges) {
        pushPoint(points, edge.start);
        pushPoint(points, edge.end);
        pushPoint(points, edge.mid);
        pushPoint(points, edge.center);
        if (edge.type === "circle" && edge.center && edge.end) {
            const radius = Math.hypot(edge.end.x - edge.center.x, edge.end.y - edge.center.y);
            if (radius > 0) {
                points.push(new Vec2(edge.center.x - radius, edge.center.y - radius));
                points.push(new Vec2(edge.center.x + radius, edge.center.y + radius));
            }
        }
    }
    if (points.length === 0) return null;
    return BBox.from_points(points).grow(2);
}

export class StaticLayoutViewer {
    private readonly canvas: HTMLCanvasElement;
    private readonly overlay: HTMLCanvasElement;
    private readonly overlayCtx: CanvasRenderingContext2D | null;
    private readonly renderer: Renderer;
    private readonly camera: Camera2;
    private readonly panAndZoom: PanAndZoom;
    private readonly renderLoop: RenderLoop;
    private readonly resizeObserver: ResizeObserver;
    private readonly hiddenLayers = new Set<string>();
    private model: RenderModel | null = null;
    private needsRedraw = true;

    constructor(
        private readonly container: HTMLElement,
        options: StaticLayoutViewerOptions = {},
    ) {
        this.container.classList.add("atopile-static-layout-viewer");

        this.canvas = document.createElement("canvas");
        this.canvas.className = "atopile-static-layout-canvas";
        this.canvas.style.width = "100%";
        this.canvas.style.height = "100%";
        this.canvas.style.display = "block";
        this.canvas.style.touchAction = "none";

        this.overlay = document.createElement("canvas");
        this.overlay.className = "atopile-static-layout-overlay";
        this.overlay.style.position = "absolute";
        this.overlay.style.inset = "0";
        this.overlay.style.width = "100%";
        this.overlay.style.height = "100%";
        this.overlay.style.pointerEvents = "none";

        const rootStyle = this.container.style;
        const computedPosition = getComputedStyle(this.container).position;
        if (computedPosition === "static") rootStyle.position = "relative";
        if (!rootStyle.overflow) rootStyle.overflow = "hidden";

        this.container.appendChild(this.canvas);
        this.container.appendChild(this.overlay);

        this.overlayCtx = this.overlay.getContext("2d");
        this.renderer = new Renderer(this.canvas);
        this.renderer.setup();

        this.camera = new Camera2();
        this.panAndZoom = new PanAndZoom(
            this.canvas,
            this.camera,
            () => this.requestRedraw(),
            options.minZoom ?? 0.08,
            options.maxZoom ?? 400,
        );
        this.renderLoop = new RenderLoop(() => this.onRenderFrame());
        this.renderLoop.start();

        this.resizeObserver = new ResizeObserver(() => {
            this.syncOverlaySize();
            this.fitToView();
            this.requestRedraw();
        });
        this.resizeObserver.observe(this.container);

        this.syncOverlaySize();
    }

    setModel(model: RenderModel): void {
        this.model = model;
        paintStaticBoard(this.renderer, model, this.hiddenLayers);
        this.fitToView();
        this.renderer.updateGrid(this.camera.bbox, 1.0);
        this.requestRedraw();
    }

    fitToView(): void {
        if (!this.model) return;
        const rect = this.container.getBoundingClientRect();
        this.camera.viewport_size = new Vec2(
            rect.width || this.canvas.clientWidth || 1,
            rect.height || this.canvas.clientHeight || 1,
        );
        this.camera.bbox = computeBoardEdgeBBox(this.model) ?? computeBBox(this.model);
        this.renderer.updateGrid(this.camera.bbox, 1.0);
    }

    setHiddenLayers(layers: Iterable<string>): void {
        this.hiddenLayers.clear();
        for (const layer of layers) this.hiddenLayers.add(layer);
        if (this.model) {
            paintStaticBoard(this.renderer, this.model, this.hiddenLayers);
        }
        this.requestRedraw();
    }

    getLayerModels(): LayerModel[] {
        if (!this.model) return [];
        return [...this.model.layers].sort((a, b) => {
            const orderDiff = a.panel_order - b.panel_order;
            if (orderDiff !== 0) return orderDiff;
            return a.id.localeCompare(b.id);
        });
    }

    destroy(): void {
        this.resizeObserver.disconnect();
        this.renderLoop.stop();
        this.renderer.dispose_layers();
        this.container.replaceChildren();
    }

    private requestRedraw(): void {
        this.needsRedraw = true;
    }

    private syncOverlaySize(): void {
        const dpr = Math.max(window.devicePixelRatio || 1, 1);
        const rect = this.container.getBoundingClientRect();
        const width = Math.max(1, Math.round((rect.width || this.canvas.clientWidth || 1) * dpr));
        const height = Math.max(1, Math.round((rect.height || this.canvas.clientHeight || 1) * dpr));
        if (this.overlay.width !== width) this.overlay.width = width;
        if (this.overlay.height !== height) this.overlay.height = height;
    }

    private getLayerMap(): Map<string, LayerModel> {
        const layerById = new Map<string, LayerModel>();
        if (!this.model) return layerById;
        for (const layer of this.model.layers) layerById.set(layer.id, layer);
        return layerById;
    }

    private drawTextOverlay(): void {
        if (!this.overlayCtx || !this.model) return;
        const rect = this.container.getBoundingClientRect();
        renderTextOverlay(
            this.overlayCtx,
            this.model,
            this.camera,
            this.hiddenLayers,
            this.getLayerMap(),
            rect.width || this.canvas.clientWidth || 1,
            rect.height || this.canvas.clientHeight || 1,
            undefined,
            { clearCanvas: true },
        );
    }

    private onRenderFrame(): void {
        if (!this.needsRedraw) return;
        this.needsRedraw = false;
        const rect = this.container.getBoundingClientRect();
        this.camera.viewport_size = new Vec2(
            rect.width || this.canvas.clientWidth || 1,
            rect.height || this.canvas.clientHeight || 1,
        );
        this.renderer.updateGrid(this.camera.bbox, 1.0);
        this.renderer.draw(this.camera.matrix);
        this.drawTextOverlay();
    }
}
