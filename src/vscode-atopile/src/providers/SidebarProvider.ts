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
 * - settings-handlers.ts: atopile settings sync + browse dialogs
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { backendServer } from '../common/backendServer';
import { traceInfo, traceError, traceVerbose, traceMilestone } from '../common/log/logging';
import { createWebviewOptions, getNonce, getWsOrigin } from '../common/webview';
import { WebviewProxyBridge } from '../common/webview-bridge';
import {
  getWebviewBridgeRuntimePath,
  serializeWebviewBridgeConfig,
  WEBVIEW_BRIDGE_CONFIG_ELEMENT_ID,
} from '../common/webview-bridge-runtime';
import { renderTemplate, serializeJsonForHtml } from '../common/template';
import { getAtopileWorkspaceFolders } from '../common/vscodeapi';
import { openMigratePreview } from '../ui/migrate';
import type { WebviewMessage } from './sidebar/types';
import { SidebarFileWatcher } from './sidebar/file-watcher';
import { SidebarFileOperations } from './sidebar/file-operations';
import { SidebarActionHandlers } from './sidebar/action-handlers';
import { SidebarSettingsHandlers } from './sidebar/settings-handlers';
import { isWebIdeUi } from '../common/environment';
// @ts-ignore
import * as _sidebarTemplateText from './sidebar.hbs';
// @ts-ignore
import * as _notBuiltTemplateText from './webview-not-built.hbs';

const sidebarTemplateText: string = (_sidebarTemplateText as any).default || _sidebarTemplateText;
const notBuiltTemplateText: string = (_notBuiltTemplateText as any).default || _notBuiltTemplateText;

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
          traceInfo('[SidebarProvider] atopile settings changed, notifying webview');
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
      case 'browseExplorerDirectory':
        this._settings.browseExplorerDirectory(message.currentPath).catch((error) => {
          traceError(`[SidebarProvider] Error browsing explorer directory: ${error}`);
        });
        break;
      case 'projectCreated':
        void this._handleProjectCreated(message.projectRoot);
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

  private _isInCurrentWorkspace(folderPath: string): boolean {
    const workspaces = vscode.workspace.workspaceFolders ?? [];
    for (const workspaceFolder of workspaces) {
      const relative = path.relative(workspaceFolder.uri.fsPath, folderPath);
      if (relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative))) {
        return true;
      }
    }
    return false;
  }

  private async _handleProjectCreated(projectRoot: string): Promise<void> {
    if (!projectRoot) {
      return;
    }

    const containingFolder = path.dirname(projectRoot);
    if (this._isInCurrentWorkspace(containingFolder)) {
      return;
    }

    const choice = await vscode.window.showInformationMessage(
      `Project created at ${projectRoot}. Open the containing folder?`,
      { modal: true },
      'Open Folder',
    );

    if (choice === 'Open Folder') {
      await vscode.commands.executeCommand('vscode.openFolder', vscode.Uri.file(containingFolder), {
        forceNewWindow: false,
      });
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

    const jsUri = webview.asWebviewUri(vscode.Uri.file(jsPath));
    const bridgeRuntimeUri = webview.asWebviewUri(
      vscode.Uri.file(getWebviewBridgeRuntimePath(extensionPath))
    );
    // Base URI for relative imports in bundled JS (e.g., ./index-xxx.js)
    const baseUri = webview.asWebviewUri(vscode.Uri.file(webviewsDir + '/'));
    const cssUri = fs.existsSync(cssPath)
      ? webview.asWebviewUri(vscode.Uri.file(cssPath))
      : null;
    const baseCssUri = fs.existsSync(baseCssPath)
      ? webview.asWebviewUri(vscode.Uri.file(baseCssPath))
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
    const enableChat = vscode.workspace.getConfiguration('atopile').get<boolean>('enableChat', false);
    const isWebIde = isWebIdeUi();
    const bridgeConfigJson = serializeWebviewBridgeConfig({
      apiUrl,
      fetchMode: 'override',
    });

    traceInfo('SidebarProvider: Generating HTML with apiUrl:', apiUrl, 'wsUrl:', wsUrl);

    const csp = [
      "default-src 'none'",
      `style-src ${webview.cspSource} 'unsafe-inline'`,
      `script-src ${webview.cspSource} 'nonce-${nonce}' 'wasm-unsafe-eval' 'unsafe-eval'`,
      `font-src ${webview.cspSource}`,
      `img-src ${webview.cspSource} data: https: http:`,
      `connect-src ${webview.cspSource} ${apiUrl} ${wsOrigin} ws: wss: blob:`,
    ].join('; ');

    return renderTemplate(sidebarTemplateText, {
      baseUri: baseUri.toString(),
      csp,
      nonce,
      baseCssLink: baseCssUri ? `<link rel="stylesheet" href="${baseCssUri}">` : '',
      cssLink: cssUri ? `<link rel="stylesheet" href="${cssUri}">` : '',
      apiUrlJson: serializeJsonForHtml(apiUrl),
      wsOriginJson: serializeJsonForHtml(wsOrigin),
      iconUriJson: serializeJsonForHtml(iconUri),
      extensionVersionJson: serializeJsonForHtml(this._extensionVersion),
      wasmUriJson: serializeJsonForHtml(wasmUri),
      modelViewerUriJson: serializeJsonForHtml(modelViewerUri),
      enableChatLiteral: enableChat ? 'true' : 'false',
      isWebIdeLiteral: isWebIde ? 'true' : 'false',
      workspaceRootJson: serializeJsonForHtml(workspaceRoot || ''),
      bridgeConfigElementId: WEBVIEW_BRIDGE_CONFIG_ELEMENT_ID,
      bridgeConfigJson,
      bridgeRuntimeUri: bridgeRuntimeUri.toString(),
      jsUri: jsUri.toString(),
    });
  }

  private _getNotBuiltHtml(): string {
    return renderTemplate(notBuiltTemplateText, {
      buildCommand: 'npm run build',
    });
  }
}
