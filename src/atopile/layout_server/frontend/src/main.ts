import { Editor } from "./editor";
import { getLayerColor } from "./colors";

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

interface LayerGroup {
    prefix: string;
    layers: { name: string; suffix: string }[];
}

function groupLayers(layerNames: string[]): { groups: LayerGroup[]; topLevel: string[] } {
    const groupMap = new Map<string, { name: string; suffix: string }[]>();
    const topLevel: string[] = [];

    for (const name of layerNames) {
        const dotIdx = name.indexOf(".");
        if (dotIdx >= 0) {
            const prefix = name.substring(0, dotIdx);
            const suffix = name.substring(dotIdx + 1);
            if (!groupMap.has(prefix)) groupMap.set(prefix, []);
            groupMap.get(prefix)!.push({ name, suffix });
        } else {
            topLevel.push(name);
        }
    }

    const groups: LayerGroup[] = [];
    for (const [prefix, layers] of groupMap) {
        groups.push({ prefix, layers });
    }

    return { groups, topLevel };
}

function colorToCSS(layerName: string): string {
    const [r, g, b] = getLayerColor(layerName);
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

    const layers = editor.getLayers();
    const { groups, topLevel } = groupLayers(layers);

    // Build groups
    for (const group of groups) {
        const childNames = group.layers.map(l => l.name);
        const isCollapsed = collapsedGroups.has(group.prefix);

        // Group header row
        const groupRow = document.createElement("div");
        groupRow.className = "layer-group-header";

        const chevron = document.createElement("span");
        chevron.className = "layer-chevron";
        chevron.textContent = isCollapsed ? "\u25B8" : "\u25BE";

        const primaryColor = colorToCSS(childNames[0]!);
        const swatch = createSwatch(primaryColor);

        const label = document.createElement("span");
        label.className = "layer-group-name";
        label.textContent = group.prefix;

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
            if (collapsedGroups.has(group.prefix)) {
                collapsedGroups.delete(group.prefix);
                chevron.textContent = "\u25BE";
            } else {
                collapsedGroups.add(group.prefix);
                chevron.textContent = "\u25B8";
            }
            const childContainer = groupRow.nextElementSibling as HTMLElement;
            if (childContainer) {
                childContainer.style.display = collapsedGroups.has(group.prefix) ? "none" : "block";
            }
        });

        content.appendChild(groupRow);

        // Child rows container
        const childContainer = document.createElement("div");
        childContainer.className = "layer-group-children";
        childContainer.style.display = isCollapsed ? "none" : "block";

        for (const child of group.layers) {
            const row = document.createElement("div");
            row.className = "layer-row";

            const childSwatch = createSwatch(colorToCSS(child.name));
            const childLabel = document.createElement("span");
            childLabel.textContent = child.suffix;

            row.appendChild(childSwatch);
            row.appendChild(childLabel);

            updateRowVisual(row, editor.isLayerVisible(child.name));

            row.addEventListener("click", () => {
                const vis = !editor.isLayerVisible(child.name);
                editor.setLayerVisible(child.name, vis);
                updateRowVisual(row, vis);
                updateGroupVisual(groupRow, childNames);
            });

            childContainer.appendChild(row);
        }

        content.appendChild(childContainer);
    }

    // Top-level layers (no dot)
    for (const name of topLevel) {
        const row = document.createElement("div");
        row.className = "layer-row layer-top-level";

        const swatch = createSwatch(colorToCSS(name));
        const label = document.createElement("span");
        label.textContent = name;

        row.appendChild(swatch);
        row.appendChild(label);

        updateRowVisual(row, editor.isLayerVisible(name));

        row.addEventListener("click", () => {
            const vis = !editor.isLayerVisible(name);
            editor.setLayerVisible(name, vis);
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

const statusEl = document.getElementById("status");
const buildStatusEl = document.getElementById("build-status");
const buildStatusTextEl = document.getElementById("build-status-text");
const helpText = "scroll to zoom, middle-click to pan, left-click to select/drag, R rotate, F flip, Ctrl+Z undo, Ctrl+Shift+Z redo";
if (statusEl) statusEl.textContent = helpText;

canvas.addEventListener("mouseenter", () => {
    if (statusEl) statusEl.dataset.hover = "1";
});
canvas.addEventListener("mouseleave", () => {
    if (statusEl) {
        delete statusEl.dataset.hover;
        statusEl.textContent = helpText;
    }
});

editor.setOnMouseMove((x, y) => {
    if (statusEl && statusEl.dataset.hover) {
        statusEl.textContent = `X: ${x.toFixed(2)}  Y: ${y.toFixed(2)}`;
    }
});

editor.setOnStatusChanged((status, message) => {
    if (!buildStatusEl) return;
    if (status === "loading") {
        buildStatusEl.classList.add("visible");
        if (buildStatusTextEl) {
            buildStatusTextEl.textContent = message || "building view";
        }
        return;
    }
    buildStatusEl.classList.remove("visible");
});

editor.init().then(() => {
    buildLayerPanel();
    editor.setOnLayersChanged(buildLayerPanel);
}).catch((err) => {
    console.error("Failed to initialize editor:", err);
});
