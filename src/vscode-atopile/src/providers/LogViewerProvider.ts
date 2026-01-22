/**
 * Stateless Log Viewer Webview Provider.
 *
 * This provider is minimal - it just opens the webview and loads the UI.
 * All state management and backend communication happens in the React app.
 *
 * In development: Loads from Vite dev server (http://localhost:5173)
 * In production: Loads from compiled assets
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { backendServer } from '../common/backendServer';

/**
 * Check if we're running in development mode.
 */
function isDevelopmentMode(extensionPath: string): boolean {
  const prodPath = path.join(extensionPath, 'resources', 'webviews', 'logViewer.js');
  return !fs.existsSync(prodPath);
}

/**
 * Generate a nonce for Content Security Policy.
 */
function getNonce(): string {
  let text = '';
  const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  for (let i = 0; i < 32; i++) {
    text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return text;
}

export class LogViewerProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'atopile.logViewer';

  private _view?: vscode.WebviewView;
  private _disposables: vscode.Disposable[] = [];
  private _lastMode: 'dev' | 'prod' | null = null;
  private _hasHtml: boolean = false;

  constructor(private readonly _extensionUri: vscode.Uri) {
    this._disposables.push(
      backendServer.onStatusChange((connected) => {
        if (connected) {
          this._refreshWebview();
        }
      })
    );
  }

  dispose(): void {
    for (const d of this._disposables) {
      d.dispose();
    }
    this._disposables = [];
  }

  private _refreshWebview(): void {
    if (!this._view) {
      console.log('[LogViewerProvider] _refreshWebview called but no view');
      return;
    }

    console.log('[LogViewerProvider] Refreshing webview with URLs:', {
      apiUrl: backendServer.apiUrl,
      wsUrl: backendServer.wsUrl,
      port: backendServer.port,
      isConnected: backendServer.isConnected,
    });

    const extensionPath = this._extensionUri.fsPath;
    const isDev = isDevelopmentMode(extensionPath);
    const mode: 'dev' | 'prod' = isDev ? 'dev' : 'prod';

    if (this._hasHtml && this._lastMode === mode) {
      console.log('[LogViewerProvider] Skipping refresh (already loaded)', { mode });
      return;
    }

    if (isDev) {
      this._view.webview.html = this._getDevHtml();
    } else {
      this._view.webview.html = this._getProdHtml(this._view.webview);
    }
    this._hasHtml = true;
    this._lastMode = mode;
  }

  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this._view = webviewView;

    const extensionPath = this._extensionUri.fsPath;
    const isDev = isDevelopmentMode(extensionPath);
    const mode: 'dev' | 'prod' = isDev ? 'dev' : 'prod';

    const webviewOptions: vscode.WebviewOptions & {
      retainContextWhenHidden?: boolean;
    } = {
      enableScripts: true,
      retainContextWhenHidden: true,
      localResourceRoots: isDev
        ? []
        : [
            vscode.Uri.file(path.join(extensionPath, 'resources', 'webviews')),
            vscode.Uri.file(path.join(extensionPath, 'webviews', 'dist')),
          ],
    };
    webviewView.webview.options = webviewOptions;

    if (isDev) {
      webviewView.webview.html = this._getDevHtml();
    } else {
      webviewView.webview.html = this._getProdHtml(webviewView.webview);
    }
    this._hasHtml = true;
    this._lastMode = mode;
  }

  /**
   * Development HTML - loads from Vite dev server.
   */
  private _getDevHtml(): string {
    const viteDevServer = 'http://localhost:5173';
    const apiUrl = backendServer.apiUrl;
    const wsUrl = backendServer.wsUrl;

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
    connect-src ${viteDevServer} ${apiUrl} ${wsUrl};
  ">
  <title>atopile Logs</title>
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
  <iframe src="${viteDevServer}/logViewer.html"></iframe>
</body>
</html>`;
  }

  /**
   * Production HTML - loads from compiled assets.
   */
  private _getProdHtml(webview: vscode.Webview): string {
    const extensionPath = this._extensionUri.fsPath;
    const nonce = getNonce();

    const webviewsDir = path.join(extensionPath, 'resources', 'webviews');
    const jsPath = path.join(webviewsDir, 'logViewer.js');
    const cssPath = path.join(webviewsDir, 'logViewer.css');
    const baseCssPath = path.join(webviewsDir, 'index.css');

    if (!fs.existsSync(jsPath)) {
      return this._getNotBuiltHtml();
    }

    const jsUri = webview.asWebviewUri(vscode.Uri.file(jsPath));
    const cssUri = fs.existsSync(cssPath)
      ? webview.asWebviewUri(vscode.Uri.file(cssPath))
      : null;
    const baseCssUri = fs.existsSync(baseCssPath)
      ? webview.asWebviewUri(vscode.Uri.file(baseCssPath))
      : null;

    // Get backend URLs from backendServer (uses discovered port or config)
    const apiUrl = backendServer.apiUrl;
    const wsUrl = backendServer.wsUrl;

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
    img-src ${webview.cspSource} data:;
    connect-src ${apiUrl} ${wsUrl} ws://localhost:* http://localhost:*;
  ">
  <title>atopile Logs</title>
  ${baseCssUri ? `<link rel="stylesheet" href="${baseCssUri}">` : ''}
  ${cssUri ? `<link rel="stylesheet" href="${cssUri}">` : ''}
  <script nonce="${nonce}">
    window.__ATOPILE_API_URL__ = '${apiUrl}';
    window.__ATOPILE_WS_URL__ = '${wsUrl}';
  </script>
</head>
<body>
  <div id="root"></div>
  <script nonce="${nonce}" type="module" src="${jsUri}"></script>
</body>
</html>`;
  }

  private _getNotBuiltHtml(): string {
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
    <p>Run <code>npm run build</code> in the webviews directory.</p>
  </div>
</body>
</html>`;
  }
}
