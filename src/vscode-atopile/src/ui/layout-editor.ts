import * as vscode from 'vscode';
import { getAndCheckResource } from '../common/resources';
import { backendServer } from '../common/backendServer';
import { getWsOrigin, getNonce } from '../common/webview';
import { BaseWebview } from './webview-base';

class LayoutEditorWebview extends BaseWebview {
    constructor() {
        super({
            id: 'layout_editor',
            title: 'Layout',
            iconName: 'pcb-icon-transparent.svg',
        });
    }

    protected getHtmlContent(webview: vscode.Webview): string {
        const apiUrl = backendServer.apiUrl;
        const wsOrigin = getWsOrigin(backendServer.wsUrl);
        const nonce = getNonce();

        const editorUri = webview.asWebviewUri(
            vscode.Uri.file(getAndCheckResource('layout-editor/editor.js'))
        );

        return /* html */ `
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <meta http-equiv="Content-Security-Policy" content="
                    default-src 'none';
                    style-src 'unsafe-inline';
                    script-src 'nonce-${nonce}' ${webview.cspSource};
                    connect-src ${apiUrl} ${wsOrigin};
                ">
                <title>Layout Editor</title>
                <style>
                    html, body {
                        padding: 0; margin: 0;
                        height: 100%; width: 100%;
                        overflow: hidden;
                        background: var(--vscode-editor-background, #1e1e1e);
                    }
                    canvas { display: block; width: 100%; height: 100%; }
                    #status {
                        position: fixed; bottom: 8px; left: 8px;
                        color: var(--vscode-descriptionForeground, #aaa);
                        font: 12px monospace;
                        pointer-events: none; z-index: 10;
                    }
                    #layer-panel {
                        position: fixed; top: 8px; right: 8px;
                        background: var(--vscode-sideBar-background, rgba(30,30,30,0.9));
                        border: 1px solid var(--vscode-panel-border, #444);
                        border-radius: 4px;
                        padding: 8px;
                        max-height: 80vh;
                        overflow-y: auto;
                        z-index: 20;
                        font: 12px monospace;
                        color: var(--vscode-foreground, #ccc);
                    }
                    .layer-row {
                        display: flex;
                        align-items: center;
                        gap: 6px;
                        padding: 2px 0;
                        cursor: pointer;
                    }
                    .layer-row:hover { color: var(--vscode-list-hoverForeground, #fff); }
                    .layer-swatch {
                        display: inline-block;
                        width: 12px; height: 12px;
                        border-radius: 2px;
                        border: 1px solid var(--vscode-panel-border, #666);
                    }
                </style>
            </head>
            <body>
                <script nonce="${nonce}">
                    window.__LAYOUT_BASE_URL__ = '${apiUrl}';
                    window.__LAYOUT_API_PREFIX__ = '/api/layout';
                    window.__LAYOUT_WS_PATH__ = '/ws/layout';
                </script>
                <canvas id="editor-canvas"></canvas>
                <div id="layer-panel"></div>
                <div id="status">scroll to zoom, middle-click to pan, left-click to select/drag, R rotate, F flip</div>
                <script nonce="${nonce}" type="module" src="${editorUri}"></script>
            </body>
            </html>`;
    }
}

let layoutEditor: LayoutEditorWebview | undefined;

export async function openLayoutEditor() {
    if (!layoutEditor) {
        layoutEditor = new LayoutEditorWebview();
    }
    await layoutEditor.open();
}

export function closeLayoutEditor() {
    layoutEditor?.dispose();
    layoutEditor = undefined;
}

export async function activate(_context: vscode.ExtensionContext) {
    // Nothing extra needed — the webview is opened on demand.
}

export function deactivate() {
    closeLayoutEditor();
}
