import { StaticLayoutViewer } from "../../layout_server/frontend/src/static_viewer";
import { getLayerColor } from "../../layout_server/frontend/src/colors";
import type { LayerModel, RenderModel } from "../../layout_server/frontend/src/types";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { MeshoptDecoder } from "three/examples/jsm/libs/meshopt_decoder.module.js";

declare global {
    interface Window {
        AtopileDemo?: {
            mount: typeof mount;
        };
        __ATOPILE_DEMO_SET_TOP_DOWN__?: (() => void) | null;
        __ATOPILE_DEMO_READY__?: boolean;
        __ATOPILE_DEMO_STATE__?: {
            layoutLoaded: boolean;
            modelLoaded: boolean;
            error: string | null;
        };
    }
}

export interface DemoManifest {
    title?: string;
    subtitle?: string;
    layoutModelPath: string;
    modelPath: string;
    posterPath?: string;
    hiddenLayoutLayers?: string[];
}

export interface MountOptions {
    assetBase?: string;
    manifest?: string | DemoManifest;
}

const DEFAULT_MANIFEST = "demo-manifest.json";
const DEFAULT_ASSET_BASE = (() => {
    if (typeof document !== "undefined") {
        const script = document.currentScript as HTMLScriptElement | null;
        if (script?.src) {
            return new URL(".", script.src).toString().replace(/\/$/, "");
        }
    }
    return new URL(".", window.location.href).toString().replace(/\/$/, "");
})();

function setDemoState(patch: Partial<NonNullable<typeof window.__ATOPILE_DEMO_STATE__>>) {
    const state = {
        layoutLoaded: false,
        modelLoaded: false,
        error: null,
        ...window.__ATOPILE_DEMO_STATE__,
        ...patch,
    };
    window.__ATOPILE_DEMO_STATE__ = state;
    const ready = state.layoutLoaded && state.modelLoaded && !state.error;
    window.__ATOPILE_DEMO_READY__ = ready;
    if (ready) {
        window.dispatchEvent(new CustomEvent("atopile-demo:ready", { detail: state }));
    }
}

