import * as vscode from 'vscode';
import { getAndCheckResource } from '../common/resources';
import { backendServer } from '../common/backendServer';
import { getWsOrigin, getNonce } from '../common/webview';
import { BaseWebview } from './webview-base';
import { WebviewProxyBridge } from '../common/webview-bridge';
import { generateBridgeRuntime } from '../common/webview-bridge-runtime';
// @ts-ignore
import * as _templateText from '../../../atopile/layout_server/static/layout-editor.hbs';
const templateText: string = (_templateText as any).default || _templateText;

function renderTemplate(template: string, values: Record<string, string>): string {
    return template.replace(/\{\{([a-zA-Z0-9_]+)\}\}/g, (_match, key) => values[key] ?? '');
}

class LayoutEditorWebview extends BaseWebview {
    private messageDisposable?: vscode.Disposable;
    private _bridge!: WebviewProxyBridge;

    constructor() {
        super({
            id: 'layout_editor',
            title: 'Layout',
            iconName: 'pcb-icon-transparent.svg',
        });
    }

    protected setupPanel(): void {
        if (!this.panel) {
            return;
        }
        this._bridge = new WebviewProxyBridge({
            postToWebview: (msg) => this.panel?.webview.postMessage(msg),
            logTag: 'LayoutEditor',
        });
        this.messageDisposable = this.panel.webview.onDidReceiveMessage((message: unknown) => {
            if (!message || typeof message !== 'object' || !('type' in message)) {
                return;
            }
            this._bridge.handleMessage(message as { type?: string });
        });
    }

    protected onDispose(): void {
        this.messageDisposable?.dispose();
        this.messageDisposable = undefined;
        this._bridge?.dispose();
    }

    protected getHtmlContent(webview: vscode.Webview): string {
        const apiUrl = backendServer.apiUrl;
        const wsOrigin = getWsOrigin(backendServer.wsUrl);
        const nonce = getNonce();
        const csp = [
            "default-src 'none'",
            "style-src 'unsafe-inline'",
            `script-src 'nonce-${nonce}' ${webview.cspSource}`,
            `connect-src ${webview.cspSource} ${apiUrl} ${wsOrigin} ws: wss:`,
        ].join('; ');

        const editorUri = this.getWebviewUri(
            webview,
            getAndCheckResource('layout-editor/editor.js'),
            true,
        ).toString();

        return renderTemplate(templateText, {
            csp,
            apiUrl,
            apiPrefix: '/api/layout',
            wsPath: '/ws/layout',
            wsOrigin,
            nonce,
            editorUri,
            bridgeRuntime: generateBridgeRuntime({ apiUrl, fetchMode: 'override' }),
        });
    }
}

let layoutEditor: LayoutEditorWebview | undefined;

export async function openLayoutEditor() {
    if (!layoutEditor) {
        layoutEditor = new LayoutEditorWebview();
    }
    await layoutEditor.open();
}

export function isLayoutEditorOpen(): boolean {
    return layoutEditor?.isOpen() ?? false;
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
