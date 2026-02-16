/**
 * Pinout webview - Loads the React-based pinout viewer.
 *
 * In production: loads compiled assets from resources/webviews/
 * In development: loads from the Vite dev server.
 * Data is passed via window.__PINOUT_CONFIG__ with a webview URI to the JSON file.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { getCurrentPinout, onPinoutChanged } from '../common/pinout';
import { BaseWebview } from './webview-base';

/**
 * Locate the pinout viewer dist directory.
 */
function getPinoutViewerDistPath(): string | null {
    const extensionPath = vscode.extensions.getExtension('atopile.atopile')?.extensionUri?.fsPath;

    if (extensionPath) {
        // Production: webviews are built into resources/webviews/
        const prodPath = path.join(extensionPath, 'resources', 'webviews');
        if (fs.existsSync(path.join(prodPath, 'pinout.html'))) {
            return prodPath;
        }
    }

    // Development: use ui-server dist directly
    for (const folder of vscode.workspace.workspaceFolders ?? []) {
        const devPath = path.join(folder.uri.fsPath, 'src', 'ui-server', 'dist');
        if (fs.existsSync(path.join(devPath, 'pinout.html'))) {
            return devPath;
        }
    }

    return null;
}

class PinoutWebview extends BaseWebview {
    constructor() {
        super({
            id: 'pinout_explorer',
            title: 'Pinout',
        });
    }

    protected getHtmlContent(webview: vscode.Webview): string {
        const resource = getCurrentPinout();

        if (!resource || !resource.exists) {
            return this.getMissingResourceHtml('Pinout');
        }

        // Verify JSON has content
        try {
            const raw = fs.readFileSync(resource.path, 'utf-8');
            const parsed = JSON.parse(raw);
            if (!parsed.components || parsed.components.length === 0) {
                return this.getMissingResourceHtml('Pinout (no ICs found — need components with 5+ pins)');
            }
        } catch {
            return this.getMissingResourceHtml('Pinout (invalid JSON)');
        }

        const distPath = getPinoutViewerDistPath();
        if (distPath) {
            return this.getProductionHtml(webview, distPath, resource.path);
        }

        // Fallback: inline minimal loader that fetches the JSON
        return this.getInlineHtml(webview, resource.path);
    }

    protected getLocalResourceRoots(): vscode.Uri[] {
        const roots = super.getLocalResourceRoots();
        const distPath = getPinoutViewerDistPath();
        if (distPath) {
            roots.push(vscode.Uri.file(distPath));
        }
        const resource = getCurrentPinout();
        if (resource && fs.existsSync(resource.path)) {
            roots.push(vscode.Uri.file(path.dirname(resource.path)));
        }
        return roots;
    }

    /**
     * Load the compiled React app from dist, injecting the data URL.
     */
    private getProductionHtml(webview: vscode.Webview, distPath: string, dataPath: string): string {
        const indexHtmlPath = path.join(distPath, 'pinout.html');
        let html = fs.readFileSync(indexHtmlPath, 'utf-8');

        const distUri = webview.asWebviewUri(vscode.Uri.file(distPath));
        const dataUri = this.getWebviewUri(webview, dataPath);

        // Rewrite asset paths
        html = html.replace(/(href|src)="\.\/assets\//g, `$1="${distUri}/assets/`);
        html = html.replace(/(href|src)="\/assets\//g, `$1="${distUri}/assets/`);
        html = html.replace(/(href|src)="\.\/pinout\./g, `$1="${distUri}/pinout.`);
        html = html.replace(/(href|src)="\/pinout\./g, `$1="${distUri}/pinout.`);

        // Also handle the entry JS
        html = html.replace(/src="\.\/src\/pinout\.tsx"/g, `src="${distUri}/pinout.js"`);

        // Inject config
        const configScript = `
            <script>
                window.__PINOUT_CONFIG__ = {
                    dataUrl: "${dataUri.toString()}"
                };
            </script>
        `;
        html = html.replace('</head>', `${configScript}</head>`);

        return html;
    }

    /**
     * Fallback: embed the JSON data directly and render with minimal inline React-like code.
     * Used when the React app hasn't been built yet.
     */
    private getInlineHtml(webview: vscode.Webview, dataPath: string): string {
        const dataUri = this.getWebviewUri(webview, dataPath);
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pinout</title>
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
        <p>Pinout viewer not built.</p>
        <p>Run <code>npm run build:webviews</code> in <code>src/vscode-atopile</code>.</p>
    </div>
</body>
</html>`;
    }
}

let pinoutViewer: PinoutWebview | undefined;

export async function openPinoutExplorer() {
    if (!pinoutViewer) {
        pinoutViewer = new PinoutWebview();
    }
    await pinoutViewer.open();
}

export function closePinoutExplorer() {
    pinoutViewer?.dispose();
    pinoutViewer = undefined;
}

export async function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        onPinoutChanged((_) => {
            if (pinoutViewer?.isOpen()) {
                openPinoutExplorer();
            }
        }),
    );
}

export function deactivate() {
    closePinoutExplorer();
}