function ensureStyles(): void {
    if (document.getElementById("atopile-demo-styles")) return;
    const style = document.createElement("style");
    style.id = "atopile-demo-styles";
    style.textContent = `
      .atopile-demo-root {
        --demo-bg:
          linear-gradient(rgba(255, 103, 31, 0.11) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255, 103, 31, 0.11) 1px, transparent 1px),
          linear-gradient(rgba(255, 103, 31, 0.035) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255, 103, 31, 0.035) 1px, transparent 1px),
          radial-gradient(circle at 50% 42%, rgba(255, 103, 31, 0.22), transparent 16%),
          radial-gradient(circle at 50% 44%, rgba(255, 103, 31, 0.1), transparent 28%),
          linear-gradient(180deg, #0a0f18 0%, #09111b 48%, #060b13 100%);
        --demo-panel: rgba(8, 13, 21, 0.86);
        --demo-panel-strong: rgba(10, 15, 24, 0.96);
        --demo-border: rgba(255, 103, 31, 0.16);
        --demo-text: #edf1fb;
        --demo-text-muted: rgba(173, 186, 211, 0.72);
        --demo-accent: #ff671f;
        --demo-shadow: 0 28px 90px rgba(0, 0, 0, 0.5);
        color: var(--demo-text);
        font-family: "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif;
        background: var(--demo-bg);
        background-size: 42px 42px, 42px 42px, 14px 14px, 14px 14px, auto, auto, auto;
        border-radius: 28px;
        overflow: hidden;
        border: 1px solid var(--demo-border);
        box-shadow: var(--demo-shadow);
        min-height: 540px;
        display: grid;
        grid-template-rows: auto 1fr;
      }
      .atopile-demo-hero {
        display: flex;
        justify-content: space-between;
        gap: 24px;
        align-items: end;
        padding: 22px 24px 16px;
        background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0));
        border-bottom: 1px solid rgba(255, 103, 31, 0.12);
      }
      .atopile-demo-title {
        margin: 0;
        font-size: clamp(1.1rem, 1.4vw + 0.8rem, 1.9rem);
        letter-spacing: -0.03em;
      }
      .atopile-demo-subtitle {
        margin: 6px 0 0;
        color: var(--demo-text-muted);
        font-size: 0.95rem;
      }
      .atopile-demo-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 999px;
        background: rgba(255, 103, 31, 0.14);
        color: var(--demo-accent);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        box-shadow: 0 0 32px rgba(255, 103, 31, 0.18);
      }
      .atopile-demo-content {
        display: grid;
        grid-template-rows: minmax(320px, 0.95fr) minmax(420px, 1.05fr);
        gap: 1px;
        background: rgba(255, 103, 31, 0.12);
      }
      .atopile-demo-pane {
        position: relative;
        min-height: 420px;
        background: var(--demo-panel);
      }
      .atopile-demo-pane-header {
        position: absolute;
        top: 14px;
        left: 14px;
        z-index: 3;
        display: inline-flex;
        gap: 8px;
        align-items: center;
        padding: 7px 11px;
        border-radius: 999px;
        background: rgba(7, 12, 20, 0.82);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 103, 31, 0.14);
        font-size: 0.78rem;
        color: var(--demo-text-muted);
      }
      .atopile-demo-pane-header strong {
        color: var(--demo-text);
        font-weight: 600;
      }
      .atopile-demo-model-surface {
        position: absolute;
        inset: 0;
      }
      .atopile-demo-layout-shell {
        --bg-deep: #080c14;
        --surface: rgba(12,18,32,0.82);
        --surface-solid: #0f1524;
        --border: rgba(255,255,255,0.07);
        --border-accent: rgba(224,160,56,0.25);
        --text-primary: #e2e5ea;
        --text-secondary: #6b7280;
        --accent: #e0a038;
        --accent-glow: rgba(224,160,56,0.12);
        position: absolute;
        inset: 0;
        overflow: hidden;
        background: var(--bg-deep);
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        text-rendering: optimizeLegibility;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      }
      .atopile-demo-layout-shell * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }
      .atopile-demo-layout-shell canvas {
        display: block;
        width: 100%;
        height: 100%;
        cursor: crosshair;
      }
      .atopile-demo-layout-shell .layout-viewport {
        position: absolute;
        inset: 0 180px 32px 0;
        overflow: hidden;
      }
      .atopile-demo-layout-shell #editor-canvas {
        position: absolute;
        inset: 0;
        overflow: hidden;
      }
      .atopile-demo-layout-shell #initial-loading {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(8, 12, 20, 0.88);
        backdrop-filter: blur(4px);
        -webkit-backdrop-filter: blur(4px);
        z-index: 60;
        opacity: 1;
        pointer-events: auto;
        transition: opacity 0.2s ease;
      }
      .atopile-demo-layout-shell #initial-loading.hidden {
        opacity: 0;
        pointer-events: none;
      }
      .atopile-demo-layout-shell .initial-loading-content {
        min-width: 220px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
        color: var(--text-primary);
        font: 12px/1.4 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      }
      .atopile-demo-layout-shell .initial-loading-spinner {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        border: 2px solid rgba(255, 255, 255, 0.18);
        border-top-color: var(--accent);
        animation: initial-loading-spin 0.8s linear infinite;
      }
      .atopile-demo-layout-shell .initial-loading-message {
        color: var(--text-primary);
        letter-spacing: 0.03em;
        text-transform: uppercase;
      }
      .atopile-demo-layout-shell .initial-loading-subtext {
        color: var(--text-secondary);
        font-size: 10px;
      }
      .atopile-demo-layout-shell #vignette {
        position: absolute;
        inset: 0;
        box-shadow: inset 0 0 120px rgba(0,0,0,0.3);
        pointer-events: none;
        z-index: 5;
      }
      .atopile-demo-layout-shell #editor-canvas .atopile-static-layout-viewer {
        position: absolute;
        inset: 0;
      }
      .atopile-demo-layout-shell #status {
        position: absolute;
        left: 0;
        right: 0;
        bottom: 0;
        height: 32px;
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 0 12px;
        background: var(--surface);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-top: 1px solid var(--border);
        z-index: 30;
        font: 11px/1 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        color: var(--text-secondary);
      }
      .atopile-demo-layout-shell #status::before {
        content: "";
        position: absolute;
        top: -1px;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--border-accent), transparent);
      }
      .atopile-demo-layout-shell #status span {
        white-space: nowrap;
      }
      .atopile-demo-layout-shell #status-coords {
        font-weight: 600;
        font-variant-numeric: tabular-nums;
        color: var(--text-primary);
        letter-spacing: 0.02em;
        min-width: 180px;
      }
      .atopile-demo-layout-shell #status-busy {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        opacity: 0;
        color: var(--text-secondary);
        font-size: 10px;
        letter-spacing: 0.02em;
        pointer-events: none;
        min-width: 74px;
      }
      .atopile-demo-layout-shell .status-busy-spinner {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        border: 1.5px solid rgba(255, 255, 255, 0.2);
        border-top-color: var(--accent);
        animation: status-busy-spin 0.7s linear infinite;
        flex-shrink: 0;
      }
      .atopile-demo-layout-shell #status-fps {
        font-variant-numeric: tabular-nums;
        color: var(--text-secondary);
        font-size: 10px;
        min-width: 48px;
      }
      .atopile-demo-layout-shell #status-help {
        color: var(--text-secondary);
        font-size: 10px;
        text-align: right;
        margin-left: auto;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .atopile-demo-layout-shell #layer-panel {
        position: absolute;
        top: 0;
        right: 0;
        bottom: 32px;
        width: 180px;
        background: var(--surface);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border-left: 1px solid var(--border);
        border-radius: 4px 0 0 0;
        z-index: 7;
        font: 11px/1.4 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        color: var(--text-primary);
        transform: translateX(0);
        transition: transform 0.2s ease;
        display: flex;
        flex-direction: column;
      }
      .atopile-demo-layout-shell #layer-panel.collapsed {
        transform: translateX(100%);
      }
      .layer-panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 12px;
        font-weight: 600;
        font-size: 13px;
        color: var(--text-primary);
        border-bottom: 1px solid var(--border);
        flex-shrink: 0;
        position: relative;
      }
      .layer-panel-header::after {
        content: "";
        position: absolute;
        bottom: -1px;
        left: 12px;
        right: 12px;
        height: 1px;
        background: var(--border-accent);
      }
      .layer-collapse-btn {
        cursor: pointer;
        opacity: 0.5;
        font-size: 10px;
        transition: opacity 0.15s, color 0.15s;
        color: var(--text-secondary);
      }
      .layer-collapse-btn:hover {
        opacity: 1;
        color: var(--accent);
      }
      .layer-expand-tab {
        display: none;
        position: absolute;
        top: 50%;
        right: 0;
        transform: translateY(-50%);
        writing-mode: vertical-rl;
        background: var(--surface);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--border);
        border-right: none;
        border-radius: 4px 0 0 4px;
        padding: 10px 5px;
        cursor: pointer;
        font: 600 11px/1.2 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        color: var(--accent);
        z-index: 8;
        transition: background 0.15s;
      }
      .layer-expand-tab:hover {
        background: var(--accent-glow);
      }
      .layer-expand-tab.visible {
        display: block;
      }
      .layer-panel-content {
        display: flex;
        flex-direction: column;
        overflow-y: auto;
        padding: 4px 0;
        flex: 1;
      }
      .layer-panel-content::-webkit-scrollbar {
        width: 4px;
      }
      .layer-panel-content::-webkit-scrollbar-track {
        background: transparent;
      }
      .layer-panel-content::-webkit-scrollbar-thumb {
        background: rgba(255,255,255,0.08);
        border-radius: 2px;
      }
      .layer-panel-content::-webkit-scrollbar-thumb:hover {
        background: rgba(255,255,255,0.14);
      }
      .layer-row,
      .layer-group-header {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 3px 12px;
        cursor: pointer;
        transition: background 0.15s, color 0.15s, opacity 0.12s;
      }
      .layer-group-header:hover {
        background: rgba(224,160,56,0.06);
        color: var(--text-primary);
      }
      .layer-swatch {
        display: inline-block;
        width: 12px;
        height: 4px;
        border-radius: 2px;
        flex-shrink: 0;
      }
      .layer-chevron {
        font-size: 10px;
        width: 10px;
        color: var(--text-secondary);
        text-align: center;
        flex-shrink: 0;
      }
      .layer-group-name,
      .layer-label {
        flex: 1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .layer-group-header {
        font-weight: 600;
        font-size: 11px;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        color: var(--text-secondary);
      }
      .layer-group-children {
        padding-left: 22px;
        overflow: hidden;
        transition: max-height 0.2s ease;
        flex-shrink: 0;
      }
      .layer-row {
        padding: 4px 12px;
        border-left: 2px solid transparent;
      }
      .layer-row:hover {
        background: rgba(224,160,56,0.06);
      }
      .layer-top-level {
        padding-left: 22px;
      }
      .atopile-demo-model-surface {
        background:
          radial-gradient(circle at 50% 28%, rgba(255, 255, 255, 0.035), transparent 26%),
          linear-gradient(180deg, rgba(255,255,255,0.025), rgba(255,255,255,0));
      }
      .atopile-demo-model-surface model-viewer {
        width: 100%;
        height: 100%;
        --poster-color: transparent;
        background: transparent;
      }
      .atopile-demo-loading,
      .atopile-demo-error {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 24px;
        z-index: 4;
        background: rgba(5, 10, 14, 0.55);
        backdrop-filter: blur(12px);
      }
      .atopile-demo-loading-card,
      .atopile-demo-error-card {
        background: var(--demo-panel-strong);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 18px;
        padding: 18px 22px;
        max-width: 320px;
      }
      .atopile-demo-spinner {
        width: 32px;
        height: 32px;
        margin: 0 auto 12px;
        border-radius: 50%;
        border: 2px solid rgba(255,255,255,0.14);
        border-top-color: var(--demo-accent);
        animation: atopile-demo-spin 0.8s linear infinite;
      }
      .atopile-demo-error-card {
        color: #ffd2cb;
      }
      @keyframes atopile-demo-spin {
        to { transform: rotate(360deg); }
      }
      @keyframes initial-loading-spin {
        to { transform: rotate(360deg); }
      }
      @keyframes status-busy-spin {
        to { transform: rotate(360deg); }
      }
      @media (max-width: 920px) {
        .atopile-demo-pane {
          min-height: 360px;
        }
        .atopile-demo-layout-shell .layout-viewport {
          inset: 0 170px 32px 0;
        }
        .atopile-demo-layout-shell #layer-panel {
          width: 170px;
        }
      }
    `;
    document.head.appendChild(style);
}

