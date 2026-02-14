/**
 * Stateless Log Viewer Webview Provider.
 *
 * This provider is minimal - it just opens the webview and loads the UI.
 * All state management and backend communication happens in the React app.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { backendServer } from '../common/backendServer';
import { createWebviewOptions, getNonce, getWsOrigin } from '../common/webview';

export class LogViewerProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'atopile.logViewer';
  private static readonly PROD_LOCAL_RESOURCE_ROOTS = ['resources/webviews', 'webviews/dist'];

  private _view?: vscode.WebviewView;
  private _disposables: vscode.Disposable[] = [];
  private _hasHtml = false;
  private _lastApiUrl: string | null = null;
  private _lastWsUrl: string | null = null;

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
      return;
    }

    const extensionPath = this._extensionUri.fsPath;
    const apiUrl = backendServer.apiUrl;
    const wsUrl = backendServer.wsUrl;

    // Port changes are always reflected in apiUrl/wsUrl (see backendServer._setPort)
    if (this._hasHtml && this._lastApiUrl === apiUrl && this._lastWsUrl === wsUrl) {
      return;
    }

    this._view.webview.options = createWebviewOptions({
      extensionPath,
      port: backendServer.port,
      prodLocalResourceRoots: LogViewerProvider.PROD_LOCAL_RESOURCE_ROOTS,
    });
    this._view.webview.html = this._getProdHtml(this._view.webview);
    this._hasHtml = true;
    this._lastApiUrl = apiUrl;
    this._lastWsUrl = wsUrl;
  }

  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this._view = webviewView;
    this._refreshWebview();
  }

  /**
   * Get the webview HTML - loads from compiled assets.
   */
  private _getProdHtml(webview: vscode.Webview): string {
    const extensionPath = this._extensionUri.fsPath;
    const nonce = getNonce();

    const webviewsDir = path.join(extensionPath, 'resources', 'webviews');
    const jsPath = path.join(webviewsDir, 'logViewer.js');
    const cssPath = path.join(webviewsDir, 'LogViewer.css');
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
  <title>atopile Logs</title>
  ${baseCssUri ? `<link rel="stylesheet" href="${baseCssUri}">` : ''}
  ${cssUri ? `<link rel="stylesheet" href="${cssUri}">` : ''}
  <script nonce="${nonce}">
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
