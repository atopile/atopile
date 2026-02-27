import { Editor } from "./editor";
import { getLayerColor } from "./colors";
import type { LayerModel } from "./types";

const canvas = document.getElementById("editor-canvas") as HTMLCanvasElement;
if (!canvas) {
    throw new Error("Canvas element #editor-canvas not found");
}

const w = window as any;
const baseUrl: string = w.__LAYOUT_BASE_URL__ || window.location.origin;
const apiPrefix: string = w.__LAYOUT_API_PREFIX__ || "/api";
const wsPath: string = w.__LAYOUT_WS_PATH__ || "/ws";
const editor = new Editor(canvas, baseUrl, apiPrefix, wsPath);

// Persistent UI state across rebuilds
let panelCollapsed = false;
const collapsedGroups = new Set<string>();
let objectTypesExpanded = false;

const OBJECT_TYPES = [
    { id: "__type:zones",  label: "Zones",         color: "#5a8a3a" },
    { id: "__type:tracks", label: "Tracks & Vias", color: "#c05030" },
    { id: "__type:pads",   label: "Pads",          color: "#a07020" },
    { id: "__type:other",  label: "Text & shapes", color: "#4080a0" },
] as const;
const OBJECT_TYPE_IDS = OBJECT_TYPES.map(t => t.id);

interface LayerGroup {
    group: string;
    layers: LayerModel[];
}

function groupLayers(layers: LayerModel[]): { groups: LayerGroup[]; topLevel: LayerModel[] } {
    const groupMap = new Map<string, LayerModel[]>();
    const topLevel: LayerModel[] = [];

    for (const layer of layers) {
        const group = layer.group?.trim() ?? "";
        if (!group) {
            topLevel.push(layer);
            continue;
        }
        if (!groupMap.has(group)) groupMap.set(group, []);
        groupMap.get(group)!.push(layer);
    }

    const groups = [...groupMap.entries()]
        .map(([group, groupedLayers]) => ({ group, layers: groupedLayers }))
        .sort((a, b) => {
            const aOrder = a.layers[0]?.panel_order ?? Number.MAX_SAFE_INTEGER;
            const bOrder = b.layers[0]?.panel_order ?? Number.MAX_SAFE_INTEGER;
            if (aOrder !== bOrder) return aOrder - bOrder;
            return a.group.localeCompare(b.group);
        });

    return { groups, topLevel };
}

function colorToCSS(layerName: string, layerById: Map<string, LayerModel>): string {
    const [r, g, b] = getLayerColor(layerName, layerById);
    return `rgb(${Math.round(r * 255)},${Math.round(g * 255)},${Math.round(b * 255)})`;
}

function createSwatch(color: string): HTMLSpanElement {
    const swatch = document.createElement("span");
    swatch.className = "layer-swatch";
    swatch.style.background = color;
    return swatch;
}

function updateRowVisual(row: HTMLElement, visible: boolean) {
    row.style.opacity = visible ? "1" : "0.3";
}

function updateGroupVisual(row: HTMLElement, childLayers: string[]) {
    const allVisible = childLayers.every(l => editor.isLayerVisible(l));
    const allHidden = childLayers.every(l => !editor.isLayerVisible(l));
    if (allVisible) {
        row.style.opacity = "1";
    } else if (allHidden) {
        row.style.opacity = "0.3";
    } else {
        row.style.opacity = "0.6";
    }
}

