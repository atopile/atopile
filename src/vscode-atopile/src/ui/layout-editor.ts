import * as vscode from 'vscode';
import { getAndCheckResource } from '../common/resources';
import { backendServer } from '../common/backendServer';
import { getWsOrigin, getNonce } from '../common/webview';
import { BaseWebview } from './webview-base';
// @ts-ignore
import * as _templateText from '../../../atopile/layout_server/static/layout-editor.hbs';
const templateText: string = (_templateText as any).default || _templateText;

function renderTemplate(template: string, values: Record<string, string>): string {
    return template.replace(/\{\{([a-zA-Z0-9_]+)\}\}/g, (_match, key) => values[key] ?? '');
}

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
        const csp = [
            "default-src 'none'",
            "style-src 'unsafe-inline'",
            `script-src 'nonce-${nonce}' ${webview.cspSource}`,
            `connect-src ${apiUrl} ${wsOrigin}`,
        ].join('; ');

        const editorUri = webview.asWebviewUri(
            vscode.Uri.file(getAndCheckResource('layout-editor/editor.js'))
        ).toString();

        return renderTemplate(templateText, {
            csp,
            apiUrl,
            apiPrefix: '/api/layout',
            wsPath: '/ws/layout',
            wsOrigin,
            nonce,
            editorUri,
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
