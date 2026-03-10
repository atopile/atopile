import { StaticLayoutViewer } from "../../../layout_server/frontend/src/static_viewer";
import { getLayerColor } from "../../../layout_server/frontend/src/colors";
import type { LayerModel, RenderModel } from "../../../layout_server/frontend/src/types";

import type { DemoManifest } from "./shared";

interface LayerGroup {
    group: string;
    layers: LayerModel[];
}

const DEMO_HIDDEN_LAYER_GROUPS = new Set(["Cmts", "Dwgs", "Eco1", "Eco2", "User"]);
const DEMO_HIDDEN_OBJECT_FILTERS = ["__type:zones"];

const OBJECT_ROOT_FILTERS = [
    { id: "__type:zones", label: "Zones", color: "#5a8a3a" },
    { id: "__type:tracks", label: "Tracks & Vias", color: "#c05030" },
    { id: "__type:pads", label: "Pads", color: "#a07020" },
] as const;

const TEXT_SHAPES_FILTERS = [
    { id: "__type:text", label: "Text", color: "#4a8cad" },
    { id: "__type:shapes", label: "Shapes", color: "#356982" },
] as const;

const TEXT_SHAPES_FILTER_IDS = TEXT_SHAPES_FILTERS.map((item) => item.id);
const OBJECT_TYPE_IDS = [
    ...OBJECT_ROOT_FILTERS.map((item) => item.id),
    ...TEXT_SHAPES_FILTER_IDS,
];

let panelCollapsed = window.matchMedia("(max-width: 700px)").matches;
const collapsedGroups = new Set<string>();
let objectTypesExpanded = false;
let textShapesExpanded = false;

async function fetchLayoutModel(assetBase: string, manifest: DemoManifest): Promise<RenderModel> {
    const response = await fetch(new URL(manifest.layoutModelPath, `${assetBase}/`).toString());
    if (!response.ok) {
        throw new Error(`Failed to load layout model (${response.status})`);
    }
    return await response.json() as RenderModel;
}

function groupLayers(layers: LayerModel[]): { groups: LayerGroup[]; topLevel: LayerModel[] } {
    const grouped = new Map<string, LayerModel[]>();
    const topLevel: LayerModel[] = [];
    for (const layer of layers) {
        const group = layer.group?.trim() ?? "";
        if (!group) {
            topLevel.push(layer);
            continue;
        }
        const bucket = grouped.get(group) ?? [];
        bucket.push(layer);
        grouped.set(group, bucket);
    }
    const groups = [...grouped.entries()]
        .map(([group, groupLayers]) => ({ group, layers: groupLayers }))
        .sort((a, b) => {
            const aOrder = a.layers[0]?.panel_order ?? Number.MAX_SAFE_INTEGER;
            const bOrder = b.layers[0]?.panel_order ?? Number.MAX_SAFE_INTEGER;
            if (aOrder !== bOrder) return aOrder - bOrder;
            return a.group.localeCompare(b.group);
        });
    return { groups, topLevel };
}

function colorToCss(layerName: string, layerById: Map<string, LayerModel>): string {
    const [r, g, b] = getLayerColor(layerName, layerById);
    return `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})`;
}

function createSwatch(color: string): HTMLSpanElement {
    const swatch = document.createElement("span");
    swatch.className = "layer-swatch";
    swatch.style.background = color;
    return swatch;
}

function computeDemoHiddenLayers(
    layers: LayerModel[],
    manifestHidden: Iterable<string>,
): string[] {
    const hidden = new Set(manifestHidden);
    for (const id of DEMO_HIDDEN_OBJECT_FILTERS) hidden.add(id);
    for (const layer of layers) {
        if (layer.group && DEMO_HIDDEN_LAYER_GROUPS.has(layer.group)) {
            hidden.add(layer.id);
        }
    }
    return [...hidden];
}

