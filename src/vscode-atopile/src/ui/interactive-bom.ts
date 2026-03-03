/**
 * Interactive BOM Webview — opens the interactive BOM UI as a VS Code editor tab.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { backendServer } from '../common/backendServer';
import { createWebviewOptions, getNonce, getWsOrigin } from '../common/webview';

const PROD_LOCAL_RESOURCE_ROOTS = ['resources/webviews', 'webviews/dist'];

let panel: vscode.WebviewPanel | undefined;

export function openInteractiveBomPreview(extensionUri: vscode.Uri): void {
  const extensionPath = extensionUri.fsPath;

  if (panel) {
    panel.reveal(vscode.ViewColumn.Beside);
    return;
  }

  const webviewOptions = createWebviewOptions({
    extensionPath,
    port: backendServer.port,
    prodLocalResourceRoots: PROD_LOCAL_RESOURCE_ROOTS,
  });

  panel = vscode.window.createWebviewPanel(
    'atopile.interactiveBom',
    'Interactive BOM',
    vscode.ViewColumn.Beside,
    webviewOptions,
  );

  panel.webview.html = getProdHtml(panel.webview, extensionPath);

  panel.onDidDispose(() => {
    panel = undefined;
  });
}

export function isInteractiveBomOpen(): boolean {
  return panel !== undefined;
}

export function closeInteractiveBom(): void {
  panel?.dispose();
  panel = undefined;
}

function getProdHtml(webview: vscode.Webview, extensionPath: string): string {
  const nonce = getNonce();

  const webviewsDir = path.join(extensionPath, 'resources', 'webviews');
  const jsPath = path.join(webviewsDir, 'interactiveBom.js');
  const cssPath = path.join(webviewsDir, 'interactiveBom.css');
  const baseCssPath = path.join(webviewsDir, 'index.css');

  if (!fs.existsSync(jsPath)) {
    return `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
  <style>
    body {
      display: flex; align-items: center; justify-content: center;
      height: 100vh; margin: 0;
      background: var(--vscode-editor-background);
      color: var(--vscode-foreground);
      font-family: var(--vscode-font-family);
      text-align: center; padding: 16px;
    }
    code { background: var(--vscode-textCodeBlock-background); padding: 2px 6px; border-radius: 3px; font-size: 12px; }
  </style>
</head>
<body>
  <div><p>Webview not built.</p><p>Run <code>npm run build</code> in the webviews directory.</p></div>
</body>
</html>`;
  }

  const jsUri = webview.asWebviewUri(vscode.Uri.file(jsPath));
  const baseUri = webview.asWebviewUri(vscode.Uri.file(webviewsDir + '/'));
  const cssUri = fs.existsSync(cssPath)
    ? webview.asWebviewUri(vscode.Uri.file(cssPath))
    : null;
  const baseCssUri = fs.existsSync(baseCssPath)
    ? webview.asWebviewUri(vscode.Uri.file(baseCssPath))
    : null;

  const apiUrl = backendServer.apiUrl;
  const wsUrl = backendServer.wsUrl;
  const wsOrigin = getWsOrigin(wsUrl);

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <base href="${baseUri}">
  <meta http-equiv="Content-Security-Policy" content="
    default-src 'none';
    style-src ${webview.cspSource} 'unsafe-inline';
    script-src ${webview.cspSource} 'nonce-${nonce}' 'wasm-unsafe-eval' 'unsafe-eval';
    font-src ${webview.cspSource};
    img-src ${webview.cspSource} data: https: http:;
    connect-src ${webview.cspSource} ${apiUrl} ${wsOrigin};
  ">
  <title>Interactive BOM</title>
  ${baseCssUri ? `<link rel="stylesheet" href="${baseCssUri}">` : ''}
  ${cssUri ? `<link rel="stylesheet" href="${cssUri}">` : ''}
  <script nonce="${nonce}">
    window.__LAYOUT_BASE_URL__ = '${apiUrl}'.replace(/\\/api$/, '');
    window.__LAYOUT_API_PREFIX__ = '/api/layout';
    window.__LAYOUT_WS_PATH__ = '/ws/layout';
    window.__ATOPILE_API_URL__ = '${apiUrl}';
    window.__ATOPILE_WS_URL__ = '${wsOrigin}';
  </script>
</head>
<body>
  <div id="root"></div>
  <script nonce="${nonce}" type="module" src="${jsUri}"></script>
</body>
</html>`;
}
