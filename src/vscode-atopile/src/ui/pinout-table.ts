import * as vscode from 'vscode';
import { backendServer } from '../common/backendServer';
import { getExtension } from '../common/vscodeapi';
import { getSelectionState, onSelectionStateChanged } from '../common/target';
import { BaseWebview } from './webview-base';
import { buildWebviewHtml, findWebviewAssets, getWebviewLocalResourceRoots } from './webview-utils';

class PinoutTableWebview extends BaseWebview {
    private _subscriptions: vscode.Disposable[] = [];

    constructor() {
        super({
            id: 'pinout_table',
            title: 'Pinout Table',
            iconName: 'pcb-icon-transparent.svg',
            column: vscode.ViewColumn.Active,
        });
    }

    protected getHtmlContent(webview: vscode.Webview): string {
        const apiUrl = backendServer.apiUrl;
        const extensionPath = getExtension().extensionPath;
        const assets = findWebviewAssets(extensionPath, 'pinoutTable');

        return buildWebviewHtml({
            webview,
            assets,
            title: 'Pinout Table',
            bootstrapScript: `
                window.__ATOPILE_API_URL__ = ${JSON.stringify(apiUrl)};
            `,
        });
    }

    protected getLocalResourceRoots(): vscode.Uri[] {
        return getWebviewLocalResourceRoots(getExtension().extensionUri);
    }

    protected setupPanel(): void {
        this._subscriptions.push(
            onSelectionStateChanged(() => this._postSelectionState())
        );
        if (this.panel) {
            this._subscriptions.push(
                this.panel.webview.onDidReceiveMessage((message) => {
                    if (message?.type === 'requestSelectionState') {
                        this._postSelectionState();
                    }
                })
            );
        }
    }

    protected onDispose(): void {
        for (const disposable of this._subscriptions) {
            disposable.dispose();
        }
        this._subscriptions = [];
    }

    private _getSelectionState(): { projectRoot: string | null; targetNames: string[] } {
        const selection = getSelectionState();
        return {
            projectRoot: selection.projectRoot ?? null,
            targetNames: selection.targetNames,
        };
    }

    private _postSelectionState(): void {
        if (!this.panel) return;
        void this.panel.webview.postMessage({
            type: 'selectionState',
            ...this._getSelectionState(),
        });
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

export async function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.pinout_table', openPinoutTable)
    );
}

export function deactivate() {
    closePinoutTable();
}
