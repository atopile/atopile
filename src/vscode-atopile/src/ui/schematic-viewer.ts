/**
 * Schematic viewer webview.
 *
 * Loads the React-based schematic viewer from the ui-server build output.
 * Data is passed via window.__SCHEMATIC_VIEWER_CONFIG__ with a webview URI to the JSON file.
 *
 * Production: loads from resources/webviews/schematic.html
 * Development: loads from ui-server/dist/schematic.html
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import axios from 'axios';
import { getCurrentSchematic, onSchematicChanged } from '../common/schematic';
import { BaseWebview } from './webview-base';
import { backendServer } from '../common/backendServer';
import { getProjectRoot } from '../common/target';

/**
 * Locate the schematic viewer dist directory.
 */
function getSchematicViewerDistPath(): string | null {
    const extensionPath = vscode.extensions.getExtension('atopile.atopile')?.extensionUri?.fsPath;

    if (extensionPath) {
        // Production: webviews are built into resources/webviews/
        const prodPath = path.join(extensionPath, 'resources', 'webviews');
        if (fs.existsSync(path.join(prodPath, 'schematic.html'))) {
            return prodPath;
        }
    }

    // Development: use ui-server dist directly
    for (const folder of vscode.workspace.workspaceFolders ?? []) {
        const devPath = path.join(folder.uri.fsPath, 'src', 'ui-server', 'dist');
        if (fs.existsSync(path.join(devPath, 'schematic.html'))) {
            return devPath;
        }
    }

    return null;
}

class SchematicWebview extends BaseWebview {
    /**
     * Timestamp of the last position save initiated by the webview.
     * Used to suppress file-watcher reloads triggered by our own writes.
     */
    private _lastSaveTime = 0;
    private static readonly SAVE_SUPPRESS_MS = 2000;

    /** Check if a recent self-save should suppress a file-watcher event. */
    public shouldSuppressReload(): boolean {
        return Date.now() - this._lastSaveTime < SchematicWebview.SAVE_SUPPRESS_MS;
    }

    /** Mark that we just saved positions (so we can suppress the echo). */
    public markSave(): void {
        this._lastSaveTime = Date.now();
    }

    constructor() {
        super({
            id: 'schematic_preview',
            title: 'Schematic',
        });
    }

    protected getHtmlContent(webview: vscode.Webview): string {
        const resource = getCurrentSchematic();

        if (!resource || !resource.exists) {
            return this.getMissingResourceHtml('Schematic');
        }

        const distPath = getSchematicViewerDistPath();
        if (distPath) {
            return this.getProductionHtml(webview, distPath, resource.path);
        }

        // Fallback: inline minimal message
        return this.getInlineHtml();
    }

    protected getLocalResourceRoots(): vscode.Uri[] {
        const roots = super.getLocalResourceRoots();
        const distPath = getSchematicViewerDistPath();
        if (distPath) {
            roots.push(vscode.Uri.file(distPath));
        }
        const resource = getCurrentSchematic();
        if (resource && fs.existsSync(resource.path)) {
            roots.push(vscode.Uri.file(path.dirname(resource.path)));
        }
        return roots;
    }

