import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { traceError, traceInfo } from '../common/log/logging';
import { getBuildTarget } from './buttons';
import { pcbManager } from './pcb';

let panel: vscode.WebviewPanel | undefined;
let extensionPath: string; // set during activate

function getKiCanvasScriptUri(webview: vscode.Webview): vscode.Uri {
    const candidate = path.join(extensionPath ?? path.join(__dirname, '..'), 'resources', 'kicanvas', 'kicanvas.js');
    if (fs.existsSync(candidate)) {
        return webview.asWebviewUri(vscode.Uri.file(candidate));
    }

    const dev = path.join(__dirname, '..', 'src', 'resources', 'kicanvas', 'kicanvas.js');
    if (fs.existsSync(dev)) {
        return webview.asWebviewUri(vscode.Uri.file(dev));
    }

    throw new Error('kicanvas.js could not be found in resources/kicanvas. Make sure it is included.');
}

function buildWebviewHtml(webview: vscode.Webview, pcbUri?: vscode.Uri): string {
    if (!pcbUri) {
        return missingLayoutHtml();
    }

    const scriptUri = getKiCanvasScriptUri(webview);
    const pcbWebUri = webview.asWebviewUri(pcbUri);

    return /* html */ `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8" />
            <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src vscode-resource: https: data: blob: vscode-webview:; font-src vscode-resource: https: data:; script-src https: vscode-resource: 'self' 'unsafe-inline'; style-src 'unsafe-inline' ${webview.cspSource} https:; connect-src vscode-resource: https: 'self';" />
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
                <kicanvas-embed id="kv" src="${pcbWebUri}" controls="basic" zoom="objects" controlslist="nodownload"></kicanvas-embed>
            </div>
            <script type="module">
                const kv = document.getElementById('kv');
                console.log('KiCanvas webview loaded, setting up message listener');
                window.addEventListener('message', ev => {
                    console.log('Received message:', ev.data);
                    if (ev.data?.type === 'updateSrc') {
                        console.log('Updating PCB source to:', ev.data.src);
                        const oldSrc = kv.src;
                        kv.src = ev.data.src;
                        console.log('PCB source updated from', oldSrc, 'to', kv.src);
                    }
                });
            </script>
        </body>
        </html>`;
}

function missingLayoutHtml(): string {
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

export async function openKiCanvasPreview() {
    const build = getBuildTarget();
    if (!build) {
        throw new Error('No current build found.');
    }

    const pcbUri = pcbManager.getPcbForBuild(build);
    const pcbDir = path.dirname(build.entry);
    const resourceRoots = [
        vscode.Uri.file(pcbDir),
        vscode.Uri.file(path.join(extensionPath || path.join(__dirname, '..'), 'resources')),
        vscode.Uri.file(path.join(__dirname, '..', 'src', 'resources', 'kicanvas')),
        ...(vscode.workspace.workspaceFolders?.map((f) => f.uri) ?? []),
    ];

    if (!panel) {
        panel = vscode.window.createWebviewPanel('kicanvas_preview', 'Layout', vscode.ViewColumn.Beside, {
            enableScripts: true,
            localResourceRoots: resourceRoots,
        });

        // custom icon disabled
        const iconSvg = path.join(extensionPath || path.join(__dirname, '..'), 'resources', 'icon.svg');
        const iconPng = path.join(extensionPath || path.join(__dirname, '..'), 'resources', 'ato_logo_256x256.png');
        const iconDevSvg = path.join(__dirname, '..', 'src', 'resources', 'icon.svg');
        const iconDevPng = path.join(__dirname, '..', 'src', 'ato_logo_256x256.png');
        let iconFile = iconSvg;
        panel.onDidDispose(() => {
            panel = undefined;
            pcbManager.disposeWatcher();
        });

        pcbManager.onPcbChanged((uri) => {
            if (panel && build) {
                panel.webview.options = {
                    ...panel.webview.options,
                    localResourceRoots: resourceRoots,
                };
                const webviewUri = panel.webview.asWebviewUri(uri);

                panel.webview.postMessage({
                    type: 'updateSrc',
                    src: webviewUri.toString(),
                });
            }
        });
    } else {
        panel.reveal();
        // Ensure resource roots are current when reusing existing panel
        panel.webview.options = { ...panel.webview.options, localResourceRoots: resourceRoots };
    }

    panel.webview.html = buildWebviewHtml(panel.webview, pcbUri);

    if (pcbUri) {
        pcbManager.setPcbPath(pcbUri.fsPath);
    }
}

export async function activate(context: vscode.ExtensionContext) {
    extensionPath = context.extensionPath;
    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.kicanvas_preview', async () => {
            try {
                await openKiCanvasPreview();
            } catch (err) {
                traceError(`Error opening KiCanvas preview: ${err}`);
                vscode.window.showErrorMessage(`Failed to open KiCanvas preview: ${err}`);
            }
        }),
        vscode.commands.registerCommand('atopile.kicanvas_preview_refresh', async () => {
            // For backward compatibility, just delegate to the main preview command.
            await openKiCanvasPreview();
        }),
    );
}

export function deactivate() {
    if (panel) {
        panel.dispose();
        panel = undefined;
    }
    pcbManager.dispose();
}
