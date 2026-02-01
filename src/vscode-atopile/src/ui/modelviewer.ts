import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { onThreeDModelChanged, onThreeDModelStatusChanged, getCurrentThreeDModel, getThreeDModelStatus } from '../common/3dmodel';
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

        if (!model || !fs.existsSync(model.path) || status.state === 'building') {
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
        const modelWebUri = this.getWebviewUri(webview, model.path);

        return buildHtml({
            title: '3D Model Preview',
            scripts: [{ type: 'module', src: scriptUri.toString() }],
            styles: `
                #container {height: 100%; width: 100%;}
                model-viewer {height: 100%; width: 100%; display: block;}
            `,
            body: `
                <div id="container">
                    <model-viewer
                        id="mv"
                        src="${modelWebUri}"
                        camera-controls
                        tone-mapping="neutral"
                        exposure="1.2"
                        shadow-intensity="0.7"
                        shadow-softness="0.8"
                    ></model-viewer>
                </div>
            `,
        });
    }

    protected getLocalResourceRoots(): vscode.Uri[] {
        const roots = super.getLocalResourceRoots();
        const model = getCurrentThreeDModel();
        if (model && fs.existsSync(model.path)) {
            roots.push(vscode.Uri.file(path.dirname(model.path)));
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
    await modelViewer.open();
}

export function closeModelViewerPreview() {
    modelViewer?.dispose();
    modelViewer = undefined;
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