function buildLayerPanel() {
    const panel = document.getElementById("layer-panel");
    if (!panel) return;
    panel.innerHTML = "";

    // Header
    const header = document.createElement("div");
    header.className = "layer-panel-header";

    const headerTitle = document.createElement("span");
    headerTitle.textContent = "Layers";

    // Expand tab — lives outside the panel so transform doesn't hide it
    let expandTab = document.getElementById("layer-expand-tab");
    if (!expandTab) {
        expandTab = document.createElement("div");
        expandTab.id = "layer-expand-tab";
        expandTab.className = "layer-expand-tab";
        expandTab.textContent = "Layers";
        expandTab.addEventListener("click", () => {
            panelCollapsed = false;
            panel.classList.remove("collapsed");
            expandTab!.classList.remove("visible");
        });
        document.body.appendChild(expandTab);
    }

    const collapseBtn = document.createElement("span");
    collapseBtn.className = "layer-collapse-btn";
    collapseBtn.textContent = "\u25C0";
    collapseBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        panelCollapsed = true;
        panel.classList.add("collapsed");
        expandTab!.classList.add("visible");
    });

    header.appendChild(headerTitle);
    header.appendChild(collapseBtn);
    panel.appendChild(header);

    const content = document.createElement("div");
    content.className = "layer-panel-content";

    // — Objects section (Zones / Tracks & Vias / Pads / Text & shapes) —
    const objGroupRow = document.createElement("div");
    objGroupRow.className = "layer-group-header";

    const objChevron = document.createElement("span");
    objChevron.className = "layer-chevron";
    objChevron.textContent = objectTypesExpanded ? "\u25BE" : "\u25B8";

    const objSwatch = document.createElement("span");
    objSwatch.className = "layer-swatch";
    objSwatch.style.background = "linear-gradient(135deg, #5a8a3a 50%, #c05030 50%)";

    const objLabel = document.createElement("span");
    objLabel.className = "layer-group-name";
    objLabel.textContent = "Objects";

    objGroupRow.appendChild(objChevron);
    objGroupRow.appendChild(objSwatch);
    objGroupRow.appendChild(objLabel);

    function updateObjGroupVisual() {
        const allVis = OBJECT_TYPE_IDS.every(id => editor.isLayerVisible(id));
        const allHid = OBJECT_TYPE_IDS.every(id => !editor.isLayerVisible(id));
        objGroupRow.style.opacity = allVis ? "1" : allHid ? "0.3" : "0.6";
    }
    updateObjGroupVisual();

    const objChildContainer = document.createElement("div");
    objChildContainer.className = "layer-group-children";
    if (!objectTypesExpanded) {
        objChildContainer.style.maxHeight = "0";
    }

    objChevron.addEventListener("click", (e) => {
        e.stopPropagation();
        if (objectTypesExpanded) {
            objectTypesExpanded = false;
            objChevron.textContent = "\u25B8";
            objChildContainer.style.maxHeight = objChildContainer.scrollHeight + "px";
            requestAnimationFrame(() => { objChildContainer.style.maxHeight = "0"; });
        } else {
            objectTypesExpanded = true;
            objChevron.textContent = "\u25BE";
            objChildContainer.style.maxHeight = objChildContainer.scrollHeight + "px";
            const onEnd = () => {
                objChildContainer.style.maxHeight = "";
                objChildContainer.removeEventListener("transitionend", onEnd);
            };
            objChildContainer.addEventListener("transitionend", onEnd);
        }
    });

    objGroupRow.addEventListener("click", () => {
        const allVis = OBJECT_TYPE_IDS.every(id => editor.isLayerVisible(id));
        editor.setLayersVisible([...OBJECT_TYPE_IDS], !allVis);
        updateObjGroupVisual();
        objChildContainer.querySelectorAll<HTMLElement>(".layer-row").forEach((row, i) => {
            updateRowVisual(row, editor.isLayerVisible(OBJECT_TYPE_IDS[i]!));
        });
    });

    for (const objType of OBJECT_TYPES) {
        const row = document.createElement("div");
        row.className = "layer-row";

        const swatch = document.createElement("span");
        swatch.className = "layer-swatch";
        swatch.style.background = objType.color;

        const label = document.createElement("span");
        label.textContent = objType.label;

        row.appendChild(swatch);
        row.appendChild(label);

        updateRowVisual(row, editor.isLayerVisible(objType.id));

        row.addEventListener("click", () => {
            const vis = !editor.isLayerVisible(objType.id);
            editor.setLayerVisible(objType.id, vis);
            updateRowVisual(row, vis);
            updateObjGroupVisual();
        });

        objChildContainer.appendChild(row);
    }

    content.appendChild(objGroupRow);
    content.appendChild(objChildContainer);
    // — end Objects section —

    const layers = editor.getLayerModels();
    const layerById = new Map(layers.map(layer => [layer.id, layer]));
    const { groups, topLevel } = groupLayers(layers);

    // Build groups
    for (const group of groups) {
        const childNames = group.layers.map(l => l.id);
        const isCollapsed = collapsedGroups.has(group.group);

        // Group header row
        const groupRow = document.createElement("div");
        groupRow.className = "layer-group-header";

        const chevron = document.createElement("span");
        chevron.className = "layer-chevron";
        chevron.textContent = isCollapsed ? "\u25B8" : "\u25BE";

        const primaryColor = colorToCSS(childNames[0]!, layerById);
        const swatch = createSwatch(primaryColor);

        const label = document.createElement("span");
        label.className = "layer-group-name";
        label.textContent = group.group;

        groupRow.appendChild(chevron);
        groupRow.appendChild(swatch);
        groupRow.appendChild(label);

        updateGroupVisual(groupRow, childNames);

        // Click group row: toggle all children visibility
        groupRow.addEventListener("click", () => {
            const allVisible = childNames.every(l => editor.isLayerVisible(l));
            editor.setLayersVisible(childNames, !allVisible);
            updateGroupVisual(groupRow, childNames);
            // Update child rows
            const childContainer = groupRow.nextElementSibling as HTMLElement;
            if (childContainer) {
                const rows = childContainer.querySelectorAll<HTMLElement>(".layer-row");
                rows.forEach((row, i) => {
                    updateRowVisual(row, editor.isLayerVisible(childNames[i]!));
                });
            }
        });

        // Chevron click: toggle collapse (stop propagation to not toggle visibility)
        chevron.addEventListener("click", (e) => {
            e.stopPropagation();
            const childContainer = groupRow.nextElementSibling as HTMLElement;
            if (!childContainer) return;
            if (collapsedGroups.has(group.group)) {
                collapsedGroups.delete(group.group);
                chevron.textContent = "\u25BE";
                // Expand: set to scrollHeight then clear after transition
                childContainer.style.maxHeight = childContainer.scrollHeight + "px";
                const onEnd = () => {
                    childContainer.style.maxHeight = "";
                    childContainer.removeEventListener("transitionend", onEnd);
                };
                childContainer.addEventListener("transitionend", onEnd);
            } else {
                collapsedGroups.add(group.group);
                chevron.textContent = "\u25B8";
                // Collapse: set explicit height first, then animate to 0
                childContainer.style.maxHeight = childContainer.scrollHeight + "px";
                requestAnimationFrame(() => {
                    childContainer.style.maxHeight = "0";
                });
            }
        });

        content.appendChild(groupRow);

        // Child rows container
        const childContainer = document.createElement("div");
        childContainer.className = "layer-group-children";
        if (isCollapsed) {
            childContainer.style.maxHeight = "0";
        }

        for (const child of group.layers) {
            const row = document.createElement("div");
            row.className = "layer-row";

            const childSwatch = createSwatch(colorToCSS(child.id, layerById));
            const childLabel = document.createElement("span");
            childLabel.textContent = child.label ?? child.id;

            row.appendChild(childSwatch);
            row.appendChild(childLabel);

            updateRowVisual(row, editor.isLayerVisible(child.id));

            row.addEventListener("click", () => {
                const vis = !editor.isLayerVisible(child.id);
                editor.setLayerVisible(child.id, vis);
                updateRowVisual(row, vis);
                updateGroupVisual(groupRow, childNames);
            });

            childContainer.appendChild(row);
        }

        content.appendChild(childContainer);
    }

    // Top-level layers (no dot)
    for (const layer of topLevel) {
        const row = document.createElement("div");
        row.className = "layer-row layer-top-level";

        const swatch = createSwatch(colorToCSS(layer.id, layerById));
        const label = document.createElement("span");
        label.textContent = layer.label ?? layer.id;

        row.appendChild(swatch);
        row.appendChild(label);

        updateRowVisual(row, editor.isLayerVisible(layer.id));

        row.addEventListener("click", () => {
            const vis = !editor.isLayerVisible(layer.id);
            editor.setLayerVisible(layer.id, vis);
            updateRowVisual(row, vis);
        });

        content.appendChild(row);
    }

    panel.appendChild(content);

    // Restore collapse state
    if (panelCollapsed) {
        panel.classList.add("collapsed");
        expandTab!.classList.add("visible");
    }
}

const coordsEl = document.getElementById("status-coords");
const helpEl = document.getElementById("status-help");
const helpText = "Scroll zoom \u00b7 Middle-click pan \u00b7 Click group/select \u00b7 Shift+drag box-select \u00b7 Double-click single \u00b7 Esc clear \u00b7 R rotate \u00b7 F flip \u00b7 Ctrl+Z undo \u00b7 Ctrl+Shift+Z redo";
if (helpEl) helpEl.textContent = helpText;

canvas.addEventListener("mouseenter", () => {
    if (coordsEl) coordsEl.dataset.hover = "1";
});
canvas.addEventListener("mouseleave", () => {
    if (coordsEl) {
        delete coordsEl.dataset.hover;
        coordsEl.textContent = "";
    }
});

editor.setOnMouseMove((x, y) => {
    if (coordsEl && coordsEl.dataset.hover) {
        coordsEl.textContent = `X: ${x.toFixed(2)}  Y: ${y.toFixed(2)}`;
    }
});

editor.init().then(() => {
    buildLayerPanel();
    editor.setOnLayersChanged(buildLayerPanel);
}).catch((err) => {
    console.error("Failed to initialize editor:", err);
});
