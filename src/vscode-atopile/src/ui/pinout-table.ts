import * as vscode from 'vscode';
import { getAndCheckResource } from '../common/resources';
import { backendServer } from '../common/backendServer';
import { getWsOrigin, getNonce } from '../common/webview';
import { BaseWebview } from './webview-base';

class PinoutTableWebview extends BaseWebview {
    constructor() {
        super({
            id: 'pinout_table',
            title: 'Pinout Table',
            iconName: 'pcb-icon-transparent.svg',
        });
    }

    protected getHtmlContent(webview: vscode.Webview): string {
        const apiUrl = backendServer.apiUrl;
        const wsOrigin = getWsOrigin(backendServer.wsUrl);
        const nonce = getNonce();

        const scriptUri = webview.asWebviewUri(
            vscode.Uri.file(getAndCheckResource('webviews/pinoutTable.js'))
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
                <title>Pinout Table</title>
                <style>
                    html, body {
                        padding: 0; margin: 0;
                        height: 100%; width: 100%;
                        overflow: auto;
                        background: var(--vscode-editor-background, #1e1e1e);
                        color: var(--vscode-foreground, #ccc);
                        font-family: var(--vscode-font-family, monospace);
                        font-size: var(--vscode-font-size, 13px);
                    }
                    #root {
                        min-height: 100%;
                    }
                </style>
            </head>
            <body>
                <script nonce="${nonce}">
                    window.__ATOPILE_API_URL__ = '${apiUrl}';
                </script>
                <div id="root"></div>
                <script nonce="${nonce}" type="module" src="${scriptUri}"></script>
            </body>
            </html>`;
    }
}

let pinoutTable: PinoutTableWebview | undefined;

export async function openPinoutTable() {
    if (!pinoutTable) {
        pinoutTable = new PinoutTableWebview();
    }
    await pinoutTable.open();
}

export function closePinoutTable() {
    pinoutTable?.dispose();
    pinoutTable = undefined;
}

export async function activate(_context: vscode.ExtensionContext) {
    // Nothing extra needed — the webview is opened on demand.
}

export function deactivate() {
    closePinoutTable();
}
