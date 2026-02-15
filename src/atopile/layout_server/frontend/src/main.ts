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

function buildLayerPanel() {
    const panel = document.getElementById("layer-panel");
    if (!panel) return;
    panel.innerHTML = "";

    const layers = editor.getLayers();
    for (const layerName of layers) {
        const row = document.createElement("label");
        row.className = "layer-row";

        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.checked = editor.isLayerVisible(layerName);
        cb.addEventListener("change", () => {
            editor.setLayerVisible(layerName, cb.checked);
        });

        const swatch = document.createElement("span");
        swatch.className = "layer-swatch";
        const [r, g, b] = getLayerColor(layerName);
        swatch.style.background = `rgb(${Math.round(r * 255)},${Math.round(g * 255)},${Math.round(b * 255)})`;

        const label = document.createElement("span");
        label.textContent = layerName;

        row.appendChild(cb);
        row.appendChild(swatch);
        row.appendChild(label);
        panel.appendChild(row);
    }
}

editor.init().then(() => {
    buildLayerPanel();
    editor.setOnLayersChanged(buildLayerPanel);
}).catch((err) => {
    console.error("Failed to initialize editor:", err);
});
