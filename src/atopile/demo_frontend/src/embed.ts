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
        --demo-bg: radial-gradient(circle at top left, rgba(255, 204, 112, 0.18), transparent 38%), linear-gradient(160deg, #071018 0%, #10212a 48%, #05090d 100%);
        --demo-panel: rgba(7, 17, 24, 0.78);
        --demo-panel-strong: rgba(9, 19, 28, 0.92);
        --demo-border: rgba(255, 255, 255, 0.12);
        --demo-text: #ecf3f8;
        --demo-text-muted: rgba(236, 243, 248, 0.72);
        --demo-accent: #ffc768;
        --demo-shadow: 0 28px 90px rgba(0, 0, 0, 0.42);
        color: var(--demo-text);
        font-family: "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif;
        background: var(--demo-bg);
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
        background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0));
        border-bottom: 1px solid rgba(255,255,255,0.08);
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
        background: rgba(255, 199, 104, 0.14);
        color: var(--demo-accent);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
      }
      .atopile-demo-content {
        display: grid;
        grid-template-rows: minmax(320px, 0.95fr) minmax(420px, 1.05fr);
        gap: 1px;
        background: rgba(255, 255, 255, 0.08);
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
        background: rgba(7, 17, 24, 0.72);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255,255,255,0.08);
        font-size: 0.78rem;
        color: var(--demo-text-muted);
      }
      .atopile-demo-pane-header strong {
        color: var(--demo-text);
        font-weight: 600;
      }
      .atopile-demo-layout-surface,
      .atopile-demo-model-surface {
        position: absolute;
        inset: 0;
      }
      .atopile-demo-layout-shell {
        position: absolute;
        inset: 0;
        display: grid;
        grid-template-columns: minmax(0, 1fr) 220px;
      }
      .atopile-demo-layout-surface {
        position: relative;
      }
      .layer-panel {
        position: relative;
        z-index: 2;
        display: flex;
        flex-direction: column;
        gap: 10px;
        padding: 70px 12px 12px;
        background: linear-gradient(180deg, rgba(8, 15, 22, 0.96), rgba(8, 15, 22, 0.88));
        border-left: 1px solid rgba(255,255,255,0.08);
        overflow: auto;
      }
      .layer-panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 0.72rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--demo-text-muted);
      }
      .layer-panel-content {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .layer-row,
      .layer-group-header {
        display: grid;
        grid-template-columns: auto auto minmax(0, 1fr);
        align-items: center;
        gap: 10px;
        font-size: 0.84rem;
        color: var(--demo-text);
        border-radius: 12px;
        padding: 8px 10px;
        cursor: pointer;
        transition: background 120ms ease, opacity 120ms ease;
      }
      .layer-row:hover,
      .layer-group-header:hover {
        background: rgba(255,255,255,0.06);
      }
      .layer-swatch {
        width: 10px;
        height: 10px;
        border-radius: 999px;
        box-shadow: 0 0 0 1px rgba(255,255,255,0.14);
      }
      .layer-chevron {
        width: 12px;
        color: var(--demo-text-muted);
        text-align: center;
      }
      .layer-group-name,
      .layer-label {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .layer-group-children {
        margin-left: 12px;
        display: flex;
        flex-direction: column;
        gap: 6px;
        overflow: hidden;
      }
      .layer-top-level {
        grid-template-columns: auto minmax(0, 1fr);
      }
      .atopile-demo-model-surface {
        background:
          radial-gradient(circle at 30% 24%, rgba(255, 199, 104, 0.22), transparent 20%),
          radial-gradient(circle at 75% 20%, rgba(124, 211, 255, 0.16), transparent 26%),
          linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0));
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
      @media (max-width: 920px) {
        .atopile-demo-pane {
          min-height: 360px;
        }
        .atopile-demo-layout-shell {
          grid-template-columns: 1fr;
          grid-template-rows: minmax(0, 1fr) auto;
        }
        .atopile-demo-layer-panel {
          padding-top: 12px;
          border-left: 0;
          border-top: 1px solid rgba(255,255,255,0.08);
          max-height: 180px;
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
            color: new THREE.Color("#d9e6f2"),
            side: THREE.BackSide,
        }),
    );
    envScene.add(sky);
    const warm = new THREE.PointLight(0xffe2b8, 25, 0, 2);
    warm.position.set(7, 10, 6);
    envScene.add(warm);
    const cool = new THREE.PointLight(0x9dd6ff, 18, 0, 2);
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
        material.color = new THREE.Color("#111111");
        material.roughness = 0.96;
        material.metalness = 0.02;
        material.envMapIntensity = 0.04;
        material.opacity = 0.94;
        material.transparent = true;
        material.needsUpdate = true;
        return;
    }

    if (materialName === "mat_26" || materialName === "mat_6") {
        material.color = new THREE.Color("#161616");
        material.roughness = 0.98;
        material.metalness = 0.0;
        material.envMapIntensity = 0.03;
        material.needsUpdate = true;
        return;
    }

    if (materialName === "mat_20" || materialName === "mat_21") {
        material.color = new THREE.Color(
            materialName === "mat_20" ? "#c79a2b" : "#c9ced4",
        );
        material.roughness = 0.34;
        material.metalness = 0.9;
        material.envMapIntensity = materialName === "mat_20" ? 0.28 : 0.18;
        material.needsUpdate = true;
        return;
    }

    material.envMapIntensity = 0.18;
    material.roughness = Math.max(material.roughness, 0.72);
    material.metalness = Math.min(material.metalness, 0.35);
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
    renderer.toneMappingExposure = 0.92;
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

    const hemi = new THREE.HemisphereLight(0xe7f1ff, 0x0c0f12, 1.8);
    scene.add(hemi);

    const key = new THREE.DirectionalLight(0xfff1d6, 3.4);
    key.position.set(80, 110, 70);
    scene.add(key);

    const fill = new THREE.DirectionalLight(0x9ccfff, 1.6);
    fill.position.set(-70, 40, -80);
    scene.add(fill);

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