async function loadManifest(assetBase: string, manifest: MountOptions["manifest"]): Promise<DemoManifest> {
    if (manifest && typeof manifest === "object") return manifest;
    const path = typeof manifest === "string" ? manifest : DEFAULT_MANIFEST;
    const response = await fetch(new URL(path, `${assetBase}/`).toString());
    if (!response.ok) {
        throw new Error(`Failed to load demo manifest (${response.status})`);
    }
    return await response.json() as DemoManifest;
}

function resolveTarget(target: HTMLElement | string): HTMLElement {
    if (typeof target !== "string") return target;
    const element = document.querySelector<HTMLElement>(target);
    if (!element) {
        throw new Error(`Unable to find mount target: ${target}`);
    }
    return element;
}

function normalizeAssetBase(assetBase?: string): string {
    if (!assetBase) {
        return DEFAULT_ASSET_BASE;
    }
    return assetBase.replace(/\/$/, "");
}

async function fetchLayoutModel(assetBase: string, manifest: DemoManifest): Promise<RenderModel> {
    const response = await fetch(new URL(manifest.layoutModelPath, `${assetBase}/`).toString());
    if (!response.ok) {
        throw new Error(`Failed to load layout model (${response.status})`);
    }
    return await response.json() as RenderModel;
}

function renderFailure(root: HTMLElement, message: string): void {
    const failure = document.createElement("div");
    failure.className = "atopile-demo-error";
    failure.innerHTML = `<div class="atopile-demo-error-card">${message}</div>`;
    root.appendChild(failure);
}

