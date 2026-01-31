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
                :root {
                    --ato-orange: #f95015;
                    --ato-orange-light: #ff6b35;
                    /* Board canvas colors - read by patched kicanvas.js */
                    --kicanvas-board-bg: var(--vscode-editor-background);
                    --kicanvas-board-grid: var(--vscode-editor-background);
                }
                #container {height: 100%; width: 100%;}
                kicanvas-embed {
                    height: 100%; width: 100%; display: block;
                    /* UI chrome - remove gradients, use VS Code theme */
                    --bg: var(--vscode-editor-background);
                    --fg: var(--vscode-foreground);
                    --gradient-purple-green-light: var(--vscode-sideBarSectionHeader-background);
                    --gradient-purple-blue-medium: var(--vscode-input-background);
                    --gradient-purple-blue-dark: var(--vscode-editor-background);
                    --gradient-purple-green-highlight: var(--vscode-list-hoverBackground);
                    --gradient-cyan-blue-light: var(--ato-orange);
                    --gradient-purple-red: var(--ato-orange);
                    --gradient-purple-red-highlight: var(--ato-orange-light);
                    --activity-bar-bg: var(--vscode-sideBar-background);
                    --activity-bar-fg: var(--vscode-foreground);
                    --activity-bar-active-bg: var(--vscode-editor-background);
                    --panel-bg: var(--vscode-editor-background);
                    --panel-fg: var(--vscode-foreground);
                    --panel-title-bg: var(--vscode-sideBarSectionHeader-background);
                    --panel-title-fg: var(--vscode-foreground);
                    --panel-subtitle-bg: var(--vscode-input-background);
                    --resizer-bg: var(--vscode-panel-border);
                    --resizer-active-bg: var(--ato-orange);
                    --scrollbar-bg: var(--vscode-editor-background);
                    --scrollbar-fg: var(--vscode-scrollbarSlider-background);
                    --scrollbar-hover-fg: var(--ato-orange);
                    --button-bg: var(--ato-orange);
                    --button-fg: white;
                    --button-hover-bg: var(--ato-orange-light);
                    --button-toolbar-bg: var(--vscode-sideBar-background);
                    --button-toolbar-fg: var(--vscode-foreground);
                    --button-toolbar-hover-bg: var(--vscode-list-hoverBackground);
                    --dropdown-bg: var(--vscode-sideBar-background);
                    --dropdown-fg: var(--vscode-foreground);
                    --dropdown-hover-bg: var(--vscode-list-hoverBackground);
                    --input-bg: var(--vscode-input-background);
                    --input-fg: var(--vscode-input-foreground);
                    --input-accent: var(--ato-orange);
                    --list-item-hover-bg: var(--vscode-list-hoverBackground);
                    --list-item-active-bg: var(--vscode-list-activeSelectionBackground);
                    --tooltip-bg: var(--vscode-editorWidget-background);
                    --tooltip-fg: var(--vscode-foreground);
                }
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