function renderLayerSelector(
    container: HTMLElement,
    layoutViewer: StaticLayoutViewer,
    initiallyHidden: string[],
): void {
    const hiddenLayers = new Set(initiallyHidden);
    const panel = container.querySelector<HTMLElement>("#layer-panel");
    if (!panel) {
        throw new Error("Layout scaffold missing #layer-panel");
    }
    panel.replaceChildren();
    panel.className = "";
    panel.id = "layer-panel";

    const header = document.createElement("div");
    header.className = "layer-panel-header";

    const headerTitle = document.createElement("span");
    headerTitle.textContent = "Layers";

    const expandTab = document.createElement("div");
    expandTab.className = "layer-expand-tab";
    expandTab.textContent = "Layers";
    expandTab.addEventListener("click", () => {
        panelCollapsed = false;
        panel.classList.remove("collapsed");
        expandTab.classList.remove("visible");
    });

    const collapseBtn = document.createElement("span");
    collapseBtn.className = "layer-collapse-btn";
    collapseBtn.textContent = "\u25C0";
    collapseBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        panelCollapsed = true;
        panel.classList.add("collapsed");
        expandTab.classList.add("visible");
    });

    header.append(headerTitle, collapseBtn);
    panel.appendChild(header);

    const content = document.createElement("div");
    content.className = "layer-panel-content";
    panel.appendChild(content);

    const layers = layoutViewer.getLayerModels();
    const layerById = new Map(layers.map((layer) => [layer.id, layer]));
    const { groups, topLevel } = groupLayers(layers);

    const applyHiddenLayers = () => layoutViewer.setHiddenLayers(hiddenLayers);
    const updateRowVisual = (row: HTMLElement, visible: boolean) => {
        row.style.opacity = visible ? "1" : "0.3";
    };
    const updateGroupVisual = (row: HTMLElement, ids: string[]) => {
        const allVisible = ids.every((id) => !hiddenLayers.has(id));
        const allHidden = ids.every((id) => hiddenLayers.has(id));
        row.style.opacity = allVisible ? "1" : allHidden ? "0.3" : "0.6";
    };

    const objectRows = new Map<string, HTMLElement>();

    const objGroupRow = document.createElement("div");
    objGroupRow.className = "layer-group-header";

    const objChevron = document.createElement("span");
    objChevron.className = "layer-chevron";
    objChevron.textContent = objectTypesExpanded ? "\u25BE" : "\u25B8";

    const objSwatch = createSwatch("linear-gradient(135deg, #5a8a3a 50%, #c05030 50%)");

    const objLabel = document.createElement("span");
    objLabel.className = "layer-group-name";
    objLabel.textContent = "Objects";

    objGroupRow.append(objChevron, objSwatch, objLabel);

    const objChildContainer = document.createElement("div");
    objChildContainer.className = "layer-group-children";
    if (!objectTypesExpanded) {
        objChildContainer.style.maxHeight = "0";
    }

    const updateObjGroupVisual = () => updateGroupVisual(objGroupRow, [...OBJECT_TYPE_IDS]);

    const updateTextShapesGroupVisual = (row: HTMLElement) => {
        updateGroupVisual(row, [...TEXT_SHAPES_FILTER_IDS]);
    };

    const updateObjectRows = (textShapesGroupRow: HTMLElement) => {
        for (const [id, row] of objectRows.entries()) {
            updateRowVisual(row, !hiddenLayers.has(id));
        }
        updateTextShapesGroupVisual(textShapesGroupRow);
        updateObjGroupVisual();
    };

    objChevron.addEventListener("click", (event) => {
        event.stopPropagation();
        if (objectTypesExpanded) {
            objectTypesExpanded = false;
            objChevron.textContent = "\u25B8";
            objChildContainer.style.maxHeight = `${objChildContainer.scrollHeight}px`;
            requestAnimationFrame(() => { objChildContainer.style.maxHeight = "0"; });
        } else {
            objectTypesExpanded = true;
            objChevron.textContent = "\u25BE";
            objChildContainer.style.maxHeight = `${objChildContainer.scrollHeight}px`;
            const onEnd = () => {
                objChildContainer.style.maxHeight = "";
                objChildContainer.removeEventListener("transitionend", onEnd);
            };
            objChildContainer.addEventListener("transitionend", onEnd);
        }
    });

    let textShapesGroupRow: HTMLElement;

    objGroupRow.addEventListener("click", () => {
        const allVisible = OBJECT_TYPE_IDS.every((id) => !hiddenLayers.has(id));
        for (const id of OBJECT_TYPE_IDS) {
            if (allVisible) hiddenLayers.add(id);
            else hiddenLayers.delete(id);
        }
        updateObjectRows(textShapesGroupRow);
        applyHiddenLayers();
    });

    for (const objectType of OBJECT_ROOT_FILTERS) {
        const row = document.createElement("div");
        row.className = "layer-row";

        const swatch = createSwatch(objectType.color);
        const label = document.createElement("span");
        label.className = "layer-label";
        label.textContent = objectType.label;

        row.append(swatch, label);
        updateRowVisual(row, !hiddenLayers.has(objectType.id));
        row.addEventListener("click", () => {
            if (hiddenLayers.has(objectType.id)) hiddenLayers.delete(objectType.id);
            else hiddenLayers.add(objectType.id);
            updateObjectRows(textShapesGroupRow);
            applyHiddenLayers();
        });

        objectRows.set(objectType.id, row);
        objChildContainer.appendChild(row);
    }

    textShapesGroupRow = document.createElement("div");
    textShapesGroupRow.className = "layer-group-header";

    const textShapesChevron = document.createElement("span");
    textShapesChevron.className = "layer-chevron";
    textShapesChevron.textContent = textShapesExpanded ? "\u25BE" : "\u25B8";

    const textShapesSwatch = createSwatch("linear-gradient(135deg, #4a8cad 50%, #356982 50%)");

    const textShapesLabel = document.createElement("span");
    textShapesLabel.className = "layer-group-name";
    textShapesLabel.textContent = "Text & Shapes";

    textShapesGroupRow.append(textShapesChevron, textShapesSwatch, textShapesLabel);

    const textShapesChildContainer = document.createElement("div");
    textShapesChildContainer.className = "layer-group-children";
    if (!textShapesExpanded) {
        textShapesChildContainer.style.maxHeight = "0";
    }

    textShapesChevron.addEventListener("click", (event) => {
        event.stopPropagation();
        if (textShapesExpanded) {
            textShapesExpanded = false;
            textShapesChevron.textContent = "\u25B8";
            textShapesChildContainer.style.maxHeight = `${textShapesChildContainer.scrollHeight}px`;
            requestAnimationFrame(() => { textShapesChildContainer.style.maxHeight = "0"; });
        } else {
            textShapesExpanded = true;
            textShapesChevron.textContent = "\u25BE";
            textShapesChildContainer.style.maxHeight = `${textShapesChildContainer.scrollHeight}px`;
            const onEnd = () => {
                textShapesChildContainer.style.maxHeight = "";
                textShapesChildContainer.removeEventListener("transitionend", onEnd);
            };
            textShapesChildContainer.addEventListener("transitionend", onEnd);
        }
    });

    textShapesGroupRow.addEventListener("click", () => {
        const allVisible = TEXT_SHAPES_FILTER_IDS.every((id) => !hiddenLayers.has(id));
        for (const id of TEXT_SHAPES_FILTER_IDS) {
            if (allVisible) hiddenLayers.add(id);
            else hiddenLayers.delete(id);
        }
        updateObjectRows(textShapesGroupRow);
        applyHiddenLayers();
    });

    for (const objectType of TEXT_SHAPES_FILTERS) {
        const row = document.createElement("div");
        row.className = "layer-row";

        const swatch = createSwatch(objectType.color);
        const label = document.createElement("span");
        label.className = "layer-label";
        label.textContent = objectType.label;

        row.append(swatch, label);
        updateRowVisual(row, !hiddenLayers.has(objectType.id));
        row.addEventListener("click", () => {
            if (hiddenLayers.has(objectType.id)) hiddenLayers.delete(objectType.id);
            else hiddenLayers.add(objectType.id);
            updateObjectRows(textShapesGroupRow);
            applyHiddenLayers();
        });

        objectRows.set(objectType.id, row);
        textShapesChildContainer.appendChild(row);
    }

    objChildContainer.append(textShapesGroupRow, textShapesChildContainer);
    updateObjectRows(textShapesGroupRow);
    content.append(objGroupRow, objChildContainer);

    for (const group of groups) {
        const groupIds = group.layers.map((layer) => layer.id);
        const isCollapsed = collapsedGroups.has(group.group);

        const groupRow = document.createElement("div");
        groupRow.className = "layer-group-header";

        const chevron = document.createElement("span");
        chevron.className = "layer-chevron";
        chevron.textContent = isCollapsed ? "\u25B8" : "\u25BE";

        const swatch = createSwatch(colorToCss(groupIds[0]!, layerById));

        const label = document.createElement("span");
        label.className = "layer-group-name";
        label.textContent = group.group;

        groupRow.append(chevron, swatch, label);

        const childContainer = document.createElement("div");
        childContainer.className = "layer-group-children";
        if (isCollapsed) {
            childContainer.style.maxHeight = "0";
        }

        const childRows: Array<{ id: string; row: HTMLElement }> = [];
        for (const layer of group.layers) {
            const row = document.createElement("div");
            row.className = "layer-row";

            const childSwatch = createSwatch(colorToCss(layer.id, layerById));

            const childLabel = document.createElement("span");
            childLabel.className = "layer-label";
            childLabel.textContent = layer.label ?? layer.id;

            row.append(childSwatch, childLabel);
            updateRowVisual(row, !hiddenLayers.has(layer.id));
            row.addEventListener("click", () => {
                if (hiddenLayers.has(layer.id)) hiddenLayers.delete(layer.id);
                else hiddenLayers.add(layer.id);
                updateRowVisual(row, !hiddenLayers.has(layer.id));
                updateGroupVisual(groupRow, groupIds);
                applyHiddenLayers();
            });

            childRows.push({ id: layer.id, row });
            childContainer.appendChild(row);
        }

        updateGroupVisual(groupRow, groupIds);
        groupRow.addEventListener("click", () => {
            const allVisible = groupIds.every((id) => !hiddenLayers.has(id));
            for (const id of groupIds) {
                if (allVisible) hiddenLayers.add(id);
                else hiddenLayers.delete(id);
            }
            for (const child of childRows) {
                updateRowVisual(child.row, !hiddenLayers.has(child.id));
            }
            updateGroupVisual(groupRow, groupIds);
            applyHiddenLayers();
        });
        chevron.addEventListener("click", (event) => {
            event.stopPropagation();
            if (collapsedGroups.has(group.group)) {
                collapsedGroups.delete(group.group);
                chevron.textContent = "\u25BE";
                childContainer.style.maxHeight = `${childContainer.scrollHeight}px`;
                const onEnd = () => {
                    childContainer.style.maxHeight = "";
                    childContainer.removeEventListener("transitionend", onEnd);
                };
                childContainer.addEventListener("transitionend", onEnd);
            } else {
                collapsedGroups.add(group.group);
                chevron.textContent = "\u25B8";
                childContainer.style.maxHeight = `${childContainer.scrollHeight}px`;
                requestAnimationFrame(() => {
                    childContainer.style.maxHeight = "0";
                });
            }
        });

        content.append(groupRow, childContainer);
    }

    for (const layer of topLevel) {
        const row = document.createElement("div");
        row.className = "layer-row layer-top-level";

        const swatch = createSwatch(colorToCss(layer.id, layerById));

        const label = document.createElement("span");
        label.className = "layer-label";
        label.textContent = layer.label ?? layer.id;

        row.append(swatch, label);
        updateRowVisual(row, !hiddenLayers.has(layer.id));
        row.addEventListener("click", () => {
            if (hiddenLayers.has(layer.id)) hiddenLayers.delete(layer.id);
            else hiddenLayers.add(layer.id);
            updateRowVisual(row, !hiddenLayers.has(layer.id));
            applyHiddenLayers();
        });
        content.appendChild(row);
    }

    if (panelCollapsed) {
        panel.classList.add("collapsed");
        expandTab.classList.add("visible");
    }

    container.appendChild(expandTab);
}

export async function mountLayout(
    shell: HTMLElement,
    surface: HTMLElement,
    initialLoading: HTMLElement,
    assetBase: string,
    manifest: DemoManifest,
): Promise<() => void> {
    const layoutViewer = new StaticLayoutViewer(surface);
    const layoutModel = await fetchLayoutModel(assetBase, manifest);
    const hiddenLayoutLayers = computeDemoHiddenLayers(
        layoutModel.layers,
        manifest.hiddenLayoutLayers ?? [],
    );
    layoutViewer.setModel(layoutModel);
    layoutViewer.setHiddenLayers(hiddenLayoutLayers);
    renderLayerSelector(shell, layoutViewer, hiddenLayoutLayers);
    initialLoading.remove();
    return () => {
        layoutViewer.destroy();
    };
}
