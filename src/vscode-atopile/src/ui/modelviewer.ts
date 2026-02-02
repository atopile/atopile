import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import {
    onThreeDModelChanged,
    onThreeDModelStatusChanged,
    getCurrentThreeDModel,
    getThreeDModelStatus,
    getOptimizedPath,
    setThreeDModelStatusFromViewer,
    startOptimizationFromViewer,
} from '../common/3dmodel';
import { BaseWebview } from './webview-base';
import { buildHtml } from './html-builder';
import { getAndCheckResource, getResourcesPath } from '../common/resources';

class ModelViewerWebview extends BaseWebview {
    constructor() {
        super({
            id: 'modelviewer_preview',
            title: '3D Model',
            iconName: 'cube-icon.svg',
        });
    }

    protected getHtmlContent(webview: vscode.Webview): string {
        const model = getCurrentThreeDModel();
        const status = getThreeDModelStatus();

        // Determine which GLB path to use based on status
        let modelPath: string | undefined;
        let isBuilding = false;

        if (status.state === 'optimized') {
            // Use optimized version
            modelPath = status.optimizedPath;
        } else if (status.state === 'optimizing') {
            // Show raw while optimizing
            modelPath = status.rawPath;
        } else if (status.state === 'raw_ready') {
            // Show raw GLB
            modelPath = status.rawPath;
        } else if (status.state === 'building') {
            // While building, keep showing existing model if available
            // Prefer optimized > raw > model watcher path
            isBuilding = true;
            if (model?.path) {
                const optimizedPath = model.path.replace(/\.glb$/, '.optimized.glb');
                if (fs.existsSync(optimizedPath)) {
                    modelPath = optimizedPath;
                } else if (fs.existsSync(model.path)) {
                    modelPath = model.path;
                }
            }
        } else if (model?.path) {
            // Fall back to model watcher path
            modelPath = model.path;
        }

        if (status.state === 'failed') {
            return buildHtml({
                title: '3D Model Preview',
                styles: `
                    html, body {height: 100%;}
                    body {display: flex; align-items: center; justify-content: center;}
                    .state {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        gap: 12px;
                        font-family: var(--vscode-font-family);
                        color: var(--vscode-foreground);
                        text-align: center;
                        max-width: 360px;
                    }
                    .icon {
                        width: 0;
                        height: 0;
                        border-left: 16px solid transparent;
                        border-right: 16px solid transparent;
                        border-bottom: 28px solid var(--vscode-warningForeground);
                        position: relative;
                    }
                    .icon::after {
                        content: '!';
                        position: absolute;
                        left: -3px;
                        top: 8px;
                        color: var(--vscode-editor-background);
                        font-weight: 700;
                        font-size: 14px;
                    }
                    .title { font-size: 0.95rem; font-weight: 600; }
                    .message { font-size: 0.85rem; color: var(--vscode-descriptionForeground); }
                `,
                body: `
                    <div class="state">
                        <div class="icon">!</div>
                        <div class="title">3D export failed</div>
                        <div class="message">${status.message}</div>
                    </div>
                `,
            });
        }

        // Show building spinner only if no model path available
        // (when building with existing model, we keep showing the old model)
        if (!modelPath || !fs.existsSync(modelPath)) {
            return buildHtml({
                title: '3D Model Preview',
                styles: `
                    html, body {height: 100%;}
                    body {display: flex; align-items: center; justify-content: center;}
                    .state {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        gap: 12px;
                        font-family: var(--vscode-font-family);
                        color: var(--vscode-foreground);
                        text-align: center;
                        max-width: 360px;
                    }
                    .spinner {
                        width: 36px;
                        height: 36px;
                        border: 3px solid var(--vscode-editorWidget-border);
                        border-top-color: var(--vscode-progressBar-background);
                        border-radius: 50%;
                        animation: spin 1s linear infinite;
                    }
                    .title { font-size: 0.95rem; font-weight: 600; }
                    .message { font-size: 0.85rem; color: var(--vscode-descriptionForeground); }
                    @keyframes spin { to { transform: rotate(360deg); } }
                `,
                body: `
                    <div class="state">
                        <div class="spinner" aria-label="Loading"></div>
                        <div class="title">Generating 3D model</div>
                    </div>
                `,
            });
        }

        const scriptUri = this.getModelViewerScriptUri(webview);
        const modelWebUri = this.getWebviewUri(webview, modelPath);

        // Build status badge - only show when building with existing model
        const statusBadge = (isBuilding && modelPath)
            ? `<div class="status-badge">
                   <span class="badge-spinner"></span>
                   <span>Building...</span>
               </div>`
            : '';

        // Script to auto-fit the camera to the model when it loads
        const autoFrameScript = `
            <script type="module">
                const mv = document.getElementById('mv');
                if (mv) {
                    mv.addEventListener('load', () => {
                        // Update framing to fit the model in view
                        mv.updateFraming();
                    });
                }
            </script>
        `;

        return buildHtml({
            title: '3D Model Preview',
            scripts: [{ type: 'module', src: scriptUri.toString() }],
            styles: `
                #container {height: 100%; width: 100%; position: relative;}
                model-viewer {height: 100%; width: 100%; display: block;}
                .status-badge {
                    position: absolute;
                    bottom: 8px;
                    left: 10px;
                    display: flex;
                    align-items: center;
                    gap: 5px;
                    font-size: 11px;
                    color: var(--vscode-descriptionForeground);
                    opacity: 0.7;
                    z-index: 10;
                    font-family: var(--vscode-font-family);
                }
                .badge-spinner {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    border: 1.5px solid var(--vscode-descriptionForeground);
                    border-top-color: transparent;
                    animation: spin 0.8s linear infinite;
                    opacity: 0.7;
                }
                @keyframes spin { to { transform: rotate(360deg); } }
            `,
            body: `
                <div id="container">
                    <model-viewer
                        id="mv"
                        src="${modelWebUri}"
                        camera-controls
                        min-camera-orbit="auto auto 2%"
                        tone-mapping="neutral"
                        exposure="1.2"
                        shadow-intensity="0.7"
                        shadow-softness="0.8"
                    ></model-viewer>
                    ${statusBadge}
                </div>
                ${autoFrameScript}
            `,
        });
    }

