import { Vec2, BBox } from "./math";
import { Camera2 } from "./camera";
import { PanAndZoom } from "./pan-and-zoom";
import { Renderer } from "./webgl/renderer";
import { paintAll, paintGroupHalos, paintSelection, computeBBox } from "./painter";
import { hitTestFootprints, hitTestFootprintsInBox } from "./hit-test";
import { LayoutClient } from "./layout_client";
import { renderTextOverlay } from "./text_overlay";
import type { ActionCommand, LayerModel, RenderModel } from "./types";

type SelectionMode = "none" | "single" | "group" | "multi";

interface UiFootprintGroup {
    id: string;
    uuid: string | null;
    name: string | null;
    memberUuids: string[];
    memberIndices: number[];
}

export class Editor {
    private canvas: HTMLCanvasElement;
    private textOverlay: HTMLCanvasElement;
    private textCtx: CanvasRenderingContext2D | null;
    private renderer: Renderer;
    private camera: Camera2;
    private panAndZoom: PanAndZoom;
    private client: LayoutClient;
    private model: RenderModel | null = null;

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

    private isDragging = false;
    private dragStartWorld: Vec2 | null = null;
    private dragTargetIndices: number[] = [];
    private dragStartPositions: Map<number, { x: number; y: number }> | null = null;
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

