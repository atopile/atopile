/**
 * Spec Viewer — read-only panel for rendering modules with requirements.
 *
 * Opens as a standalone webview panel. The React app fetches spec data
 * from the backend GET /api/specs endpoint and renders it.
 */

import * as vscode from 'vscode';
import { BaseWebview, WebviewConfig } from './webview-base';
import { findWebviewAssets, buildWebviewHtml, getWebviewLocalResourceRoots } from './webview-utils';
import { backendServer } from '../common/backendServer';
import { getProjectRoot } from '../common/target';
import { getNonce, getWsOrigin } from '../common/webview';

class SpecViewerWebview extends BaseWebview {
    private extensionUri: vscode.Uri;

    constructor(extensionUri: vscode.Uri) {
        super({
            id: 'spec_viewer',
            title: 'Spec Viewer',
            column: vscode.ViewColumn.Beside,
            enableScripts: true,
        });
        this.extensionUri = extensionUri;
    }

    protected getHtmlContent(webview: vscode.Webview): string {
        const assets = findWebviewAssets(this.extensionUri.fsPath, 'specViewer');
        if (!assets.js) {
            return this.getMissingResourceHtml('spec viewer');
        }

        // Build HTML with backend connection info
        const nonce = getNonce();
        const jsUri = webview.asWebviewUri(vscode.Uri.file(assets.js));
        const baseCssUri = assets.baseCss
            ? webview.asWebviewUri(vscode.Uri.file(assets.baseCss))
            : null;
        const cssUri = assets.css
            ? webview.asWebviewUri(vscode.Uri.file(assets.css))
            : null;

        const apiUrl = backendServer.apiUrl || '';
        const wsOrigin = backendServer.wsUrl ? getWsOrigin(backendServer.wsUrl) : '';
        const projectRoot = getProjectRoot() || '';

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="
        default-src 'none';
        style-src ${webview.cspSource} 'unsafe-inline';
        script-src 'nonce-${nonce}';
        font-src ${webview.cspSource};
        img-src ${webview.cspSource} https: http: data:;
        connect-src ${apiUrl} ${wsOrigin};
    ">
    <title>Spec Viewer</title>
    ${baseCssUri ? `<link rel="stylesheet" href="${baseCssUri}">` : ''}
    ${cssUri ? `<link rel="stylesheet" href="${cssUri}">` : ''}
</head>
<body>
    <div id="root"></div>
    <script nonce="${nonce}">
        window.__ATOPILE_API_URL__ = "${apiUrl}";
        window.__ATOPILE_PROJECT_ROOT__ = "${projectRoot}";
    </script>
    <script nonce="${nonce}" type="module" src="${jsUri}"></script>
</body>
</html>`;
    }

    protected getLocalResourceRoots(): vscode.Uri[] {
        return [
            ...super.getLocalResourceRoots(),
            ...getWebviewLocalResourceRoots(this.extensionUri),
        ];
    }
}

let specViewer: SpecViewerWebview | undefined;

export async function openSpecViewer(extensionUri: vscode.Uri): Promise<void> {
    if (!specViewer) {
        specViewer = new SpecViewerWebview(extensionUri);
    }
    await specViewer.open();
}

export function closeSpecViewer(): void {
    specViewer?.dispose();
    specViewer = undefined;
}

export async function activate(context: vscode.ExtensionContext): Promise<void> {
    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.openSpecViewer', () => {
            openSpecViewer(context.extensionUri);
        })
    );
}

export function deactivate(): void {
    closeSpecViewer();
}