    protected getLocalResourceRoots(): vscode.Uri[] {
        const roots = super.getLocalResourceRoots();
        const model = getCurrentThreeDModel();
        const status = getThreeDModelStatus();

        // Add the model directory for both raw and optimized paths
        if (model && fs.existsSync(model.path)) {
            roots.push(vscode.Uri.file(path.dirname(model.path)));
        }

        // Also add paths from status if they exist (for optimization states)
        if (status.state === 'optimizing' || status.state === 'raw_ready') {
            const rawDir = path.dirname(status.rawPath);
            if (!roots.some((r) => r.fsPath === rawDir)) {
                roots.push(vscode.Uri.file(rawDir));
            }
        } else if (status.state === 'optimized') {
            const optimizedDir = path.dirname(status.optimizedPath);
            if (!roots.some((r) => r.fsPath === optimizedDir)) {
                roots.push(vscode.Uri.file(optimizedDir));
            }
        }

        return roots;
    }

    private getModelViewerScriptUri(webview: vscode.Webview): vscode.Uri {
        return webview.asWebviewUri(vscode.Uri.file(getAndCheckResource('model-viewer/model-viewer.min.js')));
    }

    protected setupPanel(): void {}
}

let modelViewer: ModelViewerWebview | undefined;

export async function openModelViewerPreview() {
    if (!modelViewer) {
        modelViewer = new ModelViewerWebview();
    }

    // Check if we need to start optimization when opening the viewer
    const status = getThreeDModelStatus();
    const model = getCurrentThreeDModel();

    // If we're in idle state with an existing model, check if we need to optimize
    if (status.state === 'idle' && model?.exists && model.path) {
        const optimizedPath = getOptimizedPath(model.path);

        if (fs.existsSync(optimizedPath)) {
            const rawMtime = fs.statSync(model.path).mtimeMs;
            const optimizedMtime = fs.statSync(optimizedPath).mtimeMs;
            if (optimizedMtime >= rawMtime) {
                // Optimized version is up to date
                setThreeDModelStatusFromViewer({ state: 'optimized', rawPath: model.path, optimizedPath });
            } else {
                // Need to re-optimize
                setThreeDModelStatusFromViewer({ state: 'raw_ready', rawPath: model.path });
                startOptimizationFromViewer(model.path);
            }
        } else {
            // No optimized version exists - start optimization
            setThreeDModelStatusFromViewer({ state: 'raw_ready', rawPath: model.path });
            startOptimizationFromViewer(model.path);
        }
    }

    await modelViewer.open();
}

export function closeModelViewerPreview() {
    modelViewer?.dispose();
    modelViewer = undefined;
}

export function isModelViewerOpen(): boolean {
    return modelViewer?.isOpen() ?? false;
}

export async function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        onThreeDModelChanged((_) => {
            if (modelViewer?.isOpen()) {
                openModelViewerPreview();
            }
        }),
    );
    context.subscriptions.push(
        onThreeDModelStatusChanged((_) => {
            if (modelViewer?.isOpen()) {
                openModelViewerPreview();
            }
        }),
    );
}

export function deactivate() {
    closeModelViewerPreview();
}
