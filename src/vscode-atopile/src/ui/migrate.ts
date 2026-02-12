/**
 * Migrate Webview — opens the migration UI as a VS Code editor tab.
 *
 * In development: Loads from Vite dev server (http://localhost:5173)
 * In production: Loads from compiled assets
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { backendServer } from '../common/backendServer';
import { createWebviewOptions, getNonce, getWsOrigin } from '../common/webview';

const PROD_LOCAL_RESOURCE_ROOTS = ['resources/webviews', 'webviews/dist'];

function isDevelopmentMode(extensionPath: string): boolean {
  const prodPath = path.join(extensionPath, 'resources', 'webviews', 'migrate.js');
  return !fs.existsSync(prodPath);
}

let panel: vscode.WebviewPanel | undefined;

export function openMigratePreview(extensionUri: vscode.Uri, projectRoot: string): void {
  const extensionPath = extensionUri.fsPath;
  const isDev = isDevelopmentMode(extensionPath);

  if (panel) {
    panel.reveal(vscode.ViewColumn.Beside);
    return;
  }

  const webviewOptions = createWebviewOptions({
    isDev,
    extensionPath,
    port: backendServer.port,
    prodLocalResourceRoots: PROD_LOCAL_RESOURCE_ROOTS,
  });

  panel = vscode.window.createWebviewPanel(
    'atopile.migrate',
    'Migrate Project',
    vscode.ViewColumn.Beside,
    webviewOptions,
  );

  panel.webview.html = isDev
    ? getDevHtml(projectRoot)
    : getProdHtml(panel.webview, extensionPath, projectRoot);

  // Handle messages from the migrate webview
  panel.webview.onDidReceiveMessage((message) => {
    if (message.type === 'closeMigrateTab') {
      panel?.dispose();
    }
  });

  panel.onDidDispose(() => {
    panel = undefined;
  });
}

export function closeMigratePreview(): void {
  panel?.dispose();
  panel = undefined;
}

function getDevHtml(projectRoot: string): string {
  const viteDevServer = 'http://localhost:5173';
  const apiUrl = backendServer.apiUrl;
  const wsUrl = backendServer.wsUrl;
  const wsOrigin = getWsOrigin(wsUrl);

  const projectParam = projectRoot
    ? `?projectRoot=${encodeURIComponent(projectRoot)}`
    : '';

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="
    default-src 'none';
    frame-src ${viteDevServer};
    style-src 'unsafe-inline';
    script-src 'unsafe-inline';
    img-src https: http: data:;
    connect-src ${viteDevServer} ${apiUrl} ${wsOrigin};
  ">
  <title>Migrate Project</title>
  <style>
    html, body {
      margin: 0;
      padding: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
    }
    iframe {
      width: 100%;
      height: 100%;
      border: none;
    }
    .dev-banner {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      background: #ff6b35;
      color: white;
      padding: 2px 8px;
      font-size: 10px;
      text-align: center;
      z-index: 1000;
    }
  </style>
</head>
<body>
  <div class="dev-banner">DEV MODE - Loading from Vite</div>
  <iframe src="${viteDevServer}/migrate.html${projectParam}"></iframe>
</body>
</html>`;
}

function getProdHtml(webview: vscode.Webview, extensionPath: string, projectRoot: string): string {
  const nonce = getNonce();

  const webviewsDir = path.join(extensionPath, 'resources', 'webviews');
  const jsPath = path.join(webviewsDir, 'migrate.js');
  const cssPath = path.join(webviewsDir, 'migrate.css');
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
  <meta http-equiv="Content-Security-Policy" content="
    default-src 'none';
    style-src ${webview.cspSource} 'unsafe-inline';
    script-src ${webview.cspSource} 'nonce-${nonce}';
    font-src ${webview.cspSource};
    img-src ${webview.cspSource} data: https: http:;
    connect-src ${apiUrl} ${wsOrigin};
  ">
  <title>Migrate Project</title>
  ${baseCssUri ? `<link rel="stylesheet" href="${baseCssUri}">` : ''}
  ${cssUri ? `<link rel="stylesheet" href="${cssUri}">` : ''}
  <script nonce="${nonce}">
    window.__ATOPILE_API_URL__ = '${apiUrl}';
    window.__ATOPILE_WS_URL__ = '${wsOrigin}';
    window.__ATOPILE_MIGRATE_PROJECT__ = ${JSON.stringify(projectRoot)};
  </script>
</head>
<body>
  <div id="root"></div>
  <script nonce="${nonce}" type="module" src="${jsUri}"></script>
</body>
</html>`;
}