function createEnvironmentMap(renderer: THREE.WebGLRenderer): THREE.Texture {
    const pmrem = new THREE.PMREMGenerator(renderer);
    const envScene = new THREE.Scene();
    const sky = new THREE.Mesh(
        new THREE.SphereGeometry(20, 32, 16),
        new THREE.MeshBasicMaterial({
            color: new THREE.Color("#b8b2a8"),
            side: THREE.BackSide,
        }),
    );
    envScene.add(sky);
    const warm = new THREE.PointLight(0xffddb0, 14, 0, 2);
    warm.position.set(7, 8, 5);
    envScene.add(warm);
    const accent = new THREE.PointLight(0xff8a32, 5.5, 0, 2);
    accent.position.set(-3, 3.5, 9);
    envScene.add(accent);
    const cool = new THREE.PointLight(0x8cb9e6, 6, 0, 2);
    cool.position.set(-8, 6, -10);
    envScene.add(cool);
    const envTarget = pmrem.fromScene(envScene);
    const texture = envTarget.texture;
    pmrem.dispose();
    envScene.clear();
    return texture;
}

function looksLikeBoardSilkscreen(materialName: string, meshName: string): boolean {
    const material = materialName.toLowerCase();
    const mesh = meshName.toLowerCase();
    return mesh.includes("silkscreen") || material === "mat_22" || material === "mat_23";
}