    constructor(canvas: HTMLCanvasElement, baseUrl: string, apiPrefix = "/api", wsPath = "/ws") {
        this.canvas = canvas;
        this.textOverlay = this.createTextOverlay();
        this.textCtx = this.textOverlay.getContext("2d");
        this.renderer = new Renderer(canvas);
        this.camera = new Camera2();
        this.panAndZoom = new PanAndZoom(canvas, this.camera, () => this.requestRedraw());
        this.client = new LayoutClient(baseUrl, apiPrefix, wsPath);

        this.setupMouseHandlers();
        this.setupKeyboardHandlers();
        this.setupResizeHandler();
        window.addEventListener("beforeunload", () => this.client.disconnect());
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
                paintGroupHalos(this.renderer, this.model.footprints, hovered.memberIndices, "hover");
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
                paintGroupHalos(this.renderer, this.model.footprints, selectedGroup.memberIndices, "selected");
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
        this.groupsById.clear();
        this.groupIdByFpIndex.clear();
        if (!this.model) return;

        const indexByUuid = new Map<string, number>();
        for (let i = 0; i < this.model.footprints.length; i++) {
            const uuid = this.model.footprints[i]!.uuid;
            if (uuid) indexByUuid.set(uuid, i);
        }

        const rawGroups = this.model.footprint_groups;
        const usedIds = new Set<string>();
        for (let i = 0; i < rawGroups.length; i++) {
            const group = rawGroups[i]!;
            const memberIndices: number[] = [];
            const memberUuids: string[] = [];
            for (const memberUuid of group.member_uuids) {
                if (!memberUuid) continue;
                const fpIndex = indexByUuid.get(memberUuid);
                if (fpIndex === undefined) continue;
                memberIndices.push(fpIndex);
                memberUuids.push(memberUuid);
            }
            if (memberIndices.length < 2) continue;

            let idBase = group.uuid || group.name || `group-${i + 1}`;
            if (usedIds.has(idBase)) {
                let suffix = 2;
                while (usedIds.has(`${idBase}:${suffix}`)) suffix++;
                idBase = `${idBase}:${suffix}`;
            }
            usedIds.add(idBase);

            const uiGroup: UiFootprintGroup = {
                id: idBase,
                uuid: group.uuid,
                name: group.name,
                memberUuids,
                memberIndices,
            };
            this.groupsById.set(idBase, uiGroup);
            for (const fpIndex of memberIndices) {
                if (!this.groupIdByFpIndex.has(fpIndex)) {
                    this.groupIdByFpIndex.set(fpIndex, idBase);
                }
            }
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

    private selectedGroupMemberUuids(): string[] {
        const group = this.selectedGroup();
        return group ? group.memberUuids : [];
    }

    private selectedBatchUuids(): string[] {
        if (this.selectionMode === "group" && !this.singleOverrideMode) {
            return this.selectedGroupMemberUuids();
        }
        if (this.selectionMode === "multi" && this.selectedMultiIndices.length > 0) {
            return this.getSelectedMultiUuids();
        }
        return [];
    }

    private clearDragState() {
        this.isDragging = false;
        this.dragStartWorld = null;
        this.dragStartPositions = null;
        this.dragTargetIndices = [];
    }

    private clearBoxSelectionState() {
        this.isBoxSelecting = false;
        this.boxSelectStartWorld = null;
        this.boxSelectCurrentWorld = null;
    }

    private beginDragSelection(worldPos: Vec2, targetIndices: number[]) {
        const dragStartPositions = new Map<number, { x: number; y: number }>();
        for (const index of targetIndices) {
            const fp = this.model?.footprints[index];
            if (!fp) continue;
            dragStartPositions.set(index, { x: fp.at.x, y: fp.at.y });
        }
        if (dragStartPositions.size === 0) {
            return false;
        }
        this.isDragging = true;
        this.dragStartWorld = worldPos;
        this.dragTargetIndices = [...dragStartPositions.keys()];
        this.dragStartPositions = dragStartPositions;
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

            if (e.shiftKey) {
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

                const dragTargets = this.selectedIndicesForDrag(hitIdx);
                if (!this.beginDragSelection(worldPos, dragTargets)) {
                    this.repaintWithSelection();
                    return;
                }

                this.repaintWithSelection();
            } else {
                this.clearSelection(true);
                this.repaintWithSelection();
            }
        });

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

            if (!this.dragStartWorld || !this.dragStartPositions || this.dragTargetIndices.length === 0) {
                return;
            }

            const delta = worldPos.sub(this.dragStartWorld);
            for (const index of this.dragTargetIndices) {
                const fp = this.model.footprints[index];
                const start = this.dragStartPositions.get(index);
                if (!fp || !start) continue;
                fp.at.x = start.x + delta.x;
                fp.at.y = start.y + delta.y;
            }

            this.paint();
            this.requestRedraw();
        });

        window.addEventListener("mouseup", async (e: MouseEvent) => {
            if (e.button !== 0) return;

            if (this.isBoxSelecting) {
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

            if (!this.model || !this.dragStartPositions || this.dragTargetIndices.length === 0) {
                this.clearDragState();
                return;
            }

            const firstTarget = this.dragTargetIndices[0]!;
            const firstStart = this.dragStartPositions.get(firstTarget);
            const firstFp = this.model.footprints[firstTarget];
            if (!firstStart || !firstFp) {
                this.clearDragState();
                return;
            }

            const dx = firstFp.at.x - firstStart.x;
            const dy = firstFp.at.y - firstStart.y;
            const isNoop = Math.abs(dx) < 0.001 && Math.abs(dy) < 0.001;

            this.clearDragState();

            if (isNoop) return;

            const batchUuids = this.selectedBatchUuids();
            if (batchUuids.length > 0) {
                await this.executeAction({
                    command: "move_footprints",
                    uuids: batchUuids,
                    dx,
                    dy,
                });
                return;
            }

            if (this.selectionMode === "single" && this.selectedFpIndex >= 0) {
                const selectedFp = this.model.footprints[this.selectedFpIndex]!;
                if (!selectedFp.uuid) return;
                await this.executeAction({
                    command: "move_footprint",
                    uuid: selectedFp.uuid,
                    x: selectedFp.at.x,
                    y: selectedFp.at.y,
                    r: selectedFp.at.r || null,
                });
            }
        });
    }

    private setupKeyboardHandlers() {
        window.addEventListener("keydown", async (e: KeyboardEvent) => {
            if (e.key === "Escape") {
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

    private async rotateSelection(deltaDegrees: number) {
        if (!this.model) return;
        const batchUuids = this.selectedBatchUuids();
        if (batchUuids.length > 0) {
            await this.executeAction({
                command: "rotate_footprints",
                uuids: batchUuids,
                delta_degrees: deltaDegrees,
            });
            return;
        }
        if (this.selectionMode === "single" && this.selectedFpIndex >= 0) {
            const fp = this.model.footprints[this.selectedFpIndex]!;
            if (!fp.uuid) return;
            await this.executeAction({
                command: "rotate_footprint",
                uuid: fp.uuid,
                delta_degrees: deltaDegrees,
            });
        }
    }

    private async flipSelection() {
        if (!this.model) return;
        const batchUuids = this.selectedBatchUuids();
        if (batchUuids.length > 0) {
            await this.executeAction({
                command: "flip_footprints",
                uuids: batchUuids,
            });
            return;
        }
        if (this.selectionMode === "single" && this.selectedFpIndex >= 0) {
            const fp = this.model.footprints[this.selectedFpIndex]!;
            if (!fp.uuid) return;
            await this.executeAction({
                command: "flip_footprint",
                uuid: fp.uuid,
            });
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

    private async serverAction(path: string) {
        try {
            const data = await this.client.post(path);
            if (data.status === "error") {
                console.warn(`${path} failed (${data.code}): ${data.message ?? "unknown error"}`);
            }
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
