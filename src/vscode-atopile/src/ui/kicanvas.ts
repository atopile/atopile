import * as vscode from 'vscode';
import { glob } from 'glob';
import * as fs from 'fs';
import * as path from 'path';
import * as fs from 'fs';
import { traceError, traceInfo } from '../common/log/logging';
import { getCurrentBuild } from './buttons';


let panel: vscode.WebviewPanel | undefined;
let fileWatcher: vscode.FileSystemWatcher | undefined;

/**
 * Attempt to find a PCB file to preview. Strategy:
 *  1. If the currently active editor is a .kicad_pcb file, use it.
 *  2. Otherwise, search for **.kicad_pcb inside the workspace. If multiple
 *     results are found, ask the user to choose.
 */
async function findPcbPath(): Promise<string | undefined> {
    const active = vscode.window.activeTextEditor?.document.uri.fsPath;
    if (active && active.endsWith('.kicad_pcb')) {
        return active;
    }

    const results = await glob('**/*.kicad_pcb', {
        cwd: vscode.workspace.workspaceFolders?.[0].uri.fsPath ?? '.',
        absolute: true,
    });

    if (results.length === 0) {
        vscode.window.showErrorMessage('No .kicad_pcb files found in workspace. Build the project first.');
        return undefined;
    }

    if (results.length === 1) {
        return results[0];
    }

    const picked = await vscode.window.showQuickPick(results, {
        placeHolder: 'Select PCB to preview with KiCanvas',
    });
    return picked;
}

function getWebviewContent(webview: vscode.Webview, pcbUri?: vscode.Uri): string {
    if (!pcbUri) {
        // Error view
        return `<!DOCTYPE html><html><body style="font-family: sans-serif; padding:1rem; color:var(--vscode-foreground);">
            <h3>Selected build does not have a valid PCB file.</h3>
        </body></html>`;
    }
    const scriptUri = webview.asWebviewUri(
        vscode.Uri.parse('https://kicanvas.org/kicanvas/kicanvas.js'),
    );

    const pcbWebUri = webview.asWebviewUri(pcbUri);

    return /* html */ `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8" />
            <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src vscode-resource: https: data:; script-src https: vscode-resource: 'self'; style-src 'unsafe-inline' ${webview.cspSource}; connect-src vscode-resource: https: 'self';" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>KiCanvas Preview</title>
            <script type="module" src="${scriptUri}"></script>
            <style>
                html, body {
                    padding: 0;
                    margin: 0;
                    height: 100%;
                    width: 100%;
                    overflow: hidden;
                }
                #container {
                    height: 100%;
                    width: 100%;
                }
                kicanvas-embed {
                    height: 100%;
                    width: 100%;
                    display: block;
                }
            </style>
        </head>
        <body>
            <div id="container">
                <kicanvas-embed id="kv" src="${pcbWebUri}" controls="basic" zoom="objects" controlslist="nodownload"></kicanvas-embed>
            </div>
            <script type="module">
                const kv = document.getElementById('kv');
                console.log('KiCanvas embed element loaded', kv);
                kv.addEventListener('load', () => {
                    console.log('KiCanvas loaded PCB');

                });
                window.addEventListener('message', ev => {
                    if (ev.data?.type === 'updateSrc') {
                        console.log('Updating src to', ev.data.src);
                        kv.src = ev.data.src;
                    }
                });
            </script>
        </body>
        </html>`;
}

function getMissingLayoutContent(): string {
    return /* html */ `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>No Layout</title>
            <style>
                html, body {
                    padding: 0;
                    margin: 0;
                    height: 100%;
                    width: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: var(--vscode-editor-background);
                    color: var(--vscode-descriptionForeground);
                    font-family: var(--vscode-font-family);
                }
                .msg {
                    font-size: 0.9rem;
                    opacity: 0.8;
                }
            </style>
        </head>
        <body>
            <div class="msg">Build target does not have a valid layout.</div>
        </body>
        </html>`;
}