function rgbaToCss([r, g, b, a]: [number, number, number, number]): string {
    return `rgba(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)}, ${a.toFixed(3)})`;
}

interface LayerGroup {
    group: string;
    layers: LayerModel[];
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

function renderLayerSelector(
    container: HTMLElement,
    layoutViewer: StaticLayoutViewer,
    initiallyHidden: string[],
): void {
    const hiddenLayers = new Set(initiallyHidden);
    const panel = document.createElement("aside");
    panel.className = "layer-panel";

    const header = document.createElement("div");
    header.className = "layer-panel-header";
    header.innerHTML = "<span>Layers</span>";
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

    for (const group of groups) {
        const groupIds = group.layers.map((layer) => layer.id);
        let collapsed = false;

        const groupRow = document.createElement("div");
        groupRow.className = "layer-group-header";

        const chevron = document.createElement("span");
        chevron.className = "layer-chevron";
        chevron.textContent = "▾";

        const swatch = document.createElement("span");
        swatch.className = "layer-swatch";
        swatch.style.background = colorToCss(groupIds[0]!, layerById);

        const label = document.createElement("span");
        label.className = "layer-group-name";
        label.textContent = group.group;

        groupRow.append(chevron, swatch, label);

        const childContainer = document.createElement("div");
        childContainer.className = "layer-group-children";

        const childRows: Array<{ id: string; row: HTMLElement }> = [];
        for (const layer of group.layers) {
            const row = document.createElement("div");
            row.className = "layer-row";

            const spacer = document.createElement("span");
            spacer.className = "layer-chevron";
            spacer.textContent = "";

            const childSwatch = document.createElement("span");
            childSwatch.className = "layer-swatch";
            childSwatch.style.background = rgbaToCss(layer.color);

            const childLabel = document.createElement("span");
            childLabel.className = "layer-label";
            childLabel.textContent = layer.label ?? layer.id;

            row.append(spacer, childSwatch, childLabel);
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
            collapsed = !collapsed;
            chevron.textContent = collapsed ? "▸" : "▾";
            childContainer.style.display = collapsed ? "none" : "flex";
        });

        content.append(groupRow, childContainer);
    }

    for (const layer of topLevel) {
        const row = document.createElement("div");
        row.className = "layer-row layer-top-level";

        const swatch = document.createElement("span");
        swatch.className = "layer-swatch";
        swatch.style.background = rgbaToCss(layer.color);

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

    container.appendChild(panel);
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
        <div class="atopile-demo-layout-surface"></div>
      </div>
      <div class="atopile-demo-loading" data-role="layout-loading">
        <div class="atopile-demo-loading-card">
          <div class="atopile-demo-spinner"></div>
          <div>Loading layout model...</div>
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

    const layoutSurface = layoutPane.querySelector<HTMLElement>(".atopile-demo-layout-surface");
    const modelSurface = modelPane.querySelector<HTMLElement>(".atopile-demo-model-surface");
    const layoutLoading = layoutPane.querySelector<HTMLElement>("[data-role='layout-loading']");
    const modelLoading = modelPane.querySelector<HTMLElement>("[data-role='model-loading']");
    if (!layoutSurface || !modelSurface || !layoutLoading || !modelLoading) {
        throw new Error("Demo bundle failed to initialize");
    }

    const layoutViewer = new StaticLayoutViewer(layoutSurface);
    let disposeModelViewer: (() => void) | null = null;

    try {
        const layoutModel = await fetchLayoutModel(assetBase, manifest);
        layoutViewer.setModel(layoutModel);
        layoutViewer.setHiddenLayers(manifest.hiddenLayoutLayers ?? []);
        const layoutShell = layoutPane.querySelector<HTMLElement>(".atopile-demo-layout-shell");
        if (layoutShell) {
            renderLayerSelector(layoutShell, layoutViewer, manifest.hiddenLayoutLayers ?? []);
        }
        layoutLoading.remove();
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