function buildBackgroundGrid(bounds: THREE.Box3): THREE.Object3D {
    const spanX = Math.max(bounds.max.x - bounds.min.x, 1);
    const spanZ = Math.max(bounds.max.z - bounds.min.z, 1);
    const baseCellSize = 14;
    const majorCellInterval = 3;

    const targetSpan = Math.max(Math.max(spanX, spanZ) + baseCellSize * 4, baseCellSize * 6);
    const baseDivisions = Math.max(
        majorCellInterval * 2,
        Math.ceil(targetSpan / baseCellSize),
    );
    const spanDivisions = Math.ceil(baseDivisions / majorCellInterval) * majorCellInterval;

    const width = spanDivisions * baseCellSize;
    const height = spanDivisions / majorCellInterval;
    const floorHeight = bounds.max.y - bounds.min.y;
    const floorY = bounds.min.y - Math.max(floorHeight * 0.08, 0.02);

    const minorGrid = new THREE.GridHelper(width, spanDivisions, 0x202a36, 0x101922);
    minorGrid.material.opacity = 0.2;
    minorGrid.material.transparent = true;
    minorGrid.position.y = floorY;
    minorGrid.material.depthWrite = false;

    const majorGrid = new THREE.GridHelper(width, height, 0x2a3b4f, 0x2a3b4f);
    majorGrid.material.opacity = 0.4;
    majorGrid.material.transparent = true;
    majorGrid.position.y = floorY;
    majorGrid.material.depthWrite = false;

    const grid = new THREE.Group();
    grid.add(majorGrid, minorGrid);
    return grid;
}

