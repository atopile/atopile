/**
 * Stateless Sidebar Webview Provider.
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
 * Dev mode is detected by checking if the Vite manifest exists.
 */
function isDevelopmentMode(extensionPath: string): boolean {
  // In production, webviews are in resources/webviews/
  // In development, we use the Vite dev server
  const prodPath = path.join(extensionPath, 'resources', 'webviews', 'sidebar.js');
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

export class SidebarProvider implements vscode.WebviewViewProvider {
  // Must match the view ID in package.json "views" section
  public static readonly viewType = 'atopile.project';

  private _view?: vscode.WebviewView;

  constructor(private readonly _extensionUri: vscode.Uri) {}

  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this._view = webviewView;

    const extensionPath = this._extensionUri.fsPath;
    const isDev = isDevelopmentMode(extensionPath);

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: isDev
        ? [] // No local resources in dev mode
        : [
            vscode.Uri.file(path.join(extensionPath, 'resources', 'webviews')),
            vscode.Uri.file(path.join(extensionPath, 'webviews', 'dist')),
          ],
    };

    if (isDev) {
      webviewView.webview.html = this._getDevHtml();
    } else {
      webviewView.webview.html = this._getProdHtml(webviewView.webview);
    }
  }

  /**
   * Get workspace folder paths from VS Code.
   */
  private _getWorkspaceFolders(): string[] {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders) return [];
    return folders.map(f => f.uri.fsPath);
  }

  /**
   * Development HTML - loads from Vite dev server.
   * The React app connects directly to the Python backend.
   * Workspace folders are passed via URL query params since iframe can't access parent window.
   */
  private _getDevHtml(): string {
    const viteDevServer = 'http://localhost:5173';
    const backendUrl = backendServer.apiUrl;
    const wsUrl = backendServer.wsUrl;
    const workspaceFolders = this._getWorkspaceFolders();

    // Pass workspace folders as URL query param (base64 encoded to handle special chars)
    const workspaceParam = workspaceFolders.length > 0
      ? `?workspace=${encodeURIComponent(JSON.stringify(workspaceFolders))}`
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
    connect-src ${viteDevServer} ${backendUrl} ${wsUrl};
  ">
  <title>atopile</title>
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
  <iframe src="${viteDevServer}/sidebar.html${workspaceParam}"></iframe>
</body>
</html>`;
  }

  /**
   * Production HTML - loads from compiled assets.
   * The React app connects directly to the Python backend.
   */
  private _getProdHtml(webview: vscode.Webview): string {
    const extensionPath = this._extensionUri.fsPath;
    const nonce = getNonce();

    // Find compiled assets
    const webviewsDir = path.join(extensionPath, 'resources', 'webviews');
    const jsPath = path.join(webviewsDir, 'sidebar.js');
    const cssPath = path.join(webviewsDir, 'sidebar.css');
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
    const workspaceFolders = this._getWorkspaceFolders();

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
    connect-src ${apiUrl} ${wsUrl};
  ">
  <title>atopile</title>
  ${baseCssUri ? `<link rel="stylesheet" href="${baseCssUri}">` : ''}
  ${cssUri ? `<link rel="stylesheet" href="${cssUri}">` : ''}
  <script nonce="${nonce}">
    // Inject backend URLs for the React app
    window.__ATOPILE_API_URL__ = '${apiUrl}';
    window.__ATOPILE_WS_URL__ = '${wsUrl}';
    // Inject workspace folders for the React app
    window.__ATOPILE_WORKSPACE_FOLDERS__ = ${JSON.stringify(workspaceFolders)};
  </script>
</head>
<body>
  <div id="root"></div>
  <script nonce="${nonce}" type="module" src="${jsUri}"></script>
</body>
</html>`;
  }

  /**
   * HTML shown when webviews haven't been built.
   */
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
