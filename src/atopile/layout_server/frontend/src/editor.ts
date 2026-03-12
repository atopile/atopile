import { Vec2, BBox, Matrix3 } from "./math";
import { Camera2 } from "./camera";
import { PanAndZoom } from "./pan-and-zoom";
import { Renderer } from "./webgl/renderer";
import { paintStaticBoard, paintGroupBBox, paintGroupHalos, paintBBoxOutline, paintSelection, computeBBox, paintDraggedSelection, buildDragOwnerIds, type DragSelection } from "./painter";
import { footprintBBox, hitTestFootprintsInBox } from "./hit-test";
import { LayoutClient } from "./layout_client";
import { renderTextOverlay } from "./text_overlay";
import { RenderLoop } from "./render_loop";
import { buildGroupIndex, type UiFootprintGroup } from "./footprint_groups";
import { SpatialIndex } from "./spatial_index";
import type { ActionCommand, DrawingModel, LayerModel, RenderDelta, RenderModel, ZoneModel } from "./types";

type SelectionMode = "none" | "single" | "group" | "multi";
const DRAG_START_THRESHOLD_PX = 4;

type PendingDrag = {
    startWorld: Vec2;
    startScreen: Vec2;
    targetIndices: number[];
    trackUuids: string[];
    viaUuids: string[];
    drawingUuids: string[];
    textUuids: string[];
    zoneUuids: string[];
};

function captureDrawingCoords(drawing: DrawingModel): number[] {
    switch (drawing.type) {
        case "line": return [drawing.start.x, drawing.start.y, drawing.end.x, drawing.end.y];
        case "arc": return [drawing.start.x, drawing.start.y, drawing.mid.x, drawing.mid.y, drawing.end.x, drawing.end.y];
        case "circle": return [drawing.center.x, drawing.center.y, drawing.end.x, drawing.end.y];
        case "rect": return [drawing.start.x, drawing.start.y, drawing.end.x, drawing.end.y];
        case "polygon": case "curve": return drawing.points.flatMap(p => [p.x, p.y]);
        default: return [];
    }
}

function applyDeltaToDrawing(drawing: DrawingModel, coords: number[], dx: number, dy: number): void {
    let i = 0;
    switch (drawing.type) {
        case "line":
            drawing.start.x = coords[i++]! + dx; drawing.start.y = coords[i++]! + dy;
            drawing.end.x = coords[i++]! + dx; drawing.end.y = coords[i++]! + dy;
            break;
        case "arc":
            drawing.start.x = coords[i++]! + dx; drawing.start.y = coords[i++]! + dy;
            drawing.mid.x = coords[i++]! + dx; drawing.mid.y = coords[i++]! + dy;
            drawing.end.x = coords[i++]! + dx; drawing.end.y = coords[i++]! + dy;
            break;
        case "circle":
            drawing.center.x = coords[i++]! + dx; drawing.center.y = coords[i++]! + dy;
            drawing.end.x = coords[i++]! + dx; drawing.end.y = coords[i++]! + dy;
            break;
        case "rect":
            drawing.start.x = coords[i++]! + dx; drawing.start.y = coords[i++]! + dy;
            drawing.end.x = coords[i++]! + dx; drawing.end.y = coords[i++]! + dy;
            break;
        case "polygon": case "curve":
            for (const pt of drawing.points) {
                pt.x = coords[i++]! + dx; pt.y = coords[i++]! + dy;
            }
            break;
    }
}

function captureZoneCoords(zone: ZoneModel): { outline: number[]; fills: number[][] } {
    return {
        outline: zone.outline.flatMap(p => [p.x, p.y]),
        fills: zone.filled_polygons.map(fp => fp.points.flatMap(p => [p.x, p.y])),
    };
}

function applyDeltaToZone(zone: ZoneModel, coords: { outline: number[]; fills: number[][] }, dx: number, dy: number): void {
    for (let i = 0; i < zone.outline.length; i++) {
        zone.outline[i]!.x = coords.outline[i * 2]! + dx;
        zone.outline[i]!.y = coords.outline[i * 2 + 1]! + dy;
    }
    for (let fi = 0; fi < zone.filled_polygons.length; fi++) {
        const fillPts = zone.filled_polygons[fi]!.points;
        const fillCoords = coords.fills[fi];
        if (!fillCoords) continue;
        for (let i = 0; i < fillPts.length; i++) {
            fillPts[i]!.x = fillCoords[i * 2]! + dx;
            fillPts[i]!.y = fillCoords[i * 2 + 1]! + dy;
        }
    }
}

export class Editor {
    private canvas: HTMLCanvasElement;
    private textOverlay: HTMLCanvasElement;
    private textCtx: CanvasRenderingContext2D | null;
    private renderer: Renderer;
    private camera: Camera2;
    private panAndZoom: PanAndZoom;
    private client: LayoutClient;
    private renderLoop: RenderLoop;
    private model: RenderModel | null = null;
    private footprintIndex: SpatialIndex = new SpatialIndex(5);
    private footprintBBoxes: BBox[] = [];
    private textIndex: SpatialIndex = new SpatialIndex(10);

    // Selection & interaction state
    private selectionMode: SelectionMode = "none";
    private selectedFpIndex = -1;
    private selectedGroupId: string | null = null;
    private selectedMultiIndices: number[] = [];
    private hoveredGroupId: string | null = null;
    private hoveredFpIndex = -1;
    private singleOverrideMode = false;
    private groupsById = new Map<string, UiFootprintGroup>();
    private groupIdByFpIndex = new Map<number, string>();
    private trackIndexByUuid = new Map<string, number>();
    private viaIndexByUuid = new Map<string, number>();
    private drawingIndexByUuid = new Map<string, number>();
    private textIndexByUuid = new Map<string, number>();
    private zoneIndexByUuid = new Map<string, number>();
    private dragTargetDrawingUuids: string[] = [];
    private dragStartDrawingCoords: Map<string, number[]> | null = null;
    private dragTargetTextUuids: string[] = [];
    private dragStartTextPositions: Map<string, { x: number; y: number; r: number }> | null = null;
    private dragTargetZoneUuids: string[] = [];
    private dragStartZoneCoords: Map<string, { outline: number[]; fills: number[][] }> | null = null;

    private isDragging = false;
    private dragStartWorld: Vec2 | null = null;
    private dragTargetIndices: number[] = [];
    private dragStartPositions: Map<number, { x: number; y: number }> | null = null;
    private dragTargetTrackUuids: string[] = [];
    private dragStartTrackPositions: Map<string, { sx: number; sy: number; ex: number; ey: number; mx?: number; my?: number }> | null = null;
    private dragTargetViaUuids: string[] = [];
    private dragStartViaPositions: Map<string, { x: number; y: number }> | null = null;
    private dragCacheActive = false;
    private pendingDrag: PendingDrag | null = null;
    private isBoxSelecting = false;
    private boxSelectStartWorld: Vec2 | null = null;
    private boxSelectCurrentWorld: Vec2 | null = null;
    private dynamicDirty = false;
    private needsRedraw = true;