function applyBoardMaterialStyle(node: THREE.Mesh, material: THREE.Material): void {
    const meshName = node.name.toLowerCase();
    const materialName = material.name.toLowerCase();

    if (looksLikeBoardSilkscreen(materialName, meshName)) {
        const overlay = new THREE.MeshBasicMaterial({
            color: new THREE.Color("#f4f3ea"),
            side: THREE.DoubleSide,
            toneMapped: false,
            transparent: false,
            depthWrite: false,
            polygonOffset: true,
            polygonOffsetFactor: -4,
            polygonOffsetUnits: -4,
        });
        node.material = Array.isArray(node.material)
            ? (node.material as THREE.Material[]).map(() => overlay.clone())
            : overlay;
        node.renderOrder = 10;
        return;
    }

    if (!(material instanceof THREE.MeshStandardMaterial)) {
        return;
    }

    if (materialName === "mat_24" || materialName === "mat_25") {
        material.color = new THREE.Color("#161719");
        material.roughness = 0.88;
        material.metalness = 0.01;
        material.envMapIntensity = 0.035;
        material.opacity = 1;
        material.transparent = false;
        material.needsUpdate = true;
        return;
    }

    if (materialName === "mat_26" || materialName === "mat_6") {
        material.color = new THREE.Color("#202225");
        material.roughness = 0.9;
        material.metalness = 0.01;
        material.envMapIntensity = 0.03;
        material.needsUpdate = true;
        return;
    }

    if (materialName === "mat_20" || materialName === "mat_21") {
        material.color = new THREE.Color(
            materialName === "mat_20" ? "#c8a24a" : "#c7ccd3",
        );
        material.roughness = materialName === "mat_20" ? 0.42 : 0.3;
        material.metalness = 0.88;
        material.envMapIntensity = materialName === "mat_20" ? 0.22 : 0.16;
        material.needsUpdate = true;
        return;
    }

    material.envMapIntensity = 0.08;
    material.roughness = Math.max(material.roughness, 0.72);
    material.metalness = Math.min(material.metalness, 0.28);
    material.needsUpdate = true;
}

