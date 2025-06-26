import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { onPcbChanged, getCurrentPcb } from '../common/pcb';
import { getResourcesPath } from '../common/resources';

let panel: vscode.WebviewPanel | undefined;

function getKiCanvasScriptUri(webview: vscode.Webview): vscode.Uri {
    const candidate = path.join(getResourcesPath(), 'kicanvas', 'kicanvas.js');
    if (!fs.existsSync(candidate)) {
        throw new Error(`kicanvas.js could not be found in ${candidate}. Make sure it is included.`);
    }
    return webview.asWebviewUri(vscode.Uri.file(candidate));
}

function _getMissingHTML(): string {
    return /* html */ `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>No Layout</title>
            <style>
                html, body {padding: 0; margin: 0; height: 100%; width: 100%; display: flex; align-items: center; justify-content: center; background: var(--vscode-editor-background); color: var(--vscode-descriptionForeground); font-family: var(--vscode-font-family);} 
                .msg {font-size: 0.9rem; opacity: 0.8;}
            </style>
        </head>
        <body><div class="msg">Build target does not have a valid layout.</div></body>
        </html>`;
}

function _getKicanvasHTML(webview: vscode.Webview, pcb_path: string | undefined): string {
    if (!pcb_path) {
        return _getMissingHTML();
    }

    const scriptUri = getKiCanvasScriptUri(webview);
    const cacheBuster = Date.now();
    let pcbWebUri = webview.asWebviewUri(vscode.Uri.file(pcb_path));
    // use cache buster to force reload
    pcbWebUri = vscode.Uri.parse(`${pcbWebUri.toString()}?cb=${cacheBuster}`);

    return /* html */ `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>KiCanvas Preview</title>
            <script type="module" src="${scriptUri}"></script>
            <style>
                html, body {padding: 0; margin: 0; height: 100%; width: 100%; overflow: hidden;}
                                #container {height: 100%; width: 100%;}
                kicanvas-embed {height: 100%; width: 100%; display: block;}
            </style>
        </head>
        <body>
            <div id="container">
                <kicanvas-embed id="kv" src="${pcbWebUri}" controls="full" zoom="objects" controlslist="nodownload"></kicanvas-embed>
            </div>
        </body>
        </html>`;
}

export async function openKiCanvasPreview() {
    const pcb = getCurrentPcb();
    let pcb_path = undefined;
    if (pcb && fs.existsSync(pcb.path)) {
        pcb_path = pcb.path;
    }

    let resourceRoots = [
        vscode.Uri.file(getResourcesPath()),
        ...(vscode.workspace.workspaceFolders?.map((f) => f.uri) ?? []),
    ];
    if (pcb_path) {
        resourceRoots.push(vscode.Uri.file(path.dirname(pcb_path)));
    }

    if (!panel) {
        panel = vscode.window.createWebviewPanel('kicanvas_preview', 'Layout', vscode.ViewColumn.Beside, {
            enableScripts: true,
            localResourceRoots: resourceRoots,
        });

        panel.onDidDispose(() => {
            panel = undefined;
        });

        const icon = vscode.Uri.file(path.join(getResourcesPath(), 'pcb-icon-transparent.svg'));
        panel.iconPath = {
            light: icon,
            dark: icon,
        };
    }

    panel.webview.options = { ...panel.webview.options, localResourceRoots: resourceRoots };
    panel.webview.html = _getKicanvasHTML(panel.webview, pcb_path);

    panel.reveal();
}

export function closeKiCanvasPreview() {
    if (!panel) {
        return;
    }
    panel.dispose();
    panel = undefined;
}

export async function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        onPcbChanged((_) => {
            if (!panel) {
                return;
            }
            openKiCanvasPreview();
        }),
    );
}

export function deactivate() {
    closeKiCanvasPreview();
}