    // Layer visibility
    private hiddenLayers: Set<string> = new Set();
    private defaultLayerVisibilityApplied = new Set<string>();
    private onLayersChanged: (() => void) | null = null;

    // Track current mouse position
    private lastMouseScreen: Vec2 = new Vec2(0, 0);

    // Mouse coordinate callback
    private onMouseMoveCallback: ((x: number, y: number) => void) | null = null;
    private onActionBusyChanged: ((busy: boolean) => void) | null = null;
    private pendingActionRequests = 0;
    private actionNonce = 0;

    // Snap-to-grid callback: transforms raw drag delta into snapped delta
    private snapDelta: ((dx: number, dy: number) => { dx: number; dy: number }) | null = null;

    constructor(canvas: HTMLCanvasElement, baseUrl: string, apiPrefix = "/api", wsPath = "/ws") {
        this.canvas = canvas;
        this.textOverlay = this.createTextOverlay();
        this.textCtx = this.textOverlay.getContext("2d");
        this.syncTextOverlayViewport();
        this.renderer = new Renderer(canvas);
        this.camera = new Camera2();
        this.panAndZoom = new PanAndZoom(canvas, this.camera, () => this.requestRedraw());
        this.client = new LayoutClient(baseUrl, apiPrefix, wsPath);
        this.renderLoop = new RenderLoop(() => this.onRenderFrame());

        this.setupMouseHandlers();
        this.setupKeyboardHandlers();
        this.setupResizeHandler();
        window.addEventListener("beforeunload", () => {
            this.renderLoop.stop();
            this.client.disconnect();
        });
        this.renderer.setup();
        this.renderLoop.start();
    }

