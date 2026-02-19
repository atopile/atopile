import { Vec2 } from "./math";
import { Camera2 } from "./camera";
import { PanAndZoom } from "./pan-and-zoom";
import { Renderer } from "./webgl/renderer";
import { paintAll, paintGroupHalos, paintSelection, computeBBox } from "./painter";
import { hitTestFootprints } from "./hit-test";
import { getLayerColor } from "./colors";
import type { RenderModel } from "./types";
import { layoutKicadStrokeLine } from "./kicad_stroke_font";
import { sortLayerNames } from "./layer_order";

const DEG_TO_RAD = Math.PI / 180;

function expandLayerName(layerName: string, concreteLayers: Set<string>): string[] {
    if (!layerName) return [];
    if (layerName.includes("*")) {
        const suffixIdx = layerName.indexOf(".");
        const suffix = suffixIdx >= 0 ? layerName.substring(suffixIdx) : "";
        const expanded = [...concreteLayers].filter(l => l.endsWith(suffix));
        if (expanded.length > 0) return expanded;
        if (suffix === ".Cu") return ["F.Cu", "B.Cu"];
        if (suffix === ".Nets" || suffix === ".PadNumbers" || suffix === ".Drill") {
            return [`F${suffix}`, `B${suffix}`];
        }
        return [];
    }
    if (layerName.includes("&")) {
        const dotIdx = layerName.indexOf(".");
        if (dotIdx < 0) return [];
        const prefixes = layerName.substring(0, dotIdx).split("&");
        const suffix = layerName.substring(dotIdx);
        return prefixes.map(p => `${p}${suffix}`);
    }
    return [layerName];
}

