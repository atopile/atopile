import { Vec2, BBox } from "./math";
import { Camera2 } from "./camera";
import { PanAndZoom } from "./pan-and-zoom";
import { Renderer } from "./webgl/renderer";
import { paintAll, paintGroupBBox, paintGroupHalos, paintBBoxOutline, paintSelection, computeBBox } from "./painter";
import { hitTestFootprints, hitTestFootprintsInBox } from "./hit-test";
import { LayoutClient } from "./layout_client";
import { renderTextOverlay } from "./text_overlay";
import { RenderLoop } from "./render_loop";
import { buildGroupIndex, type UiFootprintGroup } from "./footprint_groups";
import type { ActionCommand, DrawingModel, LayerModel, RenderModel, ZoneModel } from "./types";

type SelectionMode = "none" | "single" | "group" | "multi";

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

export interface EditorOptions {
    readOnly?: boolean;
    container?: HTMLElement;
}

export class Editor {
    private canvas: HTMLCanvasElement;
    private textOverlay: HTMLCanvasElement;
    private textCtx: CanvasRenderingContext2D | null;
    private renderer: Renderer;
    private camera: Camera2;
    /* @internal */ panAndZoom: PanAndZoom;
    private client: LayoutClient;
    private renderLoop: RenderLoop;
    private model: RenderModel | null = null;
    private readonly readOnly: boolean;
    private readonly container: HTMLElement | null;

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
    private isBoxSelecting = false;
    private boxSelectStartWorld: Vec2 | null = null;
    private boxSelectCurrentWorld: Vec2 | null = null;
    private needsRedraw = true;

    // Layer visibility
    private hiddenLayers: Set<string> = new Set();
    private defaultLayerVisibilityApplied = new Set<string>();
    private onLayersChanged: (() => void) | null = null;

    // Track current mouse position
    private lastMouseScreen: Vec2 = new Vec2(0, 0);

    // Mouse coordinate callback
    private onMouseMoveCallback: ((x: number, y: number) => void) | null = null;

    // External selection callbacks
    onSelectionChange: ((selectedIndices: number[]) => void) | null = null;
    onModelLoad: ((model: RenderModel) => void) | null = null;

    constructor(canvas: HTMLCanvasElement, baseUrl: string, apiPrefix = "/api", wsPath = "/ws", options?: EditorOptions) {
        this.canvas = canvas;
        this.readOnly = options?.readOnly ?? false;
        this.container = options?.container ?? null;
        this.textOverlay = this.createTextOverlay();
        this.textCtx = this.textOverlay.getContext("2d");
        this.renderer = new Renderer(canvas);
        this.camera = new Camera2();
        this.panAndZoom = new PanAndZoom(canvas, this.camera, () => this.requestRedraw());
        this.client = new LayoutClient(baseUrl, apiPrefix, wsPath);
        this.renderLoop = new RenderLoop(() => this.onRenderFrame());

        this.setupMouseHandlers();
        if (!this.readOnly) {
            this.setupKeyboardHandlers();
        }
        this.setupResizeHandler();
        window.addEventListener("beforeunload", () => {
            this.renderLoop.stop();
            this.client.disconnect();
        });
        this.renderer.setup();
        this.renderLoop.start();
    }

