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
import { traceInfo, traceError } from '../common/log/logging';
import { openPcb } from '../common/kicad';
import { setCurrentPCB } from '../common/pcb';
import { setCurrentThreeDModel } from '../common/3dmodel';
import { openKiCanvasPreview } from '../ui/kicanvas';
import { openModelViewerPreview } from '../ui/modelviewer';

// Message types from the webview
interface OpenSignalsMessage {
  type: 'openSignals';
  openFile?: string | null;
  openFileLine?: number | null;
  openFileColumn?: number | null;
  openLayout?: string | null;
  openKicad?: string | null;
  open3d?: string | null;
}

interface ConnectionStatusMessage {
  type: 'connectionStatus';
  isConnected: boolean;
}

interface AtopileSettingsMessage {
  type: 'atopileSettings';
  atopile: {
    source?: string;
    currentVersion?: string;
    branch?: string | null;
    localPath?: string | null;
  };
}

type WebviewMessage = OpenSignalsMessage | ConnectionStatusMessage | AtopileSettingsMessage;

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

function getWsOrigin(wsUrl: string): string {
  try {
    return new URL(wsUrl).origin;
  } catch {
    return wsUrl;
  }
}

export class SidebarProvider implements vscode.WebviewViewProvider {
  // Must match the view ID in package.json "views" section
  public static readonly viewType = 'atopile.sidebar';

  private _view?: vscode.WebviewView;
  private _disposables: vscode.Disposable[] = [];
  private _lastMode: 'dev' | 'prod' | null = null;
  private _hasHtml: boolean = false;
  private _lastWorkspaceRoot: string | null = null;
  private _lastApiUrl: string | null = null;
  private _lastWsUrl: string | null = null;