type SelectionMode = "none" | "single" | "group";

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
    private model: RenderModel | null = null;
    private baseUrl: string;
    private apiPrefix: string;
    private wsPath: string;
    private ws: WebSocket | null = null;

    // Selection & interaction state
    private selectionMode: SelectionMode = "none";
    private selectedFpIndex = -1;
    private selectedGroupId: string | null = null;
    private hoveredGroupId: string | null = null;
    private singleOverrideMode = false;
    private groupsById = new Map<string, UiFootprintGroup>();
    private groupIdByFpIndex = new Map<number, string>();

    private isDragging = false;
    private dragStartWorld: Vec2 | null = null;
    private dragTargetIndices: number[] = [];
    private dragStartPositions: Map<number, { x: number; y: number }> | null = null;
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
        const prevSelectedUuid = this.getSelectedSingleUuid();
        const prevSelectedGroupId = this.selectedGroupId;
        const prevSingleOverride = this.singleOverrideMode;

        this.model = model;
        this.rebuildGroupIndex();
        this.restoreSelection(prevSelectedUuid, prevSelectedGroupId, prevSingleOverride);
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

        if (!this.singleOverrideMode && this.hoveredGroupId && this.hoveredGroupId !== this.selectedGroupId) {
            const hovered = this.groupsById.get(this.hoveredGroupId);
            if (hovered) {
                paintGroupHalos(this.renderer, this.model.footprints, hovered.memberIndices, "hover");
            }
        }

        if (!this.singleOverrideMode && this.selectedGroupId) {
            const selectedGroup = this.groupsById.get(this.selectedGroupId);
            if (selectedGroup) {
                paintGroupHalos(this.renderer, this.model.footprints, selectedGroup.memberIndices, "selected");
            }
        }

        if (this.selectionMode === "single" && this.selectedFpIndex >= 0 && this.selectedFpIndex < this.model.footprints.length) {
            paintSelection(this.renderer, this.model.footprints[this.selectedFpIndex]!);
        }
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

        const rawGroups = this.model.footprint_groups ?? [];
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

    private restoreSelection(
        prevSelectedUuid: string | null,
        prevSelectedGroupId: string | null,
        prevSingleOverride: boolean,
    ) {
        this.selectionMode = "none";
        this.selectedFpIndex = -1;
        this.selectedGroupId = null;
        this.hoveredGroupId = null;
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
        if (enterOverride) {
            this.singleOverrideMode = true;
        } else if (!this.groupIdByFpIndex.has(index)) {
            this.singleOverrideMode = false;
        }
    }

    private setGroupSelection(groupId: string) {
        this.selectionMode = "group";
        this.selectedGroupId = groupId;
        this.selectedFpIndex = -1;
        this.singleOverrideMode = false;
    }

    private clearSelection(exitSingleOverride = false) {
        this.selectionMode = "none";
        this.selectedFpIndex = -1;
        this.selectedGroupId = null;
        this.hoveredGroupId = null;
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

    private updateHoverGroup(worldPos: Vec2) {
        let nextHoverId: string | null = null;
        if (this.model && !this.singleOverrideMode) {
            const hitIndex = hitTestFootprints(worldPos, this.model.footprints);
            if (hitIndex >= 0) {
                nextHoverId = this.groupIdByFpIndex.get(hitIndex) ?? null;
            }
        }
        if (nextHoverId === this.hoveredGroupId) return;
        this.hoveredGroupId = nextHoverId;
        this.repaintWithSelection();
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
                const hitGroupId = this.groupIdByFpIndex.get(hitIdx) ?? null;
                if (!this.singleOverrideMode && hitGroupId) {
                    this.setGroupSelection(hitGroupId);
                } else {
                    this.setSingleSelection(hitIdx, false);
                }

                const dragTargets = this.selectionMode === "group"
                    ? this.selectedGroupMembers()
                    : [hitIdx];
                const dragStartPositions = new Map<number, { x: number; y: number }>();
                for (const index of dragTargets) {
                    const fp = this.model.footprints[index];
                    if (!fp) continue;
                    dragStartPositions.set(index, { x: fp.at.x, y: fp.at.y });
                }
                if (dragStartPositions.size === 0) {
                    this.repaintWithSelection();
                    return;
                }

                this.isDragging = true;
                this.dragStartWorld = worldPos;
                this.dragTargetIndices = [...dragStartPositions.keys()];
                this.dragStartPositions = dragStartPositions;
                this.repaintWithSelection();
            } else {
                this.clearSelection(true);
                this.paint();
                this.requestRedraw();
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
            if (e.button !== 0 || !this.isDragging) return;
            this.isDragging = false;

            if (!this.model || !this.dragStartPositions || this.dragTargetIndices.length === 0) {
                this.dragStartWorld = null;
                this.dragStartPositions = null;
                this.dragTargetIndices = [];
                return;
            }

            const firstTarget = this.dragTargetIndices[0]!;
            const firstStart = this.dragStartPositions.get(firstTarget);
            const firstFp = this.model.footprints[firstTarget];
            if (!firstStart || !firstFp) {
                this.dragStartWorld = null;
                this.dragStartPositions = null;
                this.dragTargetIndices = [];
                return;
            }

            const dx = firstFp.at.x - firstStart.x;
            const dy = firstFp.at.y - firstStart.y;
            const isNoop = Math.abs(dx) < 0.001 && Math.abs(dy) < 0.001;

            this.dragStartWorld = null;
            this.dragStartPositions = null;
            this.dragTargetIndices = [];

            if (isNoop) return;

            if (this.selectionMode === "group" && !this.singleOverrideMode) {
                const uuids = this.selectedGroupMemberUuids();
                if (uuids.length > 0) {
                    await this.executeAction("move", { uuids, dx, dy });
                }
                return;
            }

            if (this.selectionMode === "single" && this.selectedFpIndex >= 0) {
                const selectedFp = this.model.footprints[this.selectedFpIndex]!;
                await this.executeAction("move", {
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
        if (this.selectionMode === "group" && !this.singleOverrideMode) {
            const uuids = this.selectedGroupMemberUuids();
            if (uuids.length > 0) {
                await this.executeAction("rotate", { uuids, delta_degrees: deltaDegrees });
            }
            return;
        }
        if (this.selectionMode === "single" && this.selectedFpIndex >= 0) {
            const fp = this.model.footprints[this.selectedFpIndex]!;
            await this.executeAction("rotate", { uuid: fp.uuid, delta_degrees: deltaDegrees });
        }
    }

    private async flipSelection() {
        if (!this.model) return;
        if (this.selectionMode === "group" && !this.singleOverrideMode) {
            const uuids = this.selectedGroupMemberUuids();
            if (uuids.length > 0) {
                await this.executeAction("flip", { uuids });
            }
            return;
        }
        if (this.selectionMode === "single" && this.selectedFpIndex >= 0) {
            const fp = this.model.footprints[this.selectedFpIndex]!;
            await this.executeAction("flip", { uuid: fp.uuid });
        }
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
        for (const d of this.model.drawings) {
            if (d.layer) layers.add(d.layer);
        }
        for (const t of this.model.texts) {
            if (t.layer) layers.add(t.layer);
        }
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
            for (const a of fp.pad_names) {
                if (a.layer) layers.add(a.layer);
            }
            for (const a of fp.pad_numbers) {
                if (a.layer) layers.add(a.layer);
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
        const concreteLayers = new Set<string>(
            [...layers].filter(l => !l.includes("*") && !l.includes("&")),
        );
        for (const layerName of [...layers]) {
            for (const expanded of expandLayerName(layerName, concreteLayers)) {
                layers.add(expanded);
            }
        }
        for (const z of this.model.zones) {
            for (const layerName of z.layers) {
                for (const expanded of expandLayerName(layerName, concreteLayers)) {
                    layers.add(expanded);
                }
            }
        }
        layers.add("Edge.Cuts");
        // Filter out wildcard layers (*.Cu, F&B.Cu, etc.)
        for (const l of layers) {
            if (l.includes("*") || l.includes("&")) layers.delete(l);
        }
        return sortLayerNames(layers);
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

        for (const text of this.model.texts) {
            if (!text.text.trim()) continue;
            const layerName = text.layer ?? "Dwgs.User";
            if (this.hiddenLayers.has(layerName)) continue;
            this.drawOverlayText(
                text.text,
                layerName,
                text.at.x,
                text.at.y,
                text.at.r || 0,
                text.size?.w ?? text.size?.h ?? 1,
                text.size?.h ?? text.size?.w ?? 1,
                text.thickness,
                text.justify,
                width,
                height,
            );
        }
        for (const fp of this.model.footprints) {
            for (const text of fp.texts) {
                if (!text.text.trim()) continue;
                const layerName = text.layer ?? fp.layer;
                if (this.hiddenLayers.has(layerName)) continue;
                const worldPos = this.transformFootprintPoint(fp.at, text.at.x, text.at.y);
                const textRotation = (fp.at.r || 0) + (text.at.r || 0);
                this.drawOverlayText(
                    text.text,
                    layerName,
                    worldPos.x,
                    worldPos.y,
                    textRotation,
                    text.size?.w ?? text.size?.h ?? 1,
                    text.size?.h ?? text.size?.w ?? 1,
                    text.thickness,
                    text.justify,
                    width,
                    height,
                );
            }
        }
    }

    private drawOverlayText(
        text: string,
        layerName: string,
        worldX: number,
        worldY: number,
        rotationDeg: number,
        textWidth: number,
        textHeight: number,
        thickness: number | null,
        justify: string[] | null,
        width: number,
        height: number,
    ) {
        if (!this.textCtx) return;
        const screenPos = this.camera.world_to_screen(new Vec2(worldX, worldY));
        if (
            screenPos.x < -200 || screenPos.x > width + 200
            || screenPos.y < -50 || screenPos.y > height + 50
        ) {
            return;
        }

        const screenFontSize = textHeight * this.camera.zoom;
        if (screenFontSize < 2) return;
        const lines = text.split("\n");
        if (lines.length === 0) return;
        const justifySet = new Set(justify ?? []);

        const [r, g, b, a] = getLayerColor(layerName);
        const rotation = -(rotationDeg || 0) * DEG_TO_RAD;
        const linePitch = textHeight * 1.62;
        const totalHeight = textHeight * 1.17 + Math.max(0, lines.length - 1) * linePitch;
        let baseOffsetY = textHeight;
        if (justifySet.has("center") || (!justifySet.has("top") && !justifySet.has("bottom"))) {
            baseOffsetY -= totalHeight / 2;
        } else if (justifySet.has("bottom")) {
            baseOffsetY -= totalHeight;
        }
        const minWorldStroke = 0.8 / Math.max(this.camera.zoom, 1e-6);
        const worldStroke = Math.max(minWorldStroke, thickness ?? (textHeight * 0.15));
        this.textCtx.save();
        this.textCtx.translate(screenPos.x, screenPos.y);
        this.textCtx.rotate(rotation);
        this.textCtx.scale(this.camera.zoom, this.camera.zoom);
        const color = `rgba(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)}, ${Math.max(a, 0.55)})`;
        this.textCtx.strokeStyle = color;
        this.textCtx.lineWidth = worldStroke;
        this.textCtx.lineCap = "round";
        this.textCtx.lineJoin = "round";
        for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
            const line = lines[lineIdx]!;
            const layout = layoutKicadStrokeLine(line, textWidth, textHeight);
            if (layout.strokes.length === 0) {
                continue;
            }
            let lineOffsetX = 0;
            if (justifySet.has("right")) {
                lineOffsetX = -layout.advance;
            } else if (justifySet.has("center") || (!justifySet.has("left") && !justifySet.has("right"))) {
                lineOffsetX = -layout.advance / 2;
            }
            const lineOffsetY = baseOffsetY + lineIdx * linePitch;
            for (const stroke of layout.strokes) {
                if (stroke.length < 2) continue;
                this.textCtx.beginPath();
                this.textCtx.moveTo(stroke[0]!.x + lineOffsetX, stroke[0]!.y + lineOffsetY);
                for (let i = 1; i < stroke.length; i++) {
                    this.textCtx.lineTo(stroke[i]!.x + lineOffsetX, stroke[i]!.y + lineOffsetY);
                }
                this.textCtx.stroke();
            }
        }
        this.textCtx.restore();
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
