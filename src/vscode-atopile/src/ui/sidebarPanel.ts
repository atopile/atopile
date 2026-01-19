/**
 * Sidebar Panel - WebviewViewProvider for the React-based sidebar.
 *
 * Displays action buttons and build status in a React webview.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { getExtension } from '../common/vscodeapi';
import { traceInfo, traceError } from '../common/log/logging';
import { buildStateManager } from '../common/buildState';
import { getButtons } from './buttons';

function getNonce(): string {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}

/**
 * Find the webview assets in the resources directory.
 */
function findWebviewAssets(extensionPath: string, webviewName: string): { js: string | null; css: string | null; baseCss: string | null } {
    const webviewsDir = path.join(extensionPath, 'resources', 'webviews');

    if (!fs.existsSync(webviewsDir)) {
        // Development mode: check webviews/dist
        const devDir = path.join(extensionPath, 'webviews', 'dist');
        if (!fs.existsSync(devDir)) {
            return { js: null, css: null, baseCss: null };
        }

        const jsFile = path.join(devDir, `${webviewName}.js`);
        const cssFile = path.join(devDir, `${webviewName}.css`);
        const baseCssFile = path.join(devDir, 'index.css');

        return {
            js: fs.existsSync(jsFile) ? jsFile : null,
            css: fs.existsSync(cssFile) ? cssFile : null,
            baseCss: fs.existsSync(baseCssFile) ? baseCssFile : null,
        };
    }

    const jsFile = path.join(webviewsDir, `${webviewName}.js`);
    const cssFile = path.join(webviewsDir, `${webviewName}.css`);
    const baseCssFile = path.join(webviewsDir, 'index.css');

    return {
        js: fs.existsSync(jsFile) ? jsFile : null,
        css: fs.existsSync(cssFile) ? cssFile : null,
        baseCss: fs.existsSync(baseCssFile) ? baseCssFile : null,
    };
}

export class SidebarPanelProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'atopile.project';

    private _view?: vscode.WebviewView;

    constructor(private readonly _extensionUri: vscode.Uri) {
        // Subscribe to build state changes
        buildStateManager.onDidChangeBuilds(() => {
            this.updateBuilds();
        });

        buildStateManager.onDidChangeConnection(() => {
            this.updateBuilds();
        });
    }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        _context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ): void {
        this._view = webviewView;

        const extensionPath = this._extensionUri.fsPath;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [
                vscode.Uri.file(path.join(extensionPath, 'resources', 'webviews')),
                vscode.Uri.file(path.join(extensionPath, 'webviews', 'dist')),
            ],
        };

        webviewView.webview.html = this.getHtmlContent(webviewView.webview);

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async (message) => {
            switch (message.type) {
                case 'ready':
                    this.sendActionButtons();
                    this.updateBuilds();
                    break;

                case 'executeCommand':
                    await vscode.commands.executeCommand(message.command);
                    break;

                case 'selectBuild':
                    buildStateManager.selectBuild(message.buildName);
                    break;

                case 'selectStage':
                    buildStateManager.selectBuild(message.buildName);
                    buildStateManager.selectStage(message.stageName);
                    // Focus the log viewer panel
                    await vscode.commands.executeCommand('atopile.logViewer.focus');
                    break;
            }
        });
    }

    private sendActionButtons(): void {
        if (!this._view) return;

        const buttons = getButtons().map(btn => ({
            id: btn.command.getCommandName(),
            label: btn.description,
            icon: btn.icon.id,
            tooltip: btn.tooltip,
        }));

        this._view.webview.postMessage({
            type: 'updateActionButtons',
            data: { buttons },
        });
    }

    private updateBuilds(): void {
        if (!this._view) return;

        this._view.webview.postMessage({
            type: 'updateBuilds',
            data: {
                builds: buildStateManager.getBuilds(),
                isConnected: buildStateManager.isConnected,
            },
        });
    }

    private getHtmlContent(webview: vscode.Webview): string {
        const extensionPath = this._extensionUri.fsPath;
        const assets = findWebviewAssets(extensionPath, 'sidebar');
        const nonce = getNonce();

        if (!assets.js) {
            return this.getNotBuiltHtml();
        }

        const jsUri = webview.asWebviewUri(vscode.Uri.file(assets.js));
        const baseCssUri = assets.baseCss ? webview.asWebviewUri(vscode.Uri.file(assets.baseCss)) : null;
        const cssUri = assets.css ? webview.asWebviewUri(vscode.Uri.file(assets.css)) : null;

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
    ">
    <title>Atopile</title>
    ${baseCssUri ? `<link rel="stylesheet" href="${baseCssUri}">` : ''}
    ${cssUri ? `<link rel="stylesheet" href="${cssUri}">` : ''}
</head>
<body>
    <div id="root"></div>
    <script nonce="${nonce}" type="module" src="${jsUri}"></script>
</body>
</html>`;
    }

    private getNotBuiltHtml(): string {
        return `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            background: var(--vscode-sideBar-background);
            color: var(--vscode-foreground);
            font-family: var(--vscode-font-family);
            text-align: center;
            padding: 16px;
        }
        code {
            background: var(--vscode-textCodeBlock-background);
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div>
        <p>Webview not built.</p>
        <p>Run <code>npm run build:webviews</code></p>
    </div>
</body>
</html>`;
    }
}

// Exported activate/deactivate
export async function activate(context: vscode.ExtensionContext) {
    const provider = new SidebarPanelProvider(context.extensionUri);

    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(SidebarPanelProvider.viewType, provider)
    );

    // Start polling for build updates
    buildStateManager.startPolling(500);

    traceInfo('SidebarPanel: activated');
}

export function deactivate() {
    buildStateManager.stopPolling();
    buildStateManager.dispose();
}