function watchFile(pcbPath: string) {
    disposeWatcher();

    // Watch any .kicad_pcb inside the layout directory so edits or regenerations trigger reload
    fileWatcher = vscode.workspace.createFileSystemWatcher(
        new vscode.RelativePattern(path.dirname(pcbPath), '*.kicad_pcb'),
    );

    const reload = () => {
        const build = getCurrentBuild();
        if (!build) {
            traceError('No build when file watcher triggered');
            return;
        }
        const newUri = vscode.Uri.file(build.entry);
        traceInfo(`Watcher triggered – rebuilding preview for ${build.entry}`);
        // Update resource roots
        if (panel) {
            panel.webview.options = {
                ...panel.webview.options,
                localResourceRoots: [vscode.Uri.file(path.dirname(build.entry))],
            };
            let uriForView: vscode.Uri | undefined = undefined;
            if (fs.existsSync(build.entry)) {
                uriForView = newUri;
            }
            // Append timestamp if valid
            if (uriForView) {
                const busted = uriForView.with({ query: `t=${Date.now()}` });
                panel.webview.html = getWebviewContent(panel.webview, busted);
            } else {
                panel.webview.html = getWebviewContent(panel.webview);
            }
            // watcher already set for directory, no change needed
        }
    };

    fileWatcher.onDidChange(reload);
    fileWatcher.onDidCreate(reload);
    fileWatcher.onDidDelete(reload);
}

function disposeWatcher() {
    if (fileWatcher) {
        fileWatcher.dispose();
        fileWatcher = undefined;
    }
}

async function openKiCanvasPreview() {
    try {
        traceInfo('Opening KiCanvas preview');

        const build = getCurrentBuild();
        if (!build) {
            traceError('No current build found.');
            vscode.window.showErrorMessage('No current build found.');
            return;
        }

        traceInfo(`Previewing PCB from build entry: ${build.entry}`);
        

        const pcbPath = build.entry;
        let pcbUri: vscode.Uri | undefined = undefined;
        if (pcbPath && fs.existsSync(pcbPath)) {
            pcbUri = vscode.Uri.file(pcbPath);
        }

        // Determine if a valid PCB file is available
        const hasPcb = !!pcbUri;

    if (!panel) {
        panel = vscode.window.createWebviewPanel(
            'kicanvasPreview',
            'Layout',
            vscode.ViewColumn.Beside,
            {
                enableScripts: true,
                localResourceRoots: [vscode.Uri.file(path.dirname(pcbPath))],
            },
        );

        panel.onDidDispose(() => {
            panel = undefined;
            disposeWatcher();
        });
    } else {
        panel.reveal();
    }

    traceInfo('Setting webview HTML');
    if (hasPcb) {
        panel.webview.html = getWebviewContent(panel.webview, pcbUri);
    } else {
        panel.webview.html = getMissingLayoutContent();
    }
    if (hasPcb) {
        traceInfo('Webview HTML set, starting file watcher');
        watchFile(pcbPath);
    } else {
        traceInfo('No valid PCB found; showing placeholder message instead.');
    }
    traceInfo('KiCanvas preview should now be visible');
    } catch (err) {
        traceError(`Error opening KiCanvas preview: ${err}`);
        vscode.window.showErrorMessage(`Failed to open KiCanvas preview: ${err}`);
    }
}

function refreshKiCanvasPreview() {
    if (!panel) {
        // No existing panel; nothing to refresh
        traceInfo('KiCanvas refresh requested but no panel open; ignoring.');
        return;
    }

    const build = getCurrentBuild();
    if (!build) {
        traceError('No current build found when refreshing KiCanvas');
        return;
    }

    let pcbUri: vscode.Uri | undefined = undefined;
    if (fs.existsSync(build.entry)) {
        pcbUri = vscode.Uri.file(build.entry);
    }
    const pcbDir = path.dirname(build.entry);
    traceInfo(`Rebuilding KiCanvas preview for ${build.entry}`);
    panel.webview.options = {
        ...panel.webview.options,
        localResourceRoots: [vscode.Uri.file(pcbDir)],
    };

    if (fs.existsSync(build.entry)) {
        panel.webview.html = getWebviewContent(panel.webview, pcbUri);
        // Update file watcher to new PCB path
        watchFile(build.entry);
    } else {
        panel.webview.html = getMissingLayoutContent();
        traceInfo('No valid PCB found on refresh; showing placeholder message.');
        disposeWatcher();
    }
    
}

export async function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.kicanvasPreview', () => {
            openKiCanvasPreview();
        }),
        vscode.commands.registerCommand('atopile.kicanvasPreviewRefresh', () => {
            refreshKiCanvasPreview();
        }),
    );
}

export function deactivate() {
    if (panel) {
        panel.dispose();
        panel = undefined;
    }
    disposeWatcher();
}