    syncTheme() {
        this.renderer.setClearColor(getComputedStyle(document.body).getPropertyValue("--vscode-editor-background"));
        this.requestRedraw();
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

    private getCanvasViewportMetrics(): { left: number; top: number; width: number; height: number } {
        const rect = this.canvas.getBoundingClientRect();
        const width = rect.width > 0 ? rect.width : (this.canvas.clientWidth || window.innerWidth);
        const height = rect.height > 0 ? rect.height : (this.canvas.clientHeight || window.innerHeight);
        return {
            left: Number.isFinite(rect.left) ? rect.left : 0,
            top: Number.isFinite(rect.top) ? rect.top : 0,
            width,
            height,
        };
    }

    private syncTextOverlayViewport(
        viewport = this.getCanvasViewportMetrics(),
    ): void {
        const left = `${viewport.left}px`;
        const top = `${viewport.top}px`;
        const width = `${viewport.width}px`;
        const height = `${viewport.height}px`;
        if (this.textOverlay.style.left !== left) this.textOverlay.style.left = left;
        if (this.textOverlay.style.top !== top) this.textOverlay.style.top = top;
        if (this.textOverlay.style.width !== width) this.textOverlay.style.width = width;
        if (this.textOverlay.style.height !== height) this.textOverlay.style.height = height;
    }

    async init() {
        await this.fetchAndPaint();
        this.connectWebSocket();
    }

    private async fetchAndPaint() {
        const model = await this.client.fetchRenderModel();
        this.applyModel(model, true);
    }

    private applyModel(model: RenderModel, fitToView = false) {
        const prevSelectedUuid = this.getSelectedSingleUuid();
        const prevSelectedMultiUuids = this.getSelectedMultiUuids();
        const prevSelectedGroupId = this.selectedGroupId;
        const prevSingleOverride = this.singleOverrideMode;

        this.model = model;
        this.rebuildGroupIndex();
        this.rebuildSpatialIndexes();
        this.restoreSelection(prevSelectedUuid, prevSelectedMultiUuids, prevSelectedGroupId, prevSingleOverride);
        this.applyDefaultLayerVisibility();
        
        // Pre-tessellate all physical layers (for instant visibility toggles),
        // but still respect object-type filters.
        this.paintStatic();
        this.paintDynamic();

        const viewport = this.getCanvasViewportMetrics();
        this.camera.viewport_size = new Vec2(viewport.width, viewport.height);
        if (fitToView) {
            this.camera.bbox = computeBBox(this.model);
        }
        this.requestRedraw();
        if (this.onLayersChanged) this.onLayersChanged();
    }

    private applyDelta(delta: RenderDelta) {
        if (!this.model) return;
        let changed = false;
        changed = this.replaceByUuid(this.model.footprints, delta.footprints) || changed;
        changed = this.replaceByUuid(this.model.tracks, delta.tracks) || changed;
        changed = this.replaceByUuid(this.model.vias, delta.vias) || changed;
        changed = this.replaceByUuid(this.model.drawings, delta.drawings) || changed;
        changed = this.replaceByUuid(this.model.texts, delta.texts) || changed;
        changed = this.replaceByUuid(this.model.zones, delta.zones) || changed;
        if (!changed) return;

        this.rebuildGroupIndex();
        this.rebuildSpatialIndexes();
        this.paintStatic();
        this.paintDynamic();
        this.requestRedraw();
    }

    private replaceByUuid<T extends { uuid: string | null }>(target: T[], updates: T[]): boolean {
        if (updates.length === 0) return false;
        const indexByUuid = new Map<string, number>();
        for (let i = 0; i < target.length; i++) {
            const uuid = target[i]?.uuid;
            if (uuid) indexByUuid.set(uuid, i);
        }
        let changed = false;
        for (const update of updates) {
            const uuid = update.uuid;
            if (!uuid) continue;
            const idx = indexByUuid.get(uuid);
            if (idx === undefined) continue;
            target[idx] = update;
            changed = true;
        }
        return changed;
    }

    private applyDefaultLayerVisibility() {
        if (!this.model) return;
        for (const layer of this.model.layers) {
            if (this.defaultLayerVisibilityApplied.has(layer.id)) continue;
            this.defaultLayerVisibilityApplied.add(layer.id);
            if (!layer.default_visible) {
                this.hiddenLayers.add(layer.id);
            }
        }
    }

    private paintStatic(skipped?: DragSelection) {
        if (!this.model) return;
        const geometryHidden = new Set(
            [...this.hiddenLayers].filter(layer => layer.startsWith("__type:")),
        );
        paintStaticBoard(this.renderer, this.model, geometryHidden, skipped);
        
        // Ensure renderer internal visibility matches editor hiddenLayers
        for (const layer of this.model.layers) {
            this.renderer.set_layer_visible(layer.id, !this.hiddenLayers.has(layer.id));
        }
        this.renderer.set_layer_visible("Edge.Cuts", !this.hiddenLayers.has("Edge.Cuts"));
    }

    private paintDynamic() {
        this.dynamicDirty = false;
        this.renderer.dispose_dynamic_overlays();
        if (!this.model) return;

        if (
            !this.singleOverrideMode
            && this.selectionMode !== "multi"
            && this.hoveredGroupId
            && this.hoveredGroupId !== this.selectedGroupId
        ) {
            const hovered = this.groupsById.get(this.hoveredGroupId);
            if (hovered) {
                if (hovered.memberIndices.length > 0) {
                    paintGroupBBox(this.renderer, this.model.footprints, hovered.memberIndices, "hover");
                    paintGroupHalos(this.renderer, this.model.footprints, hovered.memberIndices, "hover");
                } else if (hovered.graphicBBox) {
                    paintBBoxOutline(this.renderer, hovered.graphicBBox, "hover");
                }
            }
        }
        if (
            !this.singleOverrideMode
            && this.hoveredFpIndex >= 0
            && this.hoveredFpIndex < this.model.footprints.length
            && !(this.selectionMode === "single" && this.selectedFpIndex === this.hoveredFpIndex)
        ) {
            paintGroupHalos(this.renderer, this.model.footprints, [this.hoveredFpIndex], "hover");
        }

        if (!this.singleOverrideMode && this.selectedGroupId) {
            const selectedGroup = this.groupsById.get(this.selectedGroupId);
            if (selectedGroup) {
                if (selectedGroup.memberIndices.length > 0) {
                    paintGroupBBox(this.renderer, this.model.footprints, selectedGroup.memberIndices, "selected");
                    paintGroupHalos(this.renderer, this.model.footprints, selectedGroup.memberIndices, "selected");
                } else if (selectedGroup.graphicBBox) {
                    paintBBoxOutline(this.renderer, selectedGroup.graphicBBox, "selected");
                }
            }
        }

        if (this.selectionMode === "multi" && this.selectedMultiIndices.length > 0) {
            paintGroupHalos(this.renderer, this.model.footprints, this.selectedMultiIndices, "selected");
        }

        if (this.selectionMode === "single" && this.selectedFpIndex >= 0 && this.selectedFpIndex < this.model.footprints.length) {
            paintSelection(this.renderer, this.model.footprints[this.selectedFpIndex]!);
        }

        this.paintBoxSelectionOverlay();

        // If dragging, apply the current delta to all dynamic layers
        if (this.isDragging && this.dragStartWorld) {
            const worldPos = this.camera.screen_to_world(this.lastMouseScreen);
            const delta = this.applySnap(worldPos.sub(this.dragStartWorld));
            const trans = Matrix3.translation(delta.x, delta.y);
            for (const layer of this.renderer.dynamicLayers) {
                layer.transform = trans;
            }
        }
    }

    private rebuildGroupIndex() {
        if (!this.model) return;
        const index = buildGroupIndex(this.model);
        this.groupsById = index.groupsById;
        this.groupIdByFpIndex = index.groupIdByFpIndex;
        this.trackIndexByUuid = index.trackIndexByUuid;
        this.viaIndexByUuid = index.viaIndexByUuid;
        this.drawingIndexByUuid = index.drawingIndexByUuid;
        this.textIndexByUuid = index.textIndexByUuid;
        this.zoneIndexByUuid = index.zoneIndexByUuid;
    }

    private rebuildSpatialIndexes() {
        if (!this.model) return;
        this.footprintIndex.clear();
        this.footprintBBoxes = new Array(this.model.footprints.length);
        for (let i = 0; i < this.model.footprints.length; i++) {
            const fp = this.model.footprints[i]!;
            const bbox = footprintBBox(fp);
            this.footprintBBoxes[i] = bbox;
            this.footprintIndex.insert({ bbox, index: i });
        }
        this.textIndex.clear();
        for (let i = 0; i < this.model.texts.length; i++) {
            const txt = this.model.texts[i]!;
            // Simplified text bbox for indexing
            const bbox = new BBox(txt.at.x - 1, txt.at.y - 1, 2, 2);
            this.textIndex.insert({ bbox, index: i });
        }
    }

    private getSelectedSingleUuid(): string | null {
        if (!this.model || this.selectedFpIndex < 0) return null;
        return this.model.footprints[this.selectedFpIndex]?.uuid ?? null;
    }

    private getSelectedMultiUuids(): string[] {
        if (!this.model || this.selectionMode !== "multi" || this.selectedMultiIndices.length === 0) return [];
        const uuids: string[] = [];
        for (const index of this.selectedMultiIndices) {
            const uuid = this.model.footprints[index]?.uuid;
            if (uuid) uuids.push(uuid);
        }
        return uuids;
    }

    private restoreSelection(
        prevSelectedUuid: string | null,
        prevSelectedMultiUuids: string[],
        prevSelectedGroupId: string | null,
        prevSingleOverride: boolean,
    ) {
        this.selectionMode = "none";
        this.selectedFpIndex = -1;
        this.selectedGroupId = null;
        this.selectedMultiIndices = [];
        this.hoveredGroupId = null;
        this.hoveredFpIndex = -1;
        this.singleOverrideMode = prevSingleOverride;

        if (!this.model) {
            this.singleOverrideMode = false;
            return;
        }

        if (!prevSingleOverride && prevSelectedGroupId && this.groupsById.has(prevSelectedGroupId)) {
            this.selectionMode = "group";
            this.selectedGroupId = prevSelectedGroupId;
            return;
        }

        if (!prevSingleOverride && prevSelectedMultiUuids.length > 0) {
            const selectedIndices: number[] = [];
            const selectedSet = new Set(prevSelectedMultiUuids);
            for (let i = 0; i < this.model.footprints.length; i++) {
                const uuid = this.model.footprints[i]!.uuid;
                if (uuid && selectedSet.has(uuid)) selectedIndices.push(i);
            }
            if (selectedIndices.length >= 2) {
                this.setMultiSelection(selectedIndices);
                return;
            }
            if (selectedIndices.length === 1) {
                this.setSingleSelection(selectedIndices[0]!, false);
                return;
            }
        }

        if (prevSelectedUuid) {
            for (let i = 0; i < this.model.footprints.length; i++) {
                if (this.model.footprints[i]!.uuid === prevSelectedUuid) {
                    this.selectionMode = "single";
                    this.selectedFpIndex = i;
                    return;
                }
            }
        }

        this.singleOverrideMode = false;
    }

    private setSingleSelection(index: number, enterOverride: boolean) {
        this.selectionMode = "single";
        this.selectedFpIndex = index;
        this.selectedGroupId = null;
        this.selectedMultiIndices = [];
        if (enterOverride) {
            this.singleOverrideMode = true;
        } else if (!this.groupIdByFpIndex.has(index)) {
            this.singleOverrideMode = false;
        }
    }

    private setMultiSelection(indices: number[]) {
        const normalized = [...new Set(indices)].filter(i => i >= 0).sort((a, b) => a - b);
        if (normalized.length === 0) {
            this.clearSelection();
            return;
        }
        if (normalized.length === 1) {
            this.setSingleSelection(normalized[0]!, false);
            return;
        }
        this.selectionMode = "multi";
        this.selectedMultiIndices = normalized;
        this.selectedGroupId = null;
        this.selectedFpIndex = -1;
        this.singleOverrideMode = false;
    }

    private setGroupSelection(groupId: string) {
        this.selectionMode = "group";
        this.selectedGroupId = groupId;
        this.selectedFpIndex = -1;
        this.selectedMultiIndices = [];
        this.singleOverrideMode = false;
    }

    private clearSelection(exitSingleOverride = false) {
        if (this.isDragging) {
            this.restorePostDragRendering();
        }
        this.selectionMode = "none";
        this.selectedFpIndex = -1;
        this.selectedGroupId = null;
        this.selectedMultiIndices = [];
        this.hoveredGroupId = null;
        this.hoveredFpIndex = -1;
        this.clearDragState();
        this.clearBoxSelectionState();
        if (exitSingleOverride) {
            this.singleOverrideMode = false;
        }
    }

    private selectedGroup(): UiFootprintGroup | null {
        if (!this.selectedGroupId) return null;
        return this.groupsById.get(this.selectedGroupId) ?? null;
    }

    private selectedGroupMembers(): number[] {
        const group = this.selectedGroup();
        return group ? group.memberIndices : [];
    }

    private selectedUuids(): string[] {
        if (this.singleOverrideMode && this.selectedFpIndex >= 0) {
            const uuid = this.model?.footprints[this.selectedFpIndex]?.uuid;
            return uuid ? [uuid] : [];
        }
        if (this.selectionMode === "group" && this.selectedGroupId) {
            const group = this.groupsById.get(this.selectedGroupId);
            // Send the KiCad group UUID — backend resolves to members
            return group?.uuid ? [group.uuid] : (group?.memberUuids ?? []);
        }
        if (this.selectionMode === "multi") return this.getSelectedMultiUuids();
        if (this.selectionMode === "single" && this.selectedFpIndex >= 0) {
            const uuid = this.model?.footprints[this.selectedFpIndex]?.uuid;
            return uuid ? [uuid] : [];
        }
        return [];
    }

    /** Restore all model positions from the saved drag start state. */
    private revertDragPositions() {
        if (!this.model) return;
        if (this.dragStartPositions) {
            for (const index of this.dragTargetIndices) {
                const fp = this.model.footprints[index];
                const start = this.dragStartPositions.get(index);
                if (fp && start) { fp.at.x = start.x; fp.at.y = start.y; }
            }
        }
        if (this.dragStartTrackPositions) {
            for (const uuid of this.dragTargetTrackUuids) {
                const idx = this.trackIndexByUuid.get(uuid);
                if (idx === undefined) continue;
                const track = this.model.tracks[idx];
                const start = this.dragStartTrackPositions.get(uuid);
                if (!track || !start) continue;
                track.start.x = start.sx; track.start.y = start.sy;
                track.end.x = start.ex; track.end.y = start.ey;
                if (track.mid && start.mx !== undefined && start.my !== undefined) {
                    track.mid.x = start.mx; track.mid.y = start.my;
                }
            }
        }
        if (this.dragStartViaPositions) {
            for (const uuid of this.dragTargetViaUuids) {
                const idx = this.viaIndexByUuid.get(uuid);
                if (idx === undefined) continue;
                const via = this.model.vias[idx];
                const start = this.dragStartViaPositions.get(uuid);
                if (via && start) { via.at.x = start.x; via.at.y = start.y; }
            }
        }
        if (this.dragStartDrawingCoords) {
            for (const uuid of this.dragTargetDrawingUuids) {
                const idx = this.drawingIndexByUuid.get(uuid);
                if (idx === undefined) continue;
                const drawing = this.model.drawings[idx];
                const coords = this.dragStartDrawingCoords.get(uuid);
                if (drawing && coords) applyDeltaToDrawing(drawing, coords, 0, 0);
            }
        }
        if (this.dragStartTextPositions) {
            for (const uuid of this.dragTargetTextUuids) {
                const idx = this.textIndexByUuid.get(uuid);
                if (idx === undefined) continue;
                const text = this.model.texts[idx];
                const start = this.dragStartTextPositions.get(uuid);
                if (text && start) { text.at.x = start.x; text.at.y = start.y; }
            }
        }
        if (this.dragStartZoneCoords) {
            for (const uuid of this.dragTargetZoneUuids) {
                const idx = this.zoneIndexByUuid.get(uuid);
                if (idx === undefined) continue;
                const zone = this.model.zones[idx];
                const coords = this.dragStartZoneCoords.get(uuid);
                if (zone && coords) applyDeltaToZone(zone, coords, 0, 0);
            }
        }
    }

    /** Apply a drag delta to all currently tracked drag targets. */
    private applyDragDelta(dx: number, dy: number) {
        if (!this.model) return;
        if (this.dragStartPositions) {
            for (const index of this.dragTargetIndices) {
                const fp = this.model.footprints[index];
                const start = this.dragStartPositions.get(index);
                if (fp && start) { fp.at.x = start.x + dx; fp.at.y = start.y + dy; }
            }
        }
        if (this.dragStartTrackPositions) {
            for (const uuid of this.dragTargetTrackUuids) {
                const idx = this.trackIndexByUuid.get(uuid);
                if (idx === undefined) continue;
                const track = this.model.tracks[idx];
                const start = this.dragStartTrackPositions.get(uuid);
                if (!track || !start) continue;
                track.start.x = start.sx + dx; track.start.y = start.sy + dy;
                track.end.x = start.ex + dx; track.end.y = start.ey + dy;
                if (track.mid && start.mx !== undefined && start.my !== undefined) {
                    track.mid.x = start.mx + dx; track.mid.y = start.my + dy;
                }
            }
        }
        if (this.dragStartViaPositions) {
            for (const uuid of this.dragTargetViaUuids) {
                const idx = this.viaIndexByUuid.get(uuid);
                if (idx === undefined) continue;
                const via = this.model.vias[idx];
                const start = this.dragStartViaPositions.get(uuid);
                if (via && start) { via.at.x = start.x + dx; via.at.y = start.y + dy; }
            }
        }
        if (this.dragStartDrawingCoords) {
            for (const uuid of this.dragTargetDrawingUuids) {
                const idx = this.drawingIndexByUuid.get(uuid);
                if (idx === undefined) continue;
                const drawing = this.model.drawings[idx];
                const coords = this.dragStartDrawingCoords.get(uuid);
                if (drawing && coords) applyDeltaToDrawing(drawing, coords, dx, dy);
            }
        }
        if (this.dragStartTextPositions) {
            for (const uuid of this.dragTargetTextUuids) {
                const idx = this.textIndexByUuid.get(uuid);
                if (idx === undefined) continue;
                const text = this.model.texts[idx];
                const start = this.dragStartTextPositions.get(uuid);
                if (text && start) { text.at.x = start.x + dx; text.at.y = start.y + dy; }
            }
        }
        if (this.dragStartZoneCoords) {
            for (const uuid of this.dragTargetZoneUuids) {
                const idx = this.zoneIndexByUuid.get(uuid);
                if (idx === undefined) continue;
                const zone = this.model.zones[idx];
                const coords = this.dragStartZoneCoords.get(uuid);
                if (zone && coords) applyDeltaToZone(zone, coords, dx, dy);
            }
        }
    }

    private clearDragState() {
        this.isDragging = false;
        this.dragStartWorld = null;
        this.dragStartPositions = null;
        this.dragTargetIndices = [];
        this.dragTargetTrackUuids = [];
        this.dragStartTrackPositions = null;
        this.dragTargetViaUuids = [];
        this.dragStartViaPositions = null;
        this.dragTargetDrawingUuids = [];
        this.dragStartDrawingCoords = null;
        this.dragTargetTextUuids = [];
        this.dragStartTextPositions = null;
        this.dragTargetZoneUuids = [];
        this.dragStartZoneCoords = null;
        this.dragCacheActive = false;
        this.pendingDrag = null;
    }

    private restorePostDragRendering() {
        if (!this.model) return;
        this.renderer.end_fast_drag_cache();
        this.dragCacheActive = false;
        this.renderer.dispose_dynamic_layers();
        this.paintStatic();
    }

    private isObjectTypeLayer(layer: string): boolean {
        return layer.startsWith("__type:");
    }

    private currentDraggedSelection(): DragSelection {
        return {
            footprintIndices: new Set(this.dragTargetIndices),
            trackUuids: new Set(this.dragTargetTrackUuids),
            viaUuids: new Set(this.dragTargetViaUuids),
            drawingUuids: new Set(this.dragTargetDrawingUuids),
            textUuids: new Set(this.dragTargetTextUuids),
            zoneUuids: new Set(this.dragTargetZoneUuids),
        };
    }

    private rebuildAfterObjectTypeVisibilityChange() {
        if (!this.model) return;
        if (this.isDragging) {
            const draggedSelection = this.currentDraggedSelection();
            const skipOwners = buildDragOwnerIds(this.model, draggedSelection);
            this.dragCacheActive = this.renderer.begin_fast_drag_cache(this.camera.matrix, skipOwners);
            if (!this.dragCacheActive) {
                this.paintStatic(draggedSelection);
            }
            this.renderer.dispose_dynamic_layers();
            this.renderer.isDynamicContext = true;
            paintDraggedSelection(this.renderer, this.model, draggedSelection, this.getLayerMap(), this.hiddenLayers);
            this.renderer.commit_dynamic_context_layers();
            this.renderer.isDynamicContext = false;
        } else {
            this.paintStatic();
        }
    }

    private clearBoxSelectionState() {
        this.isBoxSelecting = false;
        this.boxSelectStartWorld = null;
        this.boxSelectCurrentWorld = null;
    }

    private beginDragSelection(worldPos: Vec2, targetIndices: number[], trackUuids: string[] = [], viaUuids: string[] = [], drawingUuids: string[] = [], textUuids: string[] = [], zoneUuids: string[] = []) {
        const dragStartPositions = new Map<number, { x: number; y: number }>();
        for (const index of targetIndices) {
            const fp = this.model?.footprints[index];
            if (!fp) continue;
            dragStartPositions.set(index, { x: fp.at.x, y: fp.at.y });
        }
        // Allow drag even with no footprints if drawings/texts/zones are being dragged.
        if (dragStartPositions.size === 0 && drawingUuids.length === 0 && textUuids.length === 0 && zoneUuids.length === 0) {
            return false;
        }
        const dragStartTrackPositions = new Map<string, { sx: number; sy: number; ex: number; ey: number; mx?: number; my?: number }>();
        for (const uuid of trackUuids) {
            const idx = this.trackIndexByUuid.get(uuid);
            if (idx === undefined) continue;
            const track = this.model?.tracks[idx];
            if (!track) continue;
            dragStartTrackPositions.set(uuid, {
                sx: track.start.x, sy: track.start.y,
                ex: track.end.x, ey: track.end.y,
                ...(track.mid ? { mx: track.mid.x, my: track.mid.y } : {}),
            });
        }
        const dragStartViaPositions = new Map<string, { x: number; y: number }>();
        for (const uuid of viaUuids) {
            const idx = this.viaIndexByUuid.get(uuid);
            if (idx === undefined) continue;
            const via = this.model?.vias[idx];
            if (!via) continue;
            dragStartViaPositions.set(uuid, { x: via.at.x, y: via.at.y });
        }
        const dragStartDrawingCoords = new Map<string, number[]>();
        for (const uuid of drawingUuids) {
            const idx = this.drawingIndexByUuid.get(uuid);
            if (idx === undefined) continue;
            const drawing = this.model?.drawings[idx];
            if (!drawing) continue;
            dragStartDrawingCoords.set(uuid, captureDrawingCoords(drawing));
        }
        const dragStartTextPositions = new Map<string, { x: number; y: number; r: number }>();
        for (const uuid of textUuids) {
            const idx = this.textIndexByUuid.get(uuid);
            if (idx === undefined) continue;
            const text = this.model?.texts[idx];
            if (!text) continue;
            dragStartTextPositions.set(uuid, { x: text.at.x, y: text.at.y, r: text.at.r });
        }
        const dragStartZoneCoords = new Map<string, { outline: number[]; fills: number[][] }>();
        for (const uuid of zoneUuids) {
            const idx = this.zoneIndexByUuid.get(uuid);
            if (idx === undefined) continue;
            const zone = this.model?.zones[idx];
            if (!zone) continue;
            dragStartZoneCoords.set(uuid, captureZoneCoords(zone));
        }
        this.isDragging = true;
        this.dragStartWorld = worldPos;
        this.dragTargetIndices = [...dragStartPositions.keys()];
        this.dragStartPositions = dragStartPositions;
        this.dragTargetTrackUuids = [...dragStartTrackPositions.keys()];
        this.dragStartTrackPositions = dragStartTrackPositions;
        this.dragTargetViaUuids = [...dragStartViaPositions.keys()];
        this.dragStartViaPositions = dragStartViaPositions;
        this.dragTargetDrawingUuids = [...dragStartDrawingCoords.keys()];
        this.dragStartDrawingCoords = dragStartDrawingCoords;
        this.dragTargetTextUuids = [...dragStartTextPositions.keys()];
        this.dragStartTextPositions = dragStartTextPositions;
        this.dragTargetZoneUuids = [...dragStartZoneCoords.keys()];
        this.dragStartZoneCoords = dragStartZoneCoords;

        // Lift dragged objects out of static geometry so only moving copies are shown.
        const draggedSelection: DragSelection = {
            footprintIndices: new Set(this.dragTargetIndices),
            trackUuids: new Set(this.dragTargetTrackUuids),
            viaUuids: new Set(this.dragTargetViaUuids),
            drawingUuids: new Set(this.dragTargetDrawingUuids),
            textUuids: new Set(this.dragTargetTextUuids),
            zoneUuids: new Set(this.dragTargetZoneUuids),
        };
        const skipOwners = buildDragOwnerIds(this.model!, draggedSelection);
        this.dragCacheActive = this.renderer.begin_fast_drag_cache(this.camera.matrix, skipOwners);
        if (!this.dragCacheActive) {
            this.paintStatic(draggedSelection);
        }

        this.renderer.dispose_dynamic_layers();
        this.renderer.isDynamicContext = true;
        paintDraggedSelection(this.renderer, this.model!, draggedSelection, this.getLayerMap(), this.hiddenLayers);
        this.renderer.commit_dynamic_context_layers();
        this.renderer.isDynamicContext = false;

        this.paintDynamic();
        this.requestRedraw();
        return true;
    }

    private setPendingDrag(
        startWorld: Vec2,
        startScreen: Vec2,
        targetIndices: number[],
        trackUuids: string[] = [],
        viaUuids: string[] = [],
        drawingUuids: string[] = [],
        textUuids: string[] = [],
        zoneUuids: string[] = [],
    ) {
        this.pendingDrag = {
            startWorld,
            startScreen,
            targetIndices,
            trackUuids,
            viaUuids,
            drawingUuids,
            textUuids,
            zoneUuids,
        };
    }

    private maybeStartPendingDrag(currentWorld: Vec2, currentScreen: Vec2): boolean {
        const pending = this.pendingDrag;
        if (!pending) return false;
        const dx = currentScreen.x - pending.startScreen.x;
        const dy = currentScreen.y - pending.startScreen.y;
        if ((dx * dx + dy * dy) < (DRAG_START_THRESHOLD_PX * DRAG_START_THRESHOLD_PX)) {
            return false;
        }
        this.pendingDrag = null;
        return this.beginDragSelection(
            pending.startWorld,
            pending.targetIndices,
            pending.trackUuids,
            pending.viaUuids,
            pending.drawingUuids,
            pending.textUuids,
            pending.zoneUuids,
        );
    }

    private currentBoxSelection(): BBox | null {
        if (!this.boxSelectStartWorld || !this.boxSelectCurrentWorld) return null;
        return new BBox(
            this.boxSelectStartWorld.x,
            this.boxSelectStartWorld.y,
            this.boxSelectCurrentWorld.x - this.boxSelectStartWorld.x,
            this.boxSelectCurrentWorld.y - this.boxSelectStartWorld.y,
        );
    }

    private selectedIndicesForDrag(hitIdx: number): number[] {
        if (this.selectionMode === "group") {
            return this.selectedGroupMembers();
        }
        if (this.selectionMode === "multi" && this.selectedMultiIndices.includes(hitIdx)) {
            return this.selectedMultiIndices;
        }
        return [hitIdx];
    }

    private paintBoxSelectionOverlay() {
        if (!this.isBoxSelecting) return;
        const box = this.currentBoxSelection();
        if (!box) return;
        const corners = [
            new Vec2(box.x, box.y),
            new Vec2(box.x2, box.y),
            new Vec2(box.x2, box.y2),
            new Vec2(box.x, box.y2),
        ];
        const layer = this.renderer.start_dynamic_layer("selection-box");
        // Fill: Semi-transparent light blue
        layer.geometry.add_polygon(corners, 0.44, 0.62, 0.95, 0.15);
        // Outline: Solid light blue
        layer.geometry.add_polyline([...corners, corners[0]!.copy()], 0.1, 0.44, 0.62, 0.95, 0.8);
        this.renderer.commit_dynamic_layer(layer);
    }

    private updateHoverGroup(worldPos: Vec2) {
        let nextHoverId: string | null = null;
        let nextHoverFp = -1;
        if (this.model && !this.singleOverrideMode) {
            const candidateIndices = this.footprintIndex.queryPoint(worldPos);
            for (let i = candidateIndices.length - 1; i >= 0; i--) {
                const idx = candidateIndices[i]!;
                const bbox = this.footprintBBoxes[idx] ?? footprintBBox(this.model.footprints[idx]!);
                if (bbox.contains_point(worldPos)) {
                    // Preserve the exact footprint under cursor, even if it belongs
                    // to a group, so click/drag behavior stays precise for multi-select.
                    nextHoverFp = idx;
                    const groupId = this.groupIdByFpIndex.get(idx) ?? null;
                    if (groupId) {
                        nextHoverId = groupId;
                    }
                    break;
                }
            }

            if (nextHoverId === null && nextHoverFp === -1) {
                // Check graphic-only groups (no footprint members) by bounding box.
                for (const [groupId, group] of this.groupsById) {
                    if (group.memberIndices.length === 0 && group.graphicBBox) {
                        const hit = group.graphicBBox.contains_point(worldPos);
                        if (hit) {
                            nextHoverId = groupId;
                            break;
                        }
                    }
                }
            }
        }
        if (nextHoverId === this.hoveredGroupId && nextHoverFp === this.hoveredFpIndex) return;
        this.hoveredGroupId = nextHoverId;
        this.hoveredFpIndex = nextHoverFp;
        this.repaintWithSelection();
    }

    private connectWebSocket() {
        this.client.connect((msg) => {
            if (msg.type === "layout_updated" && msg.model) {
                this.applyModel(msg.model);
                return;
            }
            if (msg.type === "layout_delta" && msg.delta) {
                this.applyDelta(msg.delta);
            }
        });
    }

    private getIndexedHitIdx(worldPos: Vec2): number {
        if (!this.model) return -1;
        const candidateIndices = this.footprintIndex.queryPoint(worldPos);
        for (let i = candidateIndices.length - 1; i >= 0; i--) {
            const idx = candidateIndices[i]!;
            const bbox = this.footprintBBoxes[idx] ?? footprintBBox(this.model.footprints[idx]!);
            if (bbox.contains_point(worldPos)) {
                return idx;
            }
        }
        return -1;
    }

    private setupMouseHandlers() {
        this.canvas.addEventListener("mousedown", (e: MouseEvent) => {
            if (e.button !== 0) return;

            const viewport = this.getCanvasViewportMetrics();
            this.lastMouseScreen = new Vec2(e.clientX - viewport.left, e.clientY - viewport.top);
            const worldPos = this.camera.screen_to_world(this.lastMouseScreen);

            if (!this.model) return;

            if (e.shiftKey) {
                this.clearDragState();
                this.isBoxSelecting = true;
                this.boxSelectStartWorld = worldPos;
                this.boxSelectCurrentWorld = worldPos;
                this.repaintWithSelection();
                return;
            }
            this.pendingDrag = null;

            let hitIdx = -1;
            if (this.hoveredFpIndex >= 0 && this.hoveredFpIndex < this.model.footprints.length) {
                const hoveredBBox = this.footprintBBoxes[this.hoveredFpIndex] ?? footprintBBox(this.model.footprints[this.hoveredFpIndex]!);
                if (hoveredBBox.contains_point(worldPos)) {
                    hitIdx = this.hoveredFpIndex;
                }
            }
            if (hitIdx < 0) {
                hitIdx = this.getIndexedHitIdx(worldPos);
            }

            if (hitIdx >= 0) {
                const keepMultiSelection = this.selectionMode === "multi" && this.selectedMultiIndices.includes(hitIdx);
                if (!keepMultiSelection) {
                    const hitGroupId = this.groupIdByFpIndex.get(hitIdx) ?? null;
                    if (!this.singleOverrideMode && hitGroupId) {
                        this.setGroupSelection(hitGroupId);
                    } else {
                        this.setSingleSelection(hitIdx, false);
                    }
                }

                const dragTargets = this.selectedIndicesForDrag(hitIdx);
                const isGroupDrag = this.selectionMode === "group";
                const dragTrackUuids = isGroupDrag ? (this.selectedGroup()?.trackMemberUuids ?? []) : [];
                const dragViaUuids = isGroupDrag ? (this.selectedGroup()?.viaMemberUuids ?? []) : [];
                const dragDrawingUuids = isGroupDrag ? (this.selectedGroup()?.graphicMemberUuids ?? []) : [];
                const dragTextUuids = isGroupDrag ? (this.selectedGroup()?.textMemberUuids ?? []) : [];
                const dragZoneUuids = isGroupDrag ? (this.selectedGroup()?.zoneMemberUuids ?? []) : [];
                this.setPendingDrag(worldPos, this.lastMouseScreen, dragTargets, dragTrackUuids, dragViaUuids, dragDrawingUuids, dragTextUuids, dragZoneUuids);
                this.repaintWithSelection();
            } else {
                // Check if clicking inside a graphic-only group's bounding box.
                let hitGraphicGroupId: string | null = null;
                if (!this.singleOverrideMode && this.hoveredGroupId) {
                    const hoveredGroup = this.groupsById.get(this.hoveredGroupId);
                    if (hoveredGroup && hoveredGroup.memberIndices.length === 0 && hoveredGroup.graphicBBox?.contains_point(worldPos)) {
                        hitGraphicGroupId = this.hoveredGroupId;
                    }
                }
                if (!this.singleOverrideMode && !hitGraphicGroupId) {
                    for (const [groupId, group] of this.groupsById) {
                        if (group.memberIndices.length === 0 && group.graphicBBox?.contains_point(worldPos)) {
                            hitGraphicGroupId = groupId;
                            break;
                        }
                    }
                }
                if (hitGraphicGroupId) {
                    this.setGroupSelection(hitGraphicGroupId);
                    const group = this.groupsById.get(hitGraphicGroupId)!;
                    this.setPendingDrag(worldPos, this.lastMouseScreen, [], [], [], group.graphicMemberUuids, group.textMemberUuids, group.zoneMemberUuids);
                    this.repaintWithSelection();
                } else {
                    this.pendingDrag = null;
                    this.clearSelection(true);
                    this.repaintWithSelection();
                }
            }
        });

        this.canvas.addEventListener("dblclick", (e: MouseEvent) => {
            if (e.button !== 0 || !this.model) return;
            const viewport = this.getCanvasViewportMetrics();
            const screenPos = new Vec2(e.clientX - viewport.left, e.clientY - viewport.top);
            const worldPos = this.camera.screen_to_world(screenPos);
            const hitIdx = this.getIndexedHitIdx(worldPos);
            if (hitIdx < 0) return;
            this.setSingleSelection(hitIdx, true);
            this.repaintWithSelection();
        });

        this.canvas.addEventListener("mousemove", (e: MouseEvent) => {
            const viewport = this.getCanvasViewportMetrics();
            this.lastMouseScreen = new Vec2(e.clientX - viewport.left, e.clientY - viewport.top);

            if (this.onMouseMoveCallback) {
                const worldPos = this.camera.screen_to_world(this.lastMouseScreen);
                this.onMouseMoveCallback(worldPos.x, worldPos.y);
            }

            if (!this.model) return;
            const worldPos = this.camera.screen_to_world(this.lastMouseScreen);

            if (this.isBoxSelecting) {
                this.boxSelectCurrentWorld = worldPos;
                this.repaintWithSelection();
                return;
            }

            if (!this.isDragging) {
                if (this.pendingDrag) {
                    if (!this.maybeStartPendingDrag(worldPos, this.lastMouseScreen)) {
                        return;
                    }
                } else {
                    this.updateHoverGroup(worldPos);
                    return;
                }
            }

            if (!this.dragStartWorld) return;
            const delta = this.applySnap(worldPos.sub(this.dragStartWorld));

            // GPU-accelerated drag: update layer transforms instead of re-tessellating
            const trans = Matrix3.translation(delta.x, delta.y);
            for (const layer of this.renderer.dynamicLayers) {
                layer.transform = trans;
            }
            this.requestRedraw();
        });

        window.addEventListener("mouseup", async (e: MouseEvent) => {
            if (e.button !== 0) return;

            if (this.isBoxSelecting) {
                this.singleOverrideMode = false;
                const selectionBox = this.currentBoxSelection();
                if (this.model && selectionBox) {
                    const selected = hitTestFootprintsInBox(selectionBox, this.model.footprints);
                    if (selected.length > 0) {
                        this.setMultiSelection(selected);
                    } else {
                        this.clearSelection(false);
                    }
                }
                this.clearBoxSelectionState();
                this.repaintWithSelection();
                return;
            }

            if (this.pendingDrag) {
                this.pendingDrag = null;
                setTimeout(() => this.repaintWithSelection(), 0);
                return;
            }

            if (!this.isDragging) return;
            
            const viewport = this.getCanvasViewportMetrics();
            const worldPos = this.camera.screen_to_world(new Vec2(e.clientX - viewport.left, e.clientY - viewport.top));
            const delta = this.applySnap(worldPos.sub(this.dragStartWorld!));
            const dx = delta.x;
            const dy = delta.y;

            if (!this.model || !this.dragStartWorld) {
                this.isDragging = false;
                this.restorePostDragRendering();
                this.clearDragState();
                this.repaintWithSelection();
                return;
            }

            if (!Number.isFinite(dx) || !Number.isFinite(dy)) {
                console.warn("Ignoring drag move with invalid delta", { dx, dy });
                this.isDragging = false;
                this.restorePostDragRendering();
                this.clearDragState();
                this.repaintWithSelection();
                return;
            }

            const isNoop = Math.abs(dx) < 0.001 && Math.abs(dy) < 0.001;
            const uuids = this.selectedUuids();

            if (isNoop) {
                this.isDragging = false;
                this.restorePostDragRendering();
                this.clearDragState();
                this.repaintWithSelection();
                return;
            }

            const movePromise = uuids.length > 0
                ? this.executeAction({ command: "move", uuids, dx, dy })
                : null;

            // Preserve immediate drop position locally while server action is pending.
            this.isDragging = false;
            this.applyDragDelta(dx, dy);
            this.rebuildSpatialIndexes();
            const droppedTransform = Matrix3.translation(dx, dy);
            for (const layer of this.renderer.dynamicLayers) {
                layer.transform = droppedTransform;
            }
            this.clearDragState();
            this.repaintWithSelection();

            if (movePromise) {
                void movePromise.then((ok) => {
                    if (!ok) {
                        this.restorePostDragRendering();
                        this.repaintWithSelection();
                    }
                });
            } else {
                this.restorePostDragRendering();
                this.repaintWithSelection();
            }
        });
    }

    private setupKeyboardHandlers() {
        window.addEventListener("keydown", async (e: KeyboardEvent) => {
            if (e.key === "Escape") {
                if (this.isDragging) {
                    this.revertDragPositions();
                    this.restorePostDragRendering();
                }
                this.pendingDrag = null;
                this.clearSelection(true);
                this.repaintWithSelection();
                return;
            }

            // R — rotate selected footprint by 90 degrees
            if (e.key === "r" || e.key === "R") {
                if (e.ctrlKey || e.metaKey || e.altKey) return;
                await this.rotateSelection(90);
                return;
            }

            // F — flip selected footprint
            if (e.key === "f" || e.key === "F") {
                if (e.ctrlKey || e.metaKey || e.altKey) return;
                await this.flipSelection();
                return;
            }

            // Ctrl+Z — undo
            if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
                e.preventDefault();
                await this.executeAction({ command: "undo" });
                return;
            }

            // Ctrl+Shift+Z or Ctrl+Y — redo
            if (((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z" && e.shiftKey) ||
                ((e.ctrlKey || e.metaKey) && e.key === "y")) {
                e.preventDefault();
                await this.executeAction({ command: "redo" });
                return;
            }
        });
    }

    private setupResizeHandler() {
        window.addEventListener("resize", () => {
            this.requestRedraw();
        });
    }

    private async rotateSelection(deltaDegrees: number) {
        if (!this.model) return;
        const uuids = this.selectedUuids();
        if (uuids.length > 0) {
            await this.executeAction({ command: "rotate", uuids, delta_degrees: deltaDegrees });
        }
    }

    private async flipSelection() {
        if (!this.model) return;
        const uuids = this.selectedUuids();
        if (uuids.length > 0) {
            await this.executeAction({ command: "flip", uuids });
        }
    }

    private async executeAction(
        action: ActionCommand,
    ): Promise<boolean> {
        const actionId = `a${Date.now()}_${++this.actionNonce}`;
        const taggedAction: ActionCommand = { ...action, client_action_id: actionId };
        this.pendingActionRequests += 1;
        if (this.pendingActionRequests === 1 && this.onActionBusyChanged) {
            this.onActionBusyChanged(true);
        }
        let ok = false;
        try {
            const data = await this.client.executeAction(taggedAction);
            if (data.status === "error") {
                console.warn(`Action ${action.command} failed (${data.code}): ${data.message ?? "unknown error"}`);
            } else {
                ok = true;
            }
        } catch (err) {
            console.error("Failed to execute action:", err);
        } finally {
            if (this.pendingActionRequests > 0) {
                this.pendingActionRequests -= 1;
            } else {
                this.pendingActionRequests = 0;
            }
            if (this.pendingActionRequests === 0 && this.onActionBusyChanged) {
                this.onActionBusyChanged(false);
            }
        }
        return ok;
    }

    // --- Layer visibility ---

    setLayerVisible(layer: string, visible: boolean) {
        if (visible) {
            this.hiddenLayers.delete(layer);
        } else {
            this.hiddenLayers.add(layer);
        }
        if (this.isObjectTypeLayer(layer)) {
            this.rebuildAfterObjectTypeVisibilityChange();
        } else {
            this.renderer.set_layer_visible(layer, visible);
        }
        this.paintDynamic();
        this.requestRedraw();
    }

    setLayersVisible(layers: string[], visible: boolean) {
        let objectTypeChanged = false;
        for (const layer of layers) {
            if (visible) {
                this.hiddenLayers.delete(layer);
            } else {
                this.hiddenLayers.add(layer);
            }
            if (this.isObjectTypeLayer(layer)) {
                objectTypeChanged = true;
            } else {
                this.renderer.set_layer_visible(layer, visible);
            }
        }
        if (objectTypeChanged) {
            this.rebuildAfterObjectTypeVisibilityChange();
        }
        this.paintDynamic();
        this.requestRedraw();
    }

    isLayerVisible(layer: string): boolean {
        return !this.hiddenLayers.has(layer);
    }

    private getLayerMap(): Map<string, LayerModel> {
        const layerById = new Map<string, LayerModel>();
        if (!this.model) return layerById;
        for (const layer of this.model.layers) {
            layerById.set(layer.id, layer);
        }
        return layerById;
    }

    getLayerModels(): LayerModel[] {
        if (!this.model) return [];
        return [...this.model.layers].sort((a, b) => {
            const orderDiff = a.panel_order - b.panel_order;
            if (orderDiff !== 0) return orderDiff;
            return a.id.localeCompare(b.id);
        });
    }

    getLayers(): string[] {
        return this.getLayerModels().map(layer => layer.id);
    }

    setOnLayersChanged(cb: () => void) {
        this.onLayersChanged = cb;
    }

    setOnMouseMove(cb: (x: number, y: number) => void) {
        this.onMouseMoveCallback = cb;
    }

    setOnActionBusyChanged(cb: (busy: boolean) => void) {
        this.onActionBusyChanged = cb;
        cb(this.pendingActionRequests > 0);
    }

    setSnapDelta(cb: ((dx: number, dy: number) => { dx: number; dy: number }) | null) {
        this.snapDelta = cb;
    }

    private applySnap(delta: Vec2): Vec2 {
        if (!this.snapDelta) return delta;
        const s = this.snapDelta(delta.x, delta.y);
        return new Vec2(s.dx, s.dy);
    }

    private repaintWithSelection() {
        this.dynamicDirty = true;
        this.requestRedraw();
    }

    private requestRedraw() {
        this.needsRedraw = true;
    }

    private drawTextOverlay() {
        if (!this.textCtx || !this.model) return;
        const viewport = this.getCanvasViewportMetrics();
        this.syncTextOverlayViewport(viewport);
        const visibleFpIndices = this.footprintIndex.query(this.camera.bbox);
        const layerMap = this.getLayerMap();

        if (!this.isDragging || !this.dragStartWorld || this.dragTargetIndices.length === 0) {
            renderTextOverlay(
                this.textCtx,
                this.model,
                this.camera,
                this.hiddenLayers,
                layerMap,
                viewport.width,
                viewport.height,
                visibleFpIndices,
                { clearCanvas: true },
            );
            return;
        }

        const draggedSet = new Set(this.dragTargetIndices);
        const staticVisible = visibleFpIndices.filter(index => !draggedSet.has(index));
        renderTextOverlay(
            this.textCtx,
            this.model,
            this.camera,
            this.hiddenLayers,
            layerMap,
            viewport.width,
            viewport.height,
            staticVisible,
            { clearCanvas: true },
        );

        const worldPos = this.camera.screen_to_world(this.lastMouseScreen);
        const delta = this.applySnap(worldPos.sub(this.dragStartWorld));
        renderTextOverlay(
            this.textCtx,
            this.model,
            this.camera,
            this.hiddenLayers,
            layerMap,
            viewport.width,
            viewport.height,
            this.dragTargetIndices,
            { clearCanvas: false, worldOffset: delta },
        );
    }

    private onRenderFrame() {
        if (!this.needsRedraw) return;
        this.needsRedraw = false;
        if (this.dynamicDirty) {
            this.paintDynamic();
        }
        const viewport = this.getCanvasViewportMetrics();
        this.camera.viewport_size = new Vec2(viewport.width, viewport.height);
        this.renderer.updateGrid(this.camera.bbox, 1.0);
        this.renderer.draw(this.camera.matrix);
        this.drawTextOverlay();
    }
}
