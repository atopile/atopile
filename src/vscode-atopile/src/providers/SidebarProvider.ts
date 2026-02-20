/**
 * Stateless Sidebar Webview Provider.
 *
 * This provider is minimal - it just opens the webview and loads the UI.
 * All state management and backend communication happens in the React app.
 *
 * Heavy logic is delegated to focused modules in ./sidebar/:
 * - types.ts: Message interfaces
 * - file-watcher.ts: File system watching
 * - file-operations.ts: File CRUD + listing
 * - action-handlers.ts: Open signals, KiCad, 3D, selection
 * - settings-handlers.ts: Atopile settings sync + browse dialogs
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { backendServer } from '../common/backendServer';
import { traceInfo, traceError, traceVerbose, traceMilestone } from '../common/log/logging';
import { createWebviewOptions, getNonce, getWsOrigin } from '../common/webview';
import { WebviewProxyBridge } from '../common/webview-bridge';
import { generateBridgeRuntime } from '../common/webview-bridge-runtime';
import { getAtopileWorkspaceFolders } from '../common/vscodeapi';
import { openMigratePreview } from '../ui/migrate';
import type { WebviewMessage } from './sidebar/types';
import { SidebarFileWatcher } from './sidebar/file-watcher';
import { SidebarFileOperations } from './sidebar/file-operations';
import { SidebarActionHandlers } from './sidebar/action-handlers';
import { SidebarSettingsHandlers } from './sidebar/settings-handlers';

export class SidebarProvider implements vscode.WebviewViewProvider {
  // Must match the view ID in package.json "views" section
  public static readonly viewType = 'atopile.sidebar';
  private static readonly PROD_LOCAL_RESOURCE_ROOTS = [
    'resources',
    'resources/webviews',
    'resources/model-viewer',
    'webviews/dist',
  ];

  private _view?: vscode.WebviewView;
  private _disposables: vscode.Disposable[] = [];
  private _hasHtml = false;
  private _lastWorkspaceRoot: string | null = null;
  private _lastApiUrl: string | null = null;
  private _lastWsUrl: string | null = null;

  // Delegated modules
  private readonly _bridge: WebviewProxyBridge;
  private readonly _fileWatcher: SidebarFileWatcher;
  private readonly _fileOps: SidebarFileOperations;
  private readonly _actions: SidebarActionHandlers;
  private readonly _settings: SidebarSettingsHandlers;

  constructor(
    private readonly _extensionUri: vscode.Uri,
    private readonly _extensionVersion: string,
    private readonly _activationTime: number = Date.now()
  ) {
    const postToWebview = (msg: Record<string, unknown>) => this._postToWebview(msg);

    this._bridge = new WebviewProxyBridge({
      postToWebview,
      logTag: 'SidebarProvider',
    });
    this._fileWatcher = new SidebarFileWatcher({ postToWebview });
    this._fileOps = new SidebarFileOperations({
      postToWebview,
      notifyFilesChanged: () => this._fileWatcher.notifyFilesChanged(),
    });
    this._actions = new SidebarActionHandlers({
      onProjectSelected: (root) => root ? this._fileWatcher.watch(root) : this._fileWatcher.unwatch(),
    });
    this._settings = new SidebarSettingsHandlers({ postToWebview });

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
    // Send updated atopile settings to webview when configuration changes
    this._disposables.push(
      vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration('atopile.ato') || e.affectsConfiguration('atopile.from')) {
          traceInfo('[SidebarProvider] Atopile settings changed, notifying webview');
          this._settings.sendAtopileSettings();
        }
      })
    );
  }

  dispose(): void {
    for (const d of this._disposables) {
      d.dispose();
    }
    this._disposables = [];
    this._fileWatcher.dispose();
    this._bridge.dispose();
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
      prodLocalResourceRoots: SidebarProvider.PROD_LOCAL_RESOURCE_ROOTS,
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

    // Register message handler before setting HTML to avoid missing early
    // bootstrap messages from the webview (e.g. wsProxyConnect).
    this._disposables.push(
      webviewView.webview.onDidReceiveMessage(
        (message: WebviewMessage) => this._handleWebviewMessage(message),
        undefined
      )
    );

    // Listen to VS Code workspace file events as a fallback for file system
    // watcher failures in containerized environments (Docker, Fly.io).
    this._disposables.push(
      vscode.workspace.onDidCreateFiles(() => this._fileWatcher.notifyFilesChanged()),
      vscode.workspace.onDidDeleteFiles(() => this._fileWatcher.notifyFilesChanged()),
      vscode.workspace.onDidRenameFiles(() => this._fileWatcher.notifyFilesChanged()),
    );

    this._refreshWebview();
    this._postWorkspaceRoot();
    this._postActiveFile(vscode.window.activeTextEditor);
    this._settings.sendAtopileSettings();
  }

  // ── Workspace helpers ──────────────────────────────────────────────

  private _getWorkspaceRootSync(): string | null {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) return null;
    return folders[0].uri.fsPath;
  }

  private async _getWorkspaceRoot(): Promise<string | null> {
    const atopileWorkspaces = await getAtopileWorkspaceFolders();
    if (atopileWorkspaces.length > 0) {
      return atopileWorkspaces[0].uri.fsPath;
    }
    return this._getWorkspaceRootSync();
  }

  private async _postWorkspaceRoot(): Promise<void> {
    if (!this._view) {
      return;
    }
    const root = await this._getWorkspaceRoot();
    if (this._lastWorkspaceRoot === root) {
      return;
    }
    this._lastWorkspaceRoot = root;
    this._view.webview.postMessage({ type: 'workspace-root', root });
  }

  private _postActiveFile(editor?: vscode.TextEditor): void {
    if (!this._view) {
      return;
    }
    const filePath = editor?.document?.uri?.fsPath ?? null;
    traceInfo(`[SidebarProvider] Posting active file: ${filePath}`);
    this._view.webview.postMessage({ type: 'activeFile', filePath });
  }

  private _postToWebview(message: Record<string, unknown>): void {
    if (!this._view) {
      traceVerbose('[SidebarProvider] Cannot post message - no view');
      return;
    }
    this._view.webview.postMessage(message);
  }

  // ── Message routing ────────────────────────────────────────────────

  private _handleWebviewMessage(message: WebviewMessage): void {
    // Proxy messages (fetch, WebSocket) are handled by the shared bridge
    if (this._bridge.handleMessage(message)) return;

    switch (message.type) {
      case 'openSignals':
        this._actions.handleOpenSignals(message);
        break;
      case 'connectionStatus':
        backendServer.setConnected(message.isConnected);
        break;
      case 'atopileSettings':
        this._settings.handleAtopileSettings(message.atopile).catch((error) => {
          traceError(`[SidebarProvider] Error handling atopile settings: ${error}`);
        });
        break;
      case 'browseAtopilePath':
        this._settings.browseAtopilePath().catch((error) => {
          traceError(`[SidebarProvider] Error browsing atopile path: ${error}`);
        });
        break;
      case 'browseProjectPath':
        this._settings.browseProjectPath().catch((error) => {
          traceError(`[SidebarProvider] Error browsing project path: ${error}`);
        });
        break;
      case 'browseExportDirectory':
        this._settings.browseExportDirectory().catch((error) => {
          traceError(`[SidebarProvider] Error browsing export directory: ${error}`);
        });
        break;
      case 'openSourceControl':
        void vscode.commands.executeCommand('workbench.view.scm');
        break;
      case 'showProblems':
        void vscode.commands.executeCommand('workbench.actions.view.problems');
        break;
      case 'showInfo':
        void vscode.window.showInformationMessage(message.message);
        break;
      case 'webviewReady':
        traceMilestone('sidebar webview ready');
        break;
      case 'webviewDiagnostic': {
        const detail = message.detail ? `: ${message.detail}` : '';
        traceInfo(`[SidebarProvider][webview] ${message.phase}${detail}`);
        break;
      }
      case 'showError':
        void vscode.window.showErrorMessage(message.message);
        break;
      case 'selectionChanged':
        void this._actions.handleSelectionChanged(message);
        break;
      case 'reloadWindow':
        vscode.commands.executeCommand('workbench.action.reloadWindow');
        break;
      case 'getAtopileSettings':
        this._settings.sendAtopileSettings();
        break;
      case 'showLogs':
        backendServer.showLogs();
        break;
      case 'showBuildLogs':
        void vscode.commands.executeCommand('atopile.logViewer.focus');
        break;
      case 'showBackendMenu':
        void vscode.commands.executeCommand('atopile.showMenu');
        break;
      case 'openInSimpleBrowser':
        void vscode.commands.executeCommand('simpleBrowser.show', message.url);
        break;
      case 'revealInFinder':
        this._fileOps.revealInFinder(message.path);
        break;
      case 'renameFile':
        this._fileOps.renameFile(message.oldPath, message.newPath);
        break;
      case 'deleteFile':
        this._fileOps.deleteFile(message.path);
        break;
      case 'createFile':
        this._fileOps.createFile(message.path);
        break;
      case 'createFolder':
        this._fileOps.createFolder(message.path);
        break;
      case 'duplicateFile':
        this._fileOps.duplicateFile(message.sourcePath, message.destPath, message.newRelativePath);
        break;
      case 'openInTerminal':
        this._fileOps.openInTerminal(message.path);
        break;
      case 'listFiles':
        this._fileOps.listFiles(message.projectRoot, message.includeAll ?? true);
        break;
      case 'loadDirectory':
        this._fileOps.loadDirectory(message.projectRoot, message.directoryPath);
        break;
      case 'threeDModelBuildResult':
        this._actions.handleThreeDModelBuildResult(message.success, message.error);
        break;
      case 'openMigrateTab':
        traceInfo(`[SidebarProvider] Opening migrate tab for: ${message.projectRoot}`);
        openMigratePreview(this._extensionUri, message.projectRoot);
        break;
      default:
        traceInfo(`[SidebarProvider] Unknown message type: ${(message as { type?: string }).type}`);
    }
  }

  // ── HTML generation ────────────────────────────────────────────────

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

    const cacheVersion = (() => {
      try {
        return Math.floor(fs.statSync(jsPath).mtimeMs).toString();
      } catch {
        return Date.now().toString();
      }
    })();

    const withCacheBust = (uri: vscode.Uri): string =>
      `${uri.toString()}?v=${cacheVersion}`;

    const jsUri = withCacheBust(webview.asWebviewUri(vscode.Uri.file(jsPath)));
    // Base URI for relative imports in bundled JS (e.g., ./index-xxx.js)
    const baseUri = webview.asWebviewUri(vscode.Uri.file(webviewsDir + '/'));
    const cssUri = fs.existsSync(cssPath)
      ? withCacheBust(webview.asWebviewUri(vscode.Uri.file(cssPath)))
      : null;
    const baseCssUri = fs.existsSync(baseCssPath)
      ? withCacheBust(webview.asWebviewUri(vscode.Uri.file(baseCssPath)))
      : null;
    const iconUri = fs.existsSync(iconPath)
      ? webview.asWebviewUri(vscode.Uri.file(iconPath)).toString()
      : '';

    // WASM file for 3D viewer
    const wasmPath = path.join(webviewsDir, 'occt-import-js.wasm');
    const wasmUri = fs.existsSync(wasmPath)
      ? webview.asWebviewUri(vscode.Uri.file(wasmPath)).toString()
      : '';

    // Model-viewer script for GLB/GLTF 3D models
    const modelViewerPath = path.join(extensionPath, 'resources', 'model-viewer', 'model-viewer.min.js');
    const modelViewerUri = fs.existsSync(modelViewerPath)
      ? webview.asWebviewUri(vscode.Uri.file(modelViewerPath)).toString()
      : '';

    // Get backend URLs from backendServer (uses discovered port or config)
    const apiUrl = backendServer.apiUrl;
    const wsUrl = backendServer.wsUrl;
    const wsOrigin = getWsOrigin(wsUrl);
    const workspaceRoot = this._getWorkspaceRootSync();
    const isWebIde =
      vscode.env.uiKind === vscode.UIKind.Web ||
      process.env.WEB_IDE_MODE === '1' ||
      Boolean(process.env.OPENVSCODE_SERVER_ROOT);

    // Debug: log URLs being used
    traceInfo('SidebarProvider: Generating HTML with apiUrl:', apiUrl, 'wsUrl:', wsUrl);

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
    connect-src ${webview.cspSource} ${apiUrl} ${wsOrigin} ws: wss: blob:;
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
    window.__ATOPILE_WASM_URL__ = '${wasmUri}';
    window.__ATOPILE_MODEL_VIEWER_URL__ = '${modelViewerUri}';
    window.__ATOPILE_IS_WEB_IDE__ = ${isWebIde ? 'true' : 'false'};
    // Inject workspace root for the React app
    window.__ATOPILE_WORKSPACE_ROOT__ = ${JSON.stringify(workspaceRoot || '')};

    ${generateBridgeRuntime({ apiUrl, diagnostics: true, fetchMode: 'global' })}

    document.addEventListener('DOMContentLoaded', function() {
      var loading = document.getElementById('atopile-loading');
      var root = document.getElementById('root');
      function showFailure(message) {
        if (!loading) return;
        loading.textContent = message;
        if (window.__ATOPILE_POST_DIAG__) {
          window.__ATOPILE_POST_DIAG__('loading-failure', message);
        }
      }
      function maybeHideLoading() {
        if (!loading || !root) return;
        if (root.childNodes.length > 0) {
          loading.style.display = 'none';
        }
      }
      window.addEventListener('error', function(event) {
        if (event && event.message) {
          showFailure('atopile UI failed to load: ' + event.message);
        } else {
          showFailure('atopile UI failed to load.');
        }
      });
      if (root && typeof MutationObserver !== 'undefined') {
        var observer = new MutationObserver(maybeHideLoading);
        observer.observe(root, { childList: true, subtree: true });
      }
      setTimeout(function() {
        if (root && root.childNodes.length === 0) {
          showFailure('atopile UI failed to initialize. If you are on Firefox, disable strict tracking protection for this site or try Chromium.');
        }
      }, 7000);
    });
  </script>
</head>
<body>
  <div id="atopile-loading" style="padding: 8px; font-size: 12px; opacity: 0.8;">Loading atopile...</div>
  <div id="root"></div>
  <script nonce="${nonce}">
    (function() {
      var postDiag = window.__ATOPILE_POST_DIAG__;
      if (typeof postDiag === 'function') postDiag('module-script-insert');
      var script = document.createElement('script');
      script.type = 'module';
      script.src = '${jsUri}';
      script.onload = function() {
        if (typeof postDiag === 'function') postDiag('module-script-loaded');
      };
      script.onerror = function() {
        if (typeof postDiag === 'function') postDiag('module-script-error');
      };
      document.body.appendChild(script);
      setTimeout(function() {
        var root = document.getElementById('root');
        if (root && root.childNodes.length === 0 && typeof postDiag === 'function') {
          postDiag('module-timeout-no-root-content');
        }
      }, 8000);
    })();
  </script>
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