async function mountThreeViewer(surface: HTMLElement, modelUrl: string): Promise<() => void> {
    const canvas = document.createElement("canvas");
    canvas.style.width = "100%";
    canvas.style.height = "100%";
    canvas.style.display = "block";
    surface.appendChild(canvas);

    const renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
    });
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.22;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(34, 1, 0.0001, 10);
    camera.position.set(0, 45, 120);
    scene.add(camera);

    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping = true;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.8;
    controls.enablePan = false;
    controls.minDistance = 20;
    controls.maxDistance = 500;

    const envMap = createEnvironmentMap(renderer);
    scene.environment = envMap;

    const hemi = new THREE.HemisphereLight(0xe7dccd, 0x0b0d10, 1.0);
    scene.add(hemi);

    const key = new THREE.DirectionalLight(0xffe4bd, 2.4);
    key.position.set(46, 72, 34);
    scene.add(key);

    const fill = new THREE.DirectionalLight(0x9bb8d4, 0.35);
    fill.position.set(-54, 28, -56);
    scene.add(fill);

    const rim = new THREE.DirectionalLight(0xfff1dc, 0.28);
    rim.position.set(-12, 18, 62);
    scene.add(rim);

    const glow = new THREE.PointLight(0xff8a32, 0.7, 0, 2);
    glow.position.set(-28, 22, 18);
    scene.add(glow);

    const glowSecondary = new THREE.PointLight(0xff671f, 0.4, 0, 2);
    glowSecondary.position.set(32, 14, -6);
    scene.add(glowSecondary);

    const loader = new GLTFLoader();
    loader.setMeshoptDecoder(MeshoptDecoder);
    const gltf = await loader.loadAsync(modelUrl);
    const root = gltf.scene;
    scene.add(root);

    root.traverse((node) => {
        if (!(node instanceof THREE.Mesh)) return;
        node.castShadow = false;
        node.receiveShadow = false;
        const materials = Array.isArray(node.material) ? node.material : [node.material];
        for (const material of materials) {
            if (!material) continue;
            applyBoardMaterialStyle(node, material);
        }
    });

    const bounds = new THREE.Box3().setFromObject(root);
    const center = bounds.getCenter(new THREE.Vector3());
    const size = bounds.getSize(new THREE.Vector3());
    root.position.sub(center);
    const centeredBounds = bounds.clone().translate(new THREE.Vector3(-center.x, -center.y, -center.z));
    scene.add(buildBackgroundGrid(centeredBounds));

    let currentRadius = 0.01;

    const setTopDownView = () => {
        const distance = currentRadius * 2.35;
        camera.up.set(0, 0, -1);
        camera.position.set(0, distance, 0.00001);
        controls.target.set(0, 0, 0);
        camera.lookAt(0, 0, 0);
        controls.update();
    };

    const setPerspectiveView = () => {
        camera.up.set(0, 1, 0);
        const verticalFov = THREE.MathUtils.degToRad(camera.fov);
        const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * camera.aspect);
        const distance = 1.12 * Math.max(
            currentRadius / Math.tan(verticalFov / 2),
            currentRadius / Math.tan(horizontalFov / 2),
        );
        const viewDirection = new THREE.Vector3(0.72, 1.15, 0.88).normalize();
        camera.position.copy(viewDirection.multiplyScalar(distance));
        controls.target.set(0, 0, 0);
        camera.lookAt(0, 0, 0);
        controls.update();
    };

    window.__ATOPILE_DEMO_SET_TOP_DOWN__ = setTopDownView;

    const resize = () => {
        const rect = surface.getBoundingClientRect();
        const width = Math.max(1, Math.round(rect.width));
        const height = Math.max(1, Math.round(rect.height));
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        currentRadius = Math.max(bounds.getBoundingSphere(new THREE.Sphere()).radius, 0.001);
        camera.near = Math.max(currentRadius / 200, 0.00001);
        camera.far = Math.max(currentRadius * 40, 1);
        camera.updateProjectionMatrix();
        controls.minDistance = currentRadius * 0.7;
        controls.maxDistance = currentRadius * 5;
        setPerspectiveView();
    };
    resize();
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(surface);

    let disposed = false;
    const animate = () => {
        if (disposed) return;
        controls.update();
        renderer.render(scene, camera);
        window.requestAnimationFrame(animate);
    };
    animate();

    return () => {
        disposed = true;
        window.__ATOPILE_DEMO_SET_TOP_DOWN__ = null;
        resizeObserver.disconnect();
        controls.dispose();
        envMap.dispose();
        renderer.dispose();
        surface.replaceChildren();
    };
}

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

let panelCollapsed = false;
const collapsedGroups = new Set<string>();
let objectTypesExpanded = false;
let textShapesExpanded = false;

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

