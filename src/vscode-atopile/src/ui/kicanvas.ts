import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { onPcbChanged, getCurrentPcb } from '../common/pcb';
import { getAndCheckResource, getResourcesPath } from '../common/resources';
import { BaseWebview } from './webview-base';
import { buildHtml } from './html-builder';

class KiCanvasWebview extends BaseWebview {
    constructor() {
        super({
            id: 'kicanvas_preview',
            title: 'Layout',
            iconName: 'pcb-icon-transparent.svg',
        });
    }

    protected getHtmlContent(webview: vscode.Webview): string {
        const pcb = getCurrentPcb();
        if (!pcb || !fs.existsSync(pcb.path)) {
            return this.getMissingResourceHtml('Layout');
        }

        const scriptUri = this.getKiCanvasScriptUri(webview);
        const pcbWebUri = this.getWebviewUri(webview, pcb.path);

        return buildHtml({
            title: 'KiCanvas Preview',
            scripts: [{ type: 'module', src: scriptUri.toString() }],
            styles: `
                #container {height: 100%; width: 100%;}
                kicanvas-embed {height: 100%; width: 100%; display: block;}
            `,
            body: `
                <div id="container">
                    <kicanvas-embed id="kv" src="${pcbWebUri}" controls="full" zoom="objects" controlslist="nodownload"></kicanvas-embed>
                </div>
            `,
        });
    }

    protected getLocalResourceRoots(): vscode.Uri[] {
        const roots = super.getLocalResourceRoots();
        const pcb = getCurrentPcb();
        if (pcb && fs.existsSync(pcb.path)) {
            roots.push(vscode.Uri.file(path.dirname(pcb.path)));
        }
        return roots;
    }

    private getKiCanvasScriptUri(webview: vscode.Webview): vscode.Uri {
        return webview.asWebviewUri(vscode.Uri.file(getAndCheckResource('kicanvas/kicanvas.js')));
    }
}

let kiCanvas: KiCanvasWebview | undefined;

export async function openKiCanvasPreview() {
    if (!kiCanvas) {
        kiCanvas = new KiCanvasWebview();
    }
    await kiCanvas.open();
}

export function closeKiCanvasPreview() {
    kiCanvas?.dispose();
    kiCanvas = undefined;
}

export async function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        onPcbChanged((_) => {
            if (kiCanvas?.isOpen()) {
                openKiCanvasPreview();
            }
        }),
    );
}

export function deactivate() {
    closeKiCanvasPreview();
}