    /**
     * Load the compiled React app from dist, injecting the data URL.
     */
    private getProductionHtml(webview: vscode.Webview, distPath: string, dataPath: string): string {
        const indexHtmlPath = path.join(distPath, 'schematic.html');
        let html = fs.readFileSync(indexHtmlPath, 'utf-8');

        const distUri = webview.asWebviewUri(vscode.Uri.file(distPath));
        const dataUri = this.getWebviewUri(webview, dataPath);

        // Rewrite asset paths
        html = html.replace(/(href|src)="\.\/assets\//g, `$1="${distUri}/assets/`);
        html = html.replace(/(href|src)="\/assets\//g, `$1="${distUri}/assets/`);
        html = html.replace(/(href|src)="\.\/schematic\./g, `$1="${distUri}/schematic.`);
        html = html.replace(/(href|src)="\/schematic\./g, `$1="${distUri}/schematic.`);

        // Also handle the entry JS in dev mode
        html = html.replace(/src="\.\/src\/schematic\.tsx"/g, `src="${distUri}/schematic.js"`);

        // Inject config — .ato_sch contains both schematic data and positions
        const configScript = `
            <script>
                window.__SCHEMATIC_VIEWER_CONFIG__ = {
                    dataUrl: "${dataUri.toString()}",
                    atoSchPath: "${dataPath.replace(/\\/g, '\\\\')}"
                };
            </script>
        `;
        html = html.replace('</head>', `${configScript}</head>`);

        return html;
    }

    /**
     * Fallback when the React app hasn't been built yet.
     */
    private getInlineHtml(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Schematic</title>
    <style>
        body {
            display: flex; align-items: center; justify-content: center;
            height: 100vh; margin: 0;
            background: var(--vscode-editor-background, #1e1e1e);
            color: var(--vscode-descriptionForeground, #888);
            font-family: var(--vscode-font-family, system-ui);
            font-size: 13px; text-align: center; padding: 24px;
        }
        code { background: var(--vscode-textCodeBlock-background, #2d2d30); padding: 2px 6px; border-radius: 3px; font-size: 12px; }
    </style>
</head>
<body>
    <div>
        <p>Schematic viewer not built.</p>
        <p>Run <code>cd src/ui-server && npm run build</code> then rebuild the extension.</p>
    </div>
</body>
</html>`;
    }

    /**
     * Set up the panel to receive messages from the webview.
     */
    protected setupPanel(): void {
        if (!this.panel) return;

        this.panel.webview.onDidReceiveMessage(async (message) => {
            switch (message.type) {
                case 'openSource': {
                    // Bidirectional: webview sends an atopile address to open in source
                    const address = message.address as string | undefined;
                    const filePath = message.filePath as string | undefined;

                    if (filePath) {
                        // Direct file path (if provided)
                        this.openSourceFile(filePath, message.line as number, message.column as number);
                    } else if (address && backendServer.isConnected) {
                        // Resolve atopile address via the backend API
                        try {
                            const root = getProjectRoot();
                            const url = `${backendServer.apiUrl}/api/resolve-location?address=${encodeURIComponent(address)}${root ? `&project_root=${encodeURIComponent(root)}` : ''}`;
                            const resp = await axios.get(url);
                            if (resp.data?.file_path) {
                                this.openSourceFile(resp.data.file_path, resp.data.line, resp.data.column);
                            }
                        } catch {
                            // Silently fail — resolve-location may not find all addresses
                        }
                    }
                    break;
                }
                case 'save-layout': {
                    // Merge positions back into the .ato_sch file
                    const atoSchPath = message.atoSchPath as string | undefined;
                    const positions = message.positions;
                    const portSignalOrders = message.portSignalOrders;
                    if (atoSchPath && positions) {
                        try {
                            let data: Record<string, unknown> = {};
                            if (fs.existsSync(atoSchPath)) {
                                data = JSON.parse(fs.readFileSync(atoSchPath, 'utf-8'));
                            }
                            data.positions = positions;
                            if (portSignalOrders && typeof portSignalOrders === 'object') {
                                data.portSignalOrders = portSignalOrders;
                            }
                            const dir = path.dirname(atoSchPath);
                            if (!fs.existsSync(dir)) {
                                fs.mkdirSync(dir, { recursive: true });
                            }
                            // Mark self-save so the file watcher doesn't trigger a reload
                            this.markSave();
                            fs.writeFileSync(atoSchPath, JSON.stringify(data, null, 2), 'utf-8');
                        } catch (e) {
                            console.error('Failed to save positions to .ato_sch:', e);
                        }
                    }
                    break;
                }
            }
        });
    }

    private openSourceFile(filePath: string, line?: number, column?: number): void {
        const uri = vscode.Uri.file(filePath);
        vscode.workspace.openTextDocument(uri).then((doc) => {
            const options: vscode.TextDocumentShowOptions = {
                viewColumn: vscode.ViewColumn.One,
            };
            if (line != null) {
                const position = new vscode.Position(
                    Math.max(0, line - 1),
                    column ?? 0,
                );
                options.selection = new vscode.Range(position, position);
            }
            vscode.window.showTextDocument(doc, options);
        });
    }

    /**
     * Send a message to the webview (for active file tracking etc).
     */
    public postMessage(message: unknown): void {
        this.panel?.webview.postMessage(message);
    }
}

let schematicViewer: SchematicWebview | undefined;

export async function openSchematicPreview() {
    if (!schematicViewer) {
        schematicViewer = new SchematicWebview();
    }
    await schematicViewer.open();
}

/**
 * Send updated schematic data to an already-open webview without
 * replacing the HTML (preserves navigation state, selection, etc.).
 */
function sendSchematicUpdate() {
    if (!schematicViewer?.isOpen()) return;
    const resource = getCurrentSchematic();
    if (!resource?.exists) return;
    try {
        const raw = fs.readFileSync(resource.path, 'utf-8');
        const data = JSON.parse(raw);
        schematicViewer.postMessage({ type: 'update-schematic', data });
    } catch {
        // File may be mid-write or corrupt — silently skip
    }
}

export function closeSchematicPreview() {
    schematicViewer?.dispose();
    schematicViewer = undefined;
}

/**
 * Notify the schematic viewer of the currently active editor file.
 * Used for bidirectional source highlighting.
 */
export function notifyActiveFile(filePath: string | null) {
    schematicViewer?.postMessage({ type: 'activeFile', filePath });
}

export async function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        onSchematicChanged((_) => {
            if (schematicViewer?.isOpen()) {
                // Skip reload when the change was triggered by our own position save
                if (schematicViewer.shouldSuppressReload()) {
                    return;
                }
                // For external changes (rebuild), send data via message
                // to preserve navigation state instead of replacing HTML
                sendSchematicUpdate();
            }
        }),
        // Track active editor for bidirectional navigation
        vscode.window.onDidChangeActiveTextEditor((editor) => {
            if (schematicViewer?.isOpen()) {
                const filePath = editor?.document?.uri?.fsPath ?? null;
                notifyActiveFile(filePath);
            }
        }),
    );
}

export function deactivate() {
    closeSchematicPreview();
}