  constructor(
    private readonly _extensionUri: vscode.Uri,
    private readonly _extensionVersion: string
  ) {
    this._disposables.push(
      backendServer.onStatusChange((connected) => {
        if (connected) {
          this._refreshWebview();
        }
      })
    );
    this._disposables.push(
      vscode.workspace.onDidChangeWorkspaceFolders(() => {
        this._postWorkspaceRoot();
      })
    );
    // Forward messages from backendServer to webview
    this._disposables.push(
      backendServer.onWebviewMessage((message) => {
        this._postToWebview(message);
      })
    );
    // Track active editor changes and notify webview
    this._disposables.push(
      vscode.window.onDidChangeActiveTextEditor((editor) => {
        this._postActiveFile(editor);
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
      traceInfo('[SidebarProvider] _refreshWebview called but no view');
      return;
    }

    traceInfo('[SidebarProvider] Refreshing webview with URLs:', {
      apiUrl: backendServer.apiUrl,
      wsUrl: backendServer.wsUrl,
      port: backendServer.port,
      isConnected: backendServer.isConnected,
    });

    const extensionPath = this._extensionUri.fsPath;
    const isDev = isDevelopmentMode(extensionPath);
    const mode: 'dev' | 'prod' = isDev ? 'dev' : 'prod';

    const apiUrl = backendServer.apiUrl;
    const wsUrl = backendServer.wsUrl;
    const urlsUnchanged = this._lastApiUrl === apiUrl && this._lastWsUrl === wsUrl;
    if (this._hasHtml && this._lastMode === mode && urlsUnchanged) {
      traceInfo('[SidebarProvider] Skipping refresh (already loaded)', { mode });
      return;
    }

    if (isDev) {
      this._view.webview.html = this._getDevHtml();
    } else {
      this._view.webview.html = this._getProdHtml(this._view.webview);
    }
    this._hasHtml = true;
    this._lastMode = mode;
    this._lastApiUrl = apiUrl;
    this._lastWsUrl = wsUrl;
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

    traceInfo('[SidebarProvider] resolveWebviewView called', {
      extensionPath,
      isDev,
      apiUrl: backendServer.apiUrl,
      wsUrl: backendServer.wsUrl,
    });

    const webviewOptions: vscode.WebviewOptions & {
      retainContextWhenHidden?: boolean;
    } = {
      enableScripts: true,
      retainContextWhenHidden: true,
      localResourceRoots: isDev
        ? [] // No local resources in dev mode
        : [
            vscode.Uri.file(path.join(extensionPath, 'resources')),
            vscode.Uri.file(path.join(extensionPath, 'resources', 'webviews')),
            vscode.Uri.file(path.join(extensionPath, 'webviews', 'dist')),
          ],
    };
    webviewView.webview.options = webviewOptions;

    if (isDev) {
      traceInfo('[SidebarProvider] Using dev HTML');
      webviewView.webview.html = this._getDevHtml();
    } else {
      traceInfo('[SidebarProvider] Using prod HTML');
      const html = this._getProdHtml(webviewView.webview);
      traceInfo('[SidebarProvider] Generated HTML length:', html.length);
      webviewView.webview.html = html;
    }
    this._hasHtml = true;
    this._lastMode = mode;
    this._lastApiUrl = backendServer.apiUrl;
    this._lastWsUrl = backendServer.wsUrl;
    this._postWorkspaceRoot();
    // Send current active file to webview
    this._postActiveFile(vscode.window.activeTextEditor);

    // Listen for messages from webview
    this._disposables.push(
      webviewView.webview.onDidReceiveMessage(
        (message: WebviewMessage) => this._handleWebviewMessage(message),
        undefined
      )
    );
  }

  /**
   * Get workspace folder paths from VS Code.
   */
  private _getWorkspaceRoot(): string | null {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) return null;
    return folders[0].uri.fsPath;
  }

  private _postWorkspaceRoot(): void {
    if (!this._view) {
      return;
    }
    const root = this._getWorkspaceRoot();
    if (this._lastWorkspaceRoot === root) {
      return;
    }
    this._lastWorkspaceRoot = root;
    this._view.webview.postMessage({ type: 'workspace-root', root });
  }

  /**
   * Post the active file to the webview so the Structure panel can track it.
   */
  private _postActiveFile(editor?: vscode.TextEditor): void {
    if (!this._view) {
      return;
    }
    const filePath = editor?.document?.uri?.fsPath ?? null;
    traceInfo(`[SidebarProvider] Posting active file: ${filePath}`);
    this._view.webview.postMessage({ type: 'activeFile', filePath });
  }

  /**
   * Post a message to the webview.
   */
  private _postToWebview(message: Record<string, unknown>): void {
    if (!this._view) {
      traceInfo('[SidebarProvider] Cannot post message - no view');
      return;
    }
    this._view.webview.postMessage(message);
  }

  /**
   * Handle messages from the webview (forwarded from ui-server via postMessage).
   */
  private _handleWebviewMessage(message: WebviewMessage): void {
    switch (message.type) {
      case 'openSignals':
        this._handleOpenSignals(message);
        break;
      case 'connectionStatus':
        backendServer.setConnected(message.isConnected);
        break;
      case 'atopileSettings':
        this._handleAtopileSettings(message.atopile);
        break;
      default:
        traceInfo(`[SidebarProvider] Unknown message type: ${(message as Record<string, unknown>).type}`);
    }
  }

  /**
   * Handle open signals from the backend.
   */
  private _handleOpenSignals(msg: OpenSignalsMessage): void {
    if (msg.openFile) {
      this._openFile(msg.openFile, msg.openFileLine ?? undefined, msg.openFileColumn ?? undefined);
    }
    if (msg.openLayout) {
      this._openLayoutPreview(msg.openLayout);
    }
    if (msg.openKicad) {
      this._openWithKicad(msg.openKicad);
    }
    if (msg.open3d) {
      this._open3dPreview(msg.open3d);
    }
  }

  /**
   * Open a file in VS Code at a specific line and column.
   */
  private _openFile(filePath: string, line?: number, column?: number): void {
    traceInfo(`[SidebarProvider] Opening file: ${filePath}${line ? `:${line}` : ''}`);
    const uri = vscode.Uri.file(filePath);
    vscode.workspace.openTextDocument(uri).then(
      (doc) => {
        const options: vscode.TextDocumentShowOptions = {};
        if (line != null) {
          const position = new vscode.Position(Math.max(0, line - 1), column ?? 0);
          options.selection = new vscode.Range(position, position);
        }
        vscode.window.showTextDocument(doc, options);
      },
      (err) => {
        traceError(`[SidebarProvider] Failed to open file ${filePath}: ${err}`);
      }
    );
  }

  /**
   * Open a file in VS Code (for layout files).
   */
  private _openWithVSCode(filePath: string): void {
    traceInfo(`[SidebarProvider] Opening with VS Code: ${filePath}`);
    vscode.commands.executeCommand('vscode.open', vscode.Uri.file(filePath));
  }

  private _findFirstFileByExt(dirPath: string, ext: string): string | null {
    try {
      const entries = fs.readdirSync(dirPath, { withFileTypes: true });
      for (const entry of entries) {
        if (entry.isFile() && entry.name.toLowerCase().endsWith(ext)) {
          return path.join(dirPath, entry.name);
        }
      }
    } catch (error) {
      traceError(`[SidebarProvider] Failed to read directory ${dirPath}: ${error}`);
    }
    return null;
  }

  private _resolveFilePath(filePath: string, ext: string): string | null {
    if (!fs.existsSync(filePath)) {
      return null;
    }
    try {
      const stat = fs.statSync(filePath);
      if (stat.isFile()) {
        return filePath.toLowerCase().endsWith(ext) ? filePath : null;
      }
      if (stat.isDirectory()) {
        return this._findFirstFileByExt(filePath, ext);
      }
    } catch (error) {
      traceError(`[SidebarProvider] Failed to stat ${filePath}: ${error}`);
    }
    return null;
  }

  private _openLayoutPreview(filePath: string): void {
    const pcbPath = this._resolveFilePath(filePath, '.kicad_pcb');
    if (!pcbPath) {
      traceError(`[SidebarProvider] Layout file not found: ${filePath}`);
      vscode.window.showErrorMessage('Layout file not found. Run a build to generate it.');
      return;
    }
    setCurrentPCB({ path: pcbPath, exists: true });
    void openKiCanvasPreview();
  }

  private _openWithKicad(filePath: string): void {
    const pcbPath = this._resolveFilePath(filePath, '.kicad_pcb');
    if (!pcbPath) {
      traceError(`[SidebarProvider] KiCad layout file not found: ${filePath}`);
      vscode.window.showErrorMessage('KiCad layout file not found. Run a build to generate it.');
      return;
    }
    void openPcb(pcbPath).catch((error) => {
      traceError(`[SidebarProvider] Failed to open KiCad: ${error}`);
      vscode.window.showErrorMessage(`Failed to open KiCad: ${error instanceof Error ? error.message : error}`);
    });
  }

  private _open3dPreview(filePath: string): void {
    const modelPath = this._resolveFilePath(filePath, '.glb');
    if (!modelPath) {
      traceError(`[SidebarProvider] 3D model not found: ${filePath}`);
      vscode.window.showErrorMessage('3D model not found. Run a build to generate it.');
      return;
    }
    setCurrentThreeDModel({ path: modelPath, exists: true });
    void openModelViewerPreview();
  }

  /**
   * Open a file with the system default application (for KiCad, 3D files).
   * Uses VS Code's openExternal API which is safe and cross-platform.
   */
  private _openWithSystem(filePath: string): void {
    traceInfo(`[SidebarProvider] Opening with system: ${filePath}`);
    const uri = vscode.Uri.file(filePath);
    vscode.env.openExternal(uri).then(
      (success) => {
        if (!success) {
          traceError(`[SidebarProvider] Failed to open: ${filePath}`);
          vscode.window.showErrorMessage(`Failed to open file with system application`);
        }
      },
      (err) => {
        traceError(`[SidebarProvider] Failed to open: ${err}`);
        vscode.window.showErrorMessage(`Failed to open: ${err.message}`);
      }
    );
  }

  /**
   * Handle atopile settings changes from the UI.
   * Syncs atopile settings to VS Code configuration.
   */
  private _handleAtopileSettings(atopile: AtopileSettingsMessage['atopile']): void {
    if (!atopile) return;

    // Store for comparison to avoid unnecessary updates
    const settingsKey = JSON.stringify({
      source: atopile.source,
      currentVersion: atopile.currentVersion,
      branch: atopile.branch,
      localPath: atopile.localPath,
    });

    // Skip if nothing changed (we'd need to track this, but for simplicity we'll always update)
    // This is called on every state update, so we should be careful not to spam config changes

    const config = vscode.workspace.getConfiguration('atopile');
    const hasWorkspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length > 0;
    const target = hasWorkspace ? vscode.ConfigurationTarget.Workspace : vscode.ConfigurationTarget.Global;

    try {
      if (atopile.source === 'local' && atopile.localPath) {
        // For local mode, set the 'ato' setting directly
        traceInfo(`[SidebarProvider] Setting atopile.ato = ${atopile.localPath}`);
        config.update('ato', atopile.localPath, target);
        config.update('from', undefined, target);
      } else {
        // For release/branch mode, set the 'from' setting
        const fromValue = this._atopileSettingsToFrom(atopile);
        traceInfo(`[SidebarProvider] Setting atopile.from = ${fromValue}`);
        config.update('from', fromValue, target);
        config.update('ato', undefined, target);
      }
    } catch (error) {
      traceError(`[SidebarProvider] Failed to update atopile settings: ${error}`);
    }
  }

  /**
   * Convert UI atopile settings to a VS Code 'atopile.from' setting value.
   */
  private _atopileSettingsToFrom(atopile: AtopileSettingsMessage['atopile']): string {
    if (!atopile) return 'atopile';

    switch (atopile.source) {
      case 'release':
        return atopile.currentVersion
          ? `atopile@${atopile.currentVersion}`
          : 'atopile';
      case 'branch':
        return `git+https://github.com/atopile/atopile.git@${atopile.branch || 'main'}`;
      case 'local':
        return atopile.localPath || '';
      default:
        return 'atopile';
    }
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
    const wsOrigin = getWsOrigin(wsUrl);
    const workspaceRoot = this._getWorkspaceRoot();

    const workspaceParam = workspaceRoot
      ? `?workspace=${encodeURIComponent(workspaceRoot)}`
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
    connect-src ${viteDevServer} ${backendUrl} ${wsOrigin};
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
  <script>
    window.addEventListener('message', (event) => {
      const data = event && event.data;
      if (!data || (data.type !== 'workspace-root' && data.type !== 'activeFile')) return;
      const iframe = document.querySelector('iframe');
      if (iframe && iframe.contentWindow) {
        iframe.contentWindow.postMessage(data, '*');
      }
    });
  </script>
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
    const iconPath = path.join(extensionPath, 'resources', 'atopile-icon.svg');

    traceInfo('[SidebarProvider] _getProdHtml paths:', {
      webviewsDir,
      jsPath,
      jsExists: fs.existsSync(jsPath),
      cssExists: fs.existsSync(cssPath),
      baseCssExists: fs.existsSync(baseCssPath),
    });

    if (!fs.existsSync(jsPath)) {
      traceInfo('[SidebarProvider] JS file not found, returning not built HTML');
      return this._getNotBuiltHtml();
    }

    const jsUri = webview.asWebviewUri(vscode.Uri.file(jsPath));
    const cssUri = fs.existsSync(cssPath)
      ? webview.asWebviewUri(vscode.Uri.file(cssPath))
      : null;
    const baseCssUri = fs.existsSync(baseCssPath)
      ? webview.asWebviewUri(vscode.Uri.file(baseCssPath))
      : null;
    const iconUri = fs.existsSync(iconPath)
      ? webview.asWebviewUri(vscode.Uri.file(iconPath)).toString()
      : '';

    // Get backend URLs from backendServer (uses discovered port or config)
    const apiUrl = backendServer.apiUrl;
    const wsUrl = backendServer.wsUrl;
    const wsOrigin = getWsOrigin(wsUrl);
    const workspaceRoot = this._getWorkspaceRoot();

    // Debug: log URLs being used
    traceInfo('SidebarProvider: Generating HTML with apiUrl:', apiUrl, 'wsUrl:', wsUrl);

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
    connect-src ${apiUrl} ${wsOrigin};
  ">
  <title>atopile</title>
  ${baseCssUri ? `<link rel="stylesheet" href="${baseCssUri}">` : ''}
  ${cssUri ? `<link rel="stylesheet" href="${cssUri}">` : ''}
  <script nonce="${nonce}">
    // Debug info
    console.log('[atopile webview] Initializing...');
    console.log('[atopile webview] API URL:', '${apiUrl}');
    console.log('[atopile webview] WS URL:', '${wsUrl}');

    // Inject backend URLs for the React app
    window.__ATOPILE_API_URL__ = '${apiUrl}';
    window.__ATOPILE_WS_URL__ = '${wsOrigin}';
    window.__ATOPILE_ICON_URL__ = '${iconUri}';
    window.__ATOPILE_EXTENSION_VERSION__ = '${this._extensionVersion}';
    // Inject workspace root for the React app
    window.__ATOPILE_WORKSPACE_ROOT__ = ${JSON.stringify(workspaceRoot || '')};
  </script>
  <style>
    /* Debug: loading indicator */
    #debug-loading {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      padding: 8px;
      background: #1a1a2e;
      color: #fff;
      font-family: monospace;
      font-size: 11px;
      z-index: 9999;
    }
  </style>
</head>
<body>
  <div id="debug-loading">Loading atopile... API: ${apiUrl}</div>
  <div id="root"></div>
  <script nonce="${nonce}" type="module" src="${jsUri}"></script>
  <script nonce="${nonce}">
    // Remove debug loading indicator once React renders
    window.addEventListener('load', () => {
      setTimeout(() => {
        const debug = document.getElementById('debug-loading');
        if (debug && document.getElementById('root').children.length > 0) {
          debug.remove();
        }
      }, 2000);
    });
  </script>
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
