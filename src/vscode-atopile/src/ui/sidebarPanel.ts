/**
 * Sidebar Panel - WebviewViewProvider for the React-based sidebar.
 *
 * Displays action buttons and build status in a React webview.
 */

import * as vscode from 'vscode';
import { traceInfo } from '../common/log/logging';
import { buildStateManager } from '../common/buildState';
import { getButtons } from './buttons';
import {
    findWebviewAssets,
    buildWebviewHtml,
    getWebviewLocalResourceRoots,
} from './webview-utils';

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

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: getWebviewLocalResourceRoots(this._extensionUri),
        };

        const assets = findWebviewAssets(this._extensionUri.fsPath, 'sidebar');
        webviewView.webview.html = buildWebviewHtml({
            webview: webviewView.webview,
            assets,
            title: 'Atopile',
        });

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
            id: btn.id,
            label: btn.label,
            icon: btn.icon,
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