    private createTextOverlay(): HTMLCanvasElement {
        if (this.container) {
            const overlay = document.createElement("canvas");
            overlay.style.position = "absolute";
            overlay.style.top = "0";
            overlay.style.left = "0";
            overlay.style.width = "100%";
            overlay.style.height = "100%";
            overlay.style.pointerEvents = "none";
            overlay.style.zIndex = "9";
            this.container.appendChild(overlay);
            return overlay;
        }

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
        this.restoreSelection(prevSelectedUuid, prevSelectedMultiUuids, prevSelectedGroupId, prevSingleOverride);
        this.applyDefaultLayerVisibility();
        this.paint();

        this.camera.viewport_size = new Vec2(this.canvas.clientWidth, this.canvas.clientHeight);
        if (fitToView) {
            this.camera.bbox = computeBBox(this.model);
        }
        this.requestRedraw();
        if (this.onLayersChanged) this.onLayersChanged();
        if (this.onModelLoad) this.onModelLoad(this.model);
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

    private paint() {
        if (!this.model) return;
        paintAll(this.renderer, this.model, this.hiddenLayers);

        if (!this.singleOverrideMode && this.hoveredGroupId && this.hoveredGroupId !== this.selectedGroupId) {
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

    private notifySelectionChanged(): void {
        this.client.notifySelection(this.selectedUuids()).catch(() => {});
        if (this.onSelectionChange) {
            let indices: number[];
            if (this.selectionMode === "single" && this.selectedFpIndex >= 0) {
                indices = [this.selectedFpIndex];
            } else if (this.selectionMode === "multi") {
                indices = [...this.selectedMultiIndices];
            } else if (this.selectionMode === "group" && this.selectedGroupId) {
                const group = this.groupsById.get(this.selectedGroupId);
                indices = group ? [...group.memberIndices] : [];
            } else {
                indices = [];
            }
            this.onSelectionChange(indices);
        }
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
        this.notifySelectionChanged();
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
        this.notifySelectionChanged();
    }

    private setGroupSelection(groupId: string) {
        this.selectionMode = "group";
        this.selectedGroupId = groupId;
        this.selectedFpIndex = -1;
        this.selectedMultiIndices = [];
        this.singleOverrideMode = false;
        this.notifySelectionChanged();
    }

    private clearSelection(exitSingleOverride = false) {
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
        this.notifySelectionChanged();
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
        return true;
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
        const layer = this.renderer.start_layer("selection-box");
        layer.geometry.add_polygon(corners, 0.44, 0.62, 0.95, 0.12);
        layer.geometry.add_polyline([...corners, corners[0]!.copy()], 0.1, 0.44, 0.62, 0.95, 0.55);
        this.renderer.end_layer();
    }

    private updateHoverGroup(worldPos: Vec2) {
        let nextHoverId: string | null = null;
        let nextHoverFp = -1;
        if (this.model && !this.singleOverrideMode) {
            const hitIndex = hitTestFootprints(worldPos, this.model.footprints);
            if (hitIndex >= 0) {
                const groupId = this.groupIdByFpIndex.get(hitIndex) ?? null;
                if (groupId) {
                    nextHoverId = groupId;
                } else {
                    nextHoverFp = hitIndex;
                }
            } else {
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
        this.client.connect((model) => this.applyModel(model));
    }

    private setupMouseHandlers() {
        this.canvas.addEventListener("mousedown", (e: MouseEvent) => {
            if (e.button !== 0) return;

            const rect = this.canvas.getBoundingClientRect();
            const screenPos = new Vec2(e.clientX - rect.left, e.clientY - rect.top);
            const worldPos = this.camera.screen_to_world(screenPos);

            if (!this.model) return;

            if (!this.readOnly && e.shiftKey) {
                this.clearDragState();
                this.isBoxSelecting = true;
                this.boxSelectStartWorld = worldPos;
                this.boxSelectCurrentWorld = worldPos;
                this.repaintWithSelection();
                return;
            }

            const hitIdx = hitTestFootprints(worldPos, this.model.footprints);

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

                if (!this.readOnly) {
                    const dragTargets = this.selectedIndicesForDrag(hitIdx);
                    const isGroupDrag = this.selectionMode === "group";
                    const dragTrackUuids = isGroupDrag ? (this.selectedGroup()?.trackMemberUuids ?? []) : [];
                    const dragViaUuids = isGroupDrag ? (this.selectedGroup()?.viaMemberUuids ?? []) : [];
                    const dragDrawingUuids = isGroupDrag ? (this.selectedGroup()?.graphicMemberUuids ?? []) : [];
                    const dragTextUuids = isGroupDrag ? (this.selectedGroup()?.textMemberUuids ?? []) : [];
                    const dragZoneUuids = isGroupDrag ? (this.selectedGroup()?.zoneMemberUuids ?? []) : [];
                    if (!this.beginDragSelection(worldPos, dragTargets, dragTrackUuids, dragViaUuids, dragDrawingUuids, dragTextUuids, dragZoneUuids)) {
                        this.repaintWithSelection();
                        return;
                    }
                }

                this.repaintWithSelection();
            } else {
                // Check if clicking inside a graphic-only group's bounding box.
                let hitGraphicGroupId: string | null = null;
                if (!this.singleOverrideMode) {
                    for (const [groupId, group] of this.groupsById) {
                        if (group.memberIndices.length === 0 && group.graphicBBox?.contains_point(worldPos)) {
                            hitGraphicGroupId = groupId;
                            break;
                        }
                    }
                }
                if (hitGraphicGroupId) {
                    this.setGroupSelection(hitGraphicGroupId);
                    if (!this.readOnly) {
                        const group = this.groupsById.get(hitGraphicGroupId)!;
                        if (!this.beginDragSelection(worldPos, [], [], [], group.graphicMemberUuids, group.textMemberUuids, group.zoneMemberUuids)) {
                            this.repaintWithSelection();
                            return;
                        }
                    }
                    this.repaintWithSelection();
                } else {
                    this.clearSelection(true);
                    this.repaintWithSelection();
                }
            }
        });

        if (!this.readOnly) {
            this.canvas.addEventListener("dblclick", (e: MouseEvent) => {
                if (e.button !== 0 || !this.model) return;
                const rect = this.canvas.getBoundingClientRect();
                const screenPos = new Vec2(e.clientX - rect.left, e.clientY - rect.top);
                const worldPos = this.camera.screen_to_world(screenPos);
                const hitIdx = hitTestFootprints(worldPos, this.model.footprints);
                if (hitIdx < 0) return;
                this.setSingleSelection(hitIdx, true);
                this.repaintWithSelection();
            });
        }

        this.canvas.addEventListener("mousemove", (e: MouseEvent) => {
            const rect = this.canvas.getBoundingClientRect();
            this.lastMouseScreen = new Vec2(e.clientX - rect.left, e.clientY - rect.top);

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
                this.updateHoverGroup(worldPos);
                return;
            }

            if (!this.dragStartWorld) return;
            const hasAnyTargets =
                this.dragTargetIndices.length > 0
                || this.dragTargetTrackUuids.length > 0
                || this.dragTargetViaUuids.length > 0
                || this.dragTargetDrawingUuids.length > 0
                || this.dragTargetTextUuids.length > 0
                || this.dragTargetZoneUuids.length > 0;
            if (!hasAnyTargets) return;

            const delta = worldPos.sub(this.dragStartWorld);
            for (const index of this.dragTargetIndices) {
                const fp = this.model.footprints[index];
                const start = this.dragStartPositions?.get(index);
                if (!fp || !start) continue;
                fp.at.x = start.x + delta.x;
                fp.at.y = start.y + delta.y;
            }
            if (this.dragStartTrackPositions) {
                for (const uuid of this.dragTargetTrackUuids) {
                    const idx = this.trackIndexByUuid.get(uuid);
                    if (idx === undefined) continue;
                    const track = this.model.tracks[idx];
                    const start = this.dragStartTrackPositions.get(uuid);
                    if (!track || !start) continue;
                    track.start.x = start.sx + delta.x;
                    track.start.y = start.sy + delta.y;
                    track.end.x = start.ex + delta.x;
                    track.end.y = start.ey + delta.y;
                    if (track.mid && start.mx !== undefined && start.my !== undefined) {
                        track.mid.x = start.mx + delta.x;
                        track.mid.y = start.my + delta.y;
                    }
                }
            }
            if (this.dragStartViaPositions) {
                for (const uuid of this.dragTargetViaUuids) {
                    const idx = this.viaIndexByUuid.get(uuid);
                    if (idx === undefined) continue;
                    const via = this.model.vias[idx];
                    const start = this.dragStartViaPositions.get(uuid);
                    if (!via || !start) continue;
                    via.at.x = start.x + delta.x;
                    via.at.y = start.y + delta.y;
                }
            }
            if (this.dragStartDrawingCoords) {
                for (const uuid of this.dragTargetDrawingUuids) {
                    const idx = this.drawingIndexByUuid.get(uuid);
                    if (idx === undefined) continue;
                    const drawing = this.model.drawings[idx];
                    const coords = this.dragStartDrawingCoords.get(uuid);
                    if (!drawing || !coords) continue;
                    applyDeltaToDrawing(drawing, coords, delta.x, delta.y);
                }
            }
            if (this.dragStartTextPositions) {
                for (const uuid of this.dragTargetTextUuids) {
                    const idx = this.textIndexByUuid.get(uuid);
                    if (idx === undefined) continue;
                    const text = this.model.texts[idx];
                    const start = this.dragStartTextPositions.get(uuid);
                    if (!text || !start) continue;
                    text.at.x = start.x + delta.x;
                    text.at.y = start.y + delta.y;
                }
            }
            if (this.dragStartZoneCoords) {
                for (const uuid of this.dragTargetZoneUuids) {
                    const idx = this.zoneIndexByUuid.get(uuid);
                    if (idx === undefined) continue;
                    const zone = this.model.zones[idx];
                    const coords = this.dragStartZoneCoords.get(uuid);
                    if (!zone || !coords) continue;
                    applyDeltaToZone(zone, coords, delta.x, delta.y);
                }
            }

            this.paint();
            this.requestRedraw();
        });

        window.addEventListener("mouseup", async (e: MouseEvent) => {
            if (e.button !== 0) return;

            if (this.isBoxSelecting) {
                // Box selection is a new selection gesture — always exit
                // single-override mode so subsequent clicks respect groups.
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

            if (!this.isDragging) return;
            this.isDragging = false;

            if (!this.model || !this.dragStartWorld) {
                this.clearDragState();
                return;
            }

            let dx = 0, dy = 0;

            if (this.dragTargetIndices.length > 0 && this.dragStartPositions) {
                // Compute delta from first footprint's movement.
                const firstTarget = this.dragTargetIndices[0]!;
                const firstStart = this.dragStartPositions.get(firstTarget);
                const firstFp = this.model.footprints[firstTarget];
                if (!firstStart || !firstFp) {
                    this.clearDragState();
                    return;
                }
                dx = firstFp.at.x - firstStart.x;
                dy = firstFp.at.y - firstStart.y;
            } else if (this.dragTargetDrawingUuids.length > 0 && this.dragStartDrawingCoords) {
                // Graphic-only group: derive delta from the first drawing's displacement.
                const firstUuid = this.dragTargetDrawingUuids[0]!;
                const firstCoords = this.dragStartDrawingCoords.get(firstUuid);
                const idx = this.drawingIndexByUuid.get(firstUuid);
                const drawing = idx !== undefined ? this.model.drawings[idx] : undefined;
                if (!firstCoords || !drawing) {
                    this.clearDragState();
                    return;
                }
                // Current x is coords[0] + applied_delta; original x is coords[0].
                const currentX = drawing.type === "line" ? drawing.start.x
                    : drawing.type === "arc" ? drawing.start.x
                    : drawing.type === "circle" ? drawing.center.x
                    : drawing.type === "rect" ? drawing.start.x
                    : drawing.type === "polygon" || drawing.type === "curve" ? (drawing.points[0]?.x ?? 0)
                    : 0;
                const currentY = drawing.type === "line" ? drawing.start.y
                    : drawing.type === "arc" ? drawing.start.y
                    : drawing.type === "circle" ? drawing.center.y
                    : drawing.type === "rect" ? drawing.start.y
                    : drawing.type === "polygon" || drawing.type === "curve" ? (drawing.points[0]?.y ?? 0)
                    : 0;
                dx = currentX - (firstCoords[0] ?? 0);
                dy = currentY - (firstCoords[1] ?? 0);
            } else {
                this.clearDragState();
                return;
            }

            const isNoop = Math.abs(dx) < 0.001 && Math.abs(dy) < 0.001;

            this.clearDragState();

            if (isNoop) return;

            const uuids = this.selectedUuids();
            if (uuids.length > 0) {
                await this.executeAction({ command: "move", uuids, dx, dy });
            }
        });
    }

    private setupKeyboardHandlers() {
        window.addEventListener("keydown", async (e: KeyboardEvent) => {
            if (e.key === "Escape") {
                if (this.isDragging) {
                    this.revertDragPositions();
                }
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

    private async executeAction(action: ActionCommand) {
        try {
            const data = await this.client.executeAction(action);
            if (data.status === "error") {
                console.warn(`Action ${action.command} failed (${data.code}): ${data.message ?? "unknown error"}`);
            }
            if (data.model) this.applyModel(data.model);
        } catch (err) {
            console.error("Failed to execute action:", err);
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

    getModel(): RenderModel | null {
        return this.model;
    }

    selectFootprintsByIndices(indices: number[]): void {
        if (indices.length === 0) {
            this.clearSelection(true);
        } else if (indices.length === 1) {
            this.setSingleSelection(indices[0]!, false);
        } else {
            this.setMultiSelection(indices);
        }
        this.repaintWithSelection();
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
        renderTextOverlay(
            this.textCtx,
            this.model,
            this.camera,
            this.hiddenLayers,
            this.getLayerMap(),
            this.canvas.clientWidth,
            this.canvas.clientHeight,
        );
    }

    private onRenderFrame() {
        if (!this.needsRedraw) return;
        this.needsRedraw = false;
        this.camera.viewport_size = new Vec2(this.canvas.clientWidth, this.canvas.clientHeight);
        this.renderer.updateGrid(this.camera.bbox, 1.0);
        this.renderer.draw(this.camera.matrix);
        this.drawTextOverlay();
    }
}
