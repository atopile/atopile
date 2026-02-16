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
                        position: fixed; top: 0; right: 0; bottom: 0;
                        width: 140px;
                        background: var(--vscode-sideBar-background, rgba(30,30,30,0.95));
                        border-left: 1px solid var(--vscode-panel-border, #444);
                        border-radius: 4px 0 0 4px;
                        z-index: 20;
                        font: 11px/1.4 monospace;
                        color: var(--vscode-foreground, #ccc);
                        transform: translateX(0);
                        transition: transform 0.2s ease;
                        display: flex;
                        flex-direction: column;
                    }
                    #layer-panel.collapsed {
                        transform: translateX(100%);
                    }
                    .layer-panel-header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 6px 8px;
                        font-weight: bold;
                        font-size: 12px;
                        border-bottom: 1px solid var(--vscode-panel-border, #444);
                        flex-shrink: 0;
                    }
                    .layer-collapse-btn {
                        cursor: pointer;
                        opacity: 0.6;
                        font-size: 10px;
                    }
                    .layer-collapse-btn:hover { opacity: 1; }
                    .layer-expand-tab {
                        display: none;
                        position: fixed;
                        top: 50%;
                        right: 0;
                        transform: translateY(-50%);
                        writing-mode: vertical-rl;
                        background: var(--vscode-sideBar-background, rgba(30,30,30,0.95));
                        border: 1px solid var(--vscode-panel-border, #444);
                        border-right: none;
                        border-radius: 4px 0 0 4px;
                        padding: 8px 4px;
                        cursor: pointer;
                        font: 11px monospace;
                        color: var(--vscode-foreground, #ccc);
                        z-index: 21;
                    }
                    .layer-expand-tab.visible { display: block; }
                    .layer-panel-content {
                        overflow-y: auto;
                        padding: 4px 0;
                        flex: 1;
                    }
                    .layer-group-header {
                        display: flex;
                        align-items: center;
                        gap: 4px;
                        padding: 2px 8px;
                        cursor: pointer;
                        font-weight: 600;
                        transition: opacity 0.15s;
                    }
                    .layer-group-header:hover { background: var(--vscode-list-hoverBackground, rgba(255,255,255,0.05)); }
                    .layer-chevron {
                        font-size: 10px;
                        width: 10px;
                        text-align: center;
                        flex-shrink: 0;
                    }
                    .layer-group-name { flex: 1; }
                    .layer-group-children { padding-left: 22px; }
                    .layer-row {
                        display: flex;
                        align-items: center;
                        gap: 5px;
                        padding: 1px 8px;
                        cursor: pointer;
                        transition: opacity 0.15s;
                    }
                    .layer-row:hover { background: var(--vscode-list-hoverBackground, rgba(255,255,255,0.05)); }
                    .layer-top-level { padding-left: 22px; }
                    .layer-swatch {
                        display: inline-block;
                        width: 10px; height: 10px;
                        border-radius: 50%;
                        flex-shrink: 0;
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
