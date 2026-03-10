import Handlebars from "handlebars";

import { mountCodePreview } from "./code-preview";
import { mountLayout } from "./layout";
import { mountModel3D } from "./model3d";
import type { DemoManifest, MountOptions } from "./shared";
import stylesSource from "../build/styles";
import templateSource from "../build/template";

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

const DEFAULT_MANIFEST = "demo-manifest.json";
const renderTemplate = Handlebars.compile(templateSource);
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
    style.textContent = stylesSource;
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

function renderFailure(root: HTMLElement, message: string): void {
    const failure = document.createElement("div");
    failure.className = "atopile-demo-error";
    failure.innerHTML = `<div class="atopile-demo-error-card">${message}</div>`;
    root.appendChild(failure);
}

export async function mount(target: HTMLElement | string, options: MountOptions = {}): Promise<void> {
    ensureStyles();
    window.__ATOPILE_DEMO_READY__ = false;
    window.__ATOPILE_DEMO_STATE__ = { layoutLoaded: false, modelLoaded: false, error: null };

    const root = resolveTarget(target);
    const assetBase = normalizeAssetBase(options.assetBase);
    const manifest = await loadManifest(assetBase, options.manifest);

    const showHero = options.showHero ?? true;

    root.replaceChildren();
    root.classList.add("atopile-demo-root");
    if (!showHero) root.classList.add("atopile-demo-root--no-hero");
    if (!manifest.codePath) root.classList.add("atopile-demo-root--no-code");
    root.innerHTML = renderTemplate({
        title: manifest.title ?? "Interactive PCB Demo",
        subtitle: manifest.subtitle ?? "Read-only layout plus a polished 3D board model.",
    });

    const codeSurface = root.querySelector<HTMLElement>(".atopile-demo-code-surface");
    const layoutShell = root.querySelector<HTMLElement>(".atopile-demo-layout-shell");
    const layoutSurface = root.querySelector<HTMLElement>("#editor-canvas");
    const layoutInitialLoading = root.querySelector<HTMLElement>("#initial-loading");
    const modelSurface = root.querySelector<HTMLElement>(".atopile-demo-model-surface");
    const modelLoading = root.querySelector<HTMLElement>("[data-role='model-loading']");
    if (!layoutShell || !layoutSurface || !layoutInitialLoading || !modelSurface || !modelLoading) {
        throw new Error("Demo bundle failed to initialize");
    }

    let disposeLayoutViewer: (() => void) | null = null;
    let disposeModelViewer: (() => void) | null = null;

    try {
        // Mount code preview (non-blocking)
        if (codeSurface && manifest.codePath) {
            const codeUrl = new URL(manifest.codePath, `${assetBase}/`).toString();
            const filename = manifest.codePath;
            mountCodePreview(codeSurface, codeUrl, filename).catch(err => {
                console.warn("Code preview failed:", err);
            });
        }

        disposeLayoutViewer = await mountLayout(
            layoutShell,
            layoutSurface,
            layoutInitialLoading,
            assetBase,
            manifest,
        );
        setDemoState({ layoutLoaded: true });

        disposeModelViewer = await mountModel3D(
            modelSurface,
            new URL(manifest.modelPath, `${assetBase}/`).toString(),
            { showStats: manifest.showStats },
        );
        modelLoading.remove();
        setDemoState({ modelLoaded: true });
    } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to initialize demo";
        disposeModelViewer?.();
        disposeLayoutViewer?.();
        renderFailure(root, message);
        setDemoState({ error: message });
        throw error;
    }
}

const demoApi = { mount };
Object.assign(window, { AtopileDemo: demoApi });