export async function mount(target: HTMLElement | string, options: MountOptions = {}): Promise<void> {
    ensureStyles();
    window.__ATOPILE_DEMO_READY__ = false;
    window.__ATOPILE_DEMO_STATE__ = { layoutLoaded: false, modelLoaded: false, error: null };

    const root = resolveTarget(target);
    const assetBase = normalizeAssetBase(options.assetBase);
    const manifest = await loadManifest(assetBase, options.manifest);

    root.replaceChildren();
    root.classList.add("atopile-demo-root");

    const hero = document.createElement("div");
    hero.className = "atopile-demo-hero";
    hero.innerHTML = `
      <div>
        <h2 class="atopile-demo-title">${manifest.title ?? "Interactive PCB Demo"}</h2>
        <p class="atopile-demo-subtitle">${manifest.subtitle ?? "Read-only layout plus a polished 3D board model."}</p>
      </div>
      <div class="atopile-demo-badge">Marketing Embed Preview</div>
    `;

    const content = document.createElement("div");
    content.className = "atopile-demo-content";

    const layoutPane = document.createElement("section");
    layoutPane.className = "atopile-demo-pane";
    layoutPane.dataset.pane = "layout";
    layoutPane.innerHTML = `
      <div class="atopile-demo-pane-header"><strong>Layout</strong> Read only</div>
      <div class="atopile-demo-layout-shell">
        <div class="layout-viewport">
          <div id="editor-canvas"></div>
          <div id="vignette"></div>
        </div>
        <div id="initial-loading" role="status" aria-live="polite" aria-busy="true">
          <div class="initial-loading-content">
            <div class="initial-loading-spinner"></div>
            <div class="initial-loading-message">Loading PCB</div>
            <div class="initial-loading-subtext">Building scene geometry...</div>
          </div>
        </div>
        <div id="layer-panel"></div>
        <div id="status">
          <span id="status-coords"></span>
          <span id="status-busy" aria-hidden="true">
            <span class="status-busy-spinner"></span>
            Syncing...
          </span>
          <span id="status-fps"></span>
          <span id="status-help">Scroll zoom · Middle-click pan · Click group/select · Shift-drag box-select · Double-click single · Esc clear · R rotate · F flip · Ctrl+Z undo · Ctrl+Shift+Z redo</span>
        </div>
      </div>
    `;

    const modelPane = document.createElement("section");
    modelPane.className = "atopile-demo-pane";
    modelPane.dataset.pane = "model";
    modelPane.innerHTML = `
      <div class="atopile-demo-pane-header"><strong>3D</strong> Interactive model</div>
      <div class="atopile-demo-model-surface"></div>
      <div class="atopile-demo-loading" data-role="model-loading">
        <div class="atopile-demo-loading-card">
          <div class="atopile-demo-spinner"></div>
          <div>Loading 3D viewer...</div>
        </div>
      </div>
    `;

    content.appendChild(layoutPane);
    content.appendChild(modelPane);
    root.append(hero, content);

    const layoutShell = layoutPane.querySelector<HTMLElement>(".atopile-demo-layout-shell");
    const layoutSurface = layoutPane.querySelector<HTMLElement>("#editor-canvas");
    const layoutInitialLoading = layoutPane.querySelector<HTMLElement>("#initial-loading");
    const modelSurface = modelPane.querySelector<HTMLElement>(".atopile-demo-model-surface");
    const modelLoading = modelPane.querySelector<HTMLElement>("[data-role='model-loading']");
    if (!layoutShell || !layoutSurface || !layoutInitialLoading || !modelSurface || !modelLoading) {
        throw new Error("Demo bundle failed to initialize");
    }

    const layoutViewer = new StaticLayoutViewer(layoutSurface);
    let disposeModelViewer: (() => void) | null = null;

    try {
        const layoutModel = await fetchLayoutModel(assetBase, manifest);
        const hiddenLayoutLayers = computeDemoHiddenLayers(
            layoutModel.layers,
            manifest.hiddenLayoutLayers ?? [],
        );
        layoutViewer.setModel(layoutModel);
        layoutViewer.setHiddenLayers(hiddenLayoutLayers);
        renderLayerSelector(layoutShell, layoutViewer, hiddenLayoutLayers);
        layoutInitialLoading.remove();
        setDemoState({ layoutLoaded: true });

        disposeModelViewer = await mountThreeViewer(
            modelSurface,
            new URL(manifest.modelPath, `${assetBase}/`).toString(),
        );
        modelLoading.remove();
        setDemoState({ modelLoaded: true });
    } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to initialize demo";
        disposeModelViewer?.();
        layoutViewer.destroy();
        renderFailure(root, message);
        setDemoState({ error: message });
        throw error;
    }
}

const demoApi = { mount };
Object.assign(window, { AtopileDemo: demoApi });
