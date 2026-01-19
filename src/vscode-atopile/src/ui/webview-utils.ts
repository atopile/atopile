/**
 * Shared utilities for React webview panels.
 *
 * This module consolidates common functionality used by both the
 * sidebar panel and log viewer panel, including:
 * - Nonce generation for CSP
 * - Asset resolution (JS/CSS files)
 * - HTML template generation
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

/**
 * Generate a random nonce for Content Security Policy.
 */
export function getNonce(): string {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}

/**
 * Resolved webview assets.
 */
export interface WebviewAssets {
    js: string | null;
    css: string | null;
    baseCss: string | null;
}

/**
 * Find webview assets for a given webview name.
 *
 * Looks in two locations:
 * 1. resources/webviews/ - production (packaged extension)
 * 2. webviews/dist/ - development
 */
export function findWebviewAssets(extensionPath: string, webviewName: string): WebviewAssets {
    const webviewsDir = path.join(extensionPath, 'resources', 'webviews');

    if (!fs.existsSync(webviewsDir)) {
        // Development mode: check webviews/dist
        const devDir = path.join(extensionPath, 'webviews', 'dist');
        if (!fs.existsSync(devDir)) {
            return { js: null, css: null, baseCss: null };
        }

        const jsFile = path.join(devDir, `${webviewName}.js`);
        const cssFile = path.join(devDir, `${webviewName}.css`);
        const baseCssFile = path.join(devDir, 'index.css');

        return {
            js: fs.existsSync(jsFile) ? jsFile : null,
            css: fs.existsSync(cssFile) ? cssFile : null,
            baseCss: fs.existsSync(baseCssFile) ? baseCssFile : null,
        };
    }

    const jsFile = path.join(webviewsDir, `${webviewName}.js`);
    const cssFile = path.join(webviewsDir, `${webviewName}.css`);
    const baseCssFile = path.join(webviewsDir, 'index.css');

    return {
        js: fs.existsSync(jsFile) ? jsFile : null,
        css: fs.existsSync(cssFile) ? cssFile : null,
        baseCss: fs.existsSync(baseCssFile) ? baseCssFile : null,
    };
}

/**
 * Options for building webview HTML.
 */
export interface WebviewHtmlOptions {
    webview: vscode.Webview;
    assets: WebviewAssets;
    title: string;
}

/**
 * Build HTML content for a React webview.
 *
 * Returns the complete HTML document with:
 * - Proper CSP headers
 * - Base CSS (index.css) and component CSS
 * - React app entry point
 */
export function buildWebviewHtml(options: WebviewHtmlOptions): string {
    const { webview, assets, title } = options;

    if (!assets.js) {
        return buildNotBuiltHtml();
    }

    const nonce = getNonce();
    const jsUri = webview.asWebviewUri(vscode.Uri.file(assets.js));
    const baseCssUri = assets.baseCss ? webview.asWebviewUri(vscode.Uri.file(assets.baseCss)) : null;
    const cssUri = assets.css ? webview.asWebviewUri(vscode.Uri.file(assets.css)) : null;

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="
        default-src 'none';
        style-src ${webview.cspSource} 'unsafe-inline';
        script-src 'nonce-${nonce}';
        font-src ${webview.cspSource};
    ">
    <title>${title}</title>
    ${baseCssUri ? `<link rel="stylesheet" href="${baseCssUri}">` : ''}
    ${cssUri ? `<link rel="stylesheet" href="${cssUri}">` : ''}
</head>
<body>
    <div id="root"></div>
    <script nonce="${nonce}" type="module" src="${jsUri}"></script>
</body>
</html>`;
}

/**
 * Build HTML for when webviews haven't been built yet.
 */
export function buildNotBuiltHtml(): string {
    return `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            background: var(--vscode-sideBar-background);
            color: var(--vscode-foreground);
            font-family: var(--vscode-font-family);
            text-align: center;
            padding: 16px;
        }
        code {
            background: var(--vscode-textCodeBlock-background);
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div>
        <p>Webview not built.</p>
        <p>Run <code>npm run build:webviews</code></p>
    </div>
</body>
</html>`;
}

/**
 * Get the local resource roots for webview options.
 */
export function getWebviewLocalResourceRoots(extensionUri: vscode.Uri): vscode.Uri[] {
    const extensionPath = extensionUri.fsPath;
    return [
        vscode.Uri.file(path.join(extensionPath, 'resources', 'webviews')),
        vscode.Uri.file(path.join(extensionPath, 'webviews', 'dist')),
    ];
}
