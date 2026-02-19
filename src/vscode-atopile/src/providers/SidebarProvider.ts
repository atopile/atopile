/**
 * Stateless Sidebar Webview Provider.
 *
 * This provider is minimal - it just opens the webview and loads the UI.
 * All state management and backend communication happens in the React app.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { backendServer } from '../common/backendServer';
import { traceInfo, traceError, traceVerbose, traceMilestone } from '../common/log/logging';
import { getWorkspaceSettings } from '../common/settings';
import { getProjectRoot } from '../common/utilities';
import { openPcb } from '../common/kicad';
import { prepareThreeDViewer, handleThreeDModelBuildResult } from '../common/3dmodel';
import { isModelViewerOpen, openModelViewerPreview } from '../ui/modelviewer';
import { getBuildTarget, setProjectRoot, setSelectedTargets } from '../common/target';
import { type Build, loadBuilds, getBuilds } from '../common/manifest';
import { createWebviewOptions, getNonce, getWsOrigin } from '../common/webview';
import { openLayoutEditor } from '../ui/layout-editor';
import { openMigratePreview } from '../ui/migrate';
import { getAtopileWorkspaceFolders } from '../common/vscodeapi';
import { WebSocket as NodeWebSocket } from 'ws';

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
    localPath?: string | null;
  };
}

interface FetchProxyRequest {
  type: 'fetchProxy';
  id: number;
  url: string;
  method: string;
  headers: Record<string, string>;
  body: string | null;
}

// WebSocket proxy: bridges webview WebSocket connections through the extension host.
// In OpenVSCode Server, webviews are served from HTTPS CDN which blocks
// ws:// connections to the local backend (Mixed Content).
interface WsProxyConnect {
  type: 'wsProxyConnect';
  id: number;
  url: string;
}
interface WsProxySend {
  type: 'wsProxySend';
  id: number;
  data: string;
}
interface WsProxyClose {
  type: 'wsProxyClose';
  id: number;
  code?: number;
  reason?: string;
}

interface SelectionChangedMessage {
  type: 'selectionChanged';
  projectRoot: string | null;
  targetNames: string[];
}

interface BrowseAtopilePathMessage {
  type: 'browseAtopilePath';
}

interface BrowseProjectPathMessage {
  type: 'browseProjectPath';
}

interface BrowseExportDirectoryMessage {
  type: 'browseExportDirectory';
}

interface OpenSourceControlMessage {
  type: 'openSourceControl';
}

interface ShowProblemsMessage {
  type: 'showProblems';
}

interface ShowInfoMessage {
  type: 'showInfo';
  message: string;
}

interface ShowErrorMessage {
  type: 'showError';
  message: string;
}

interface ReloadWindowMessage {
  type: 'reloadWindow';
}

interface ShowLogsMessage {
  type: 'showLogs';
}

interface ShowBuildLogsMessage {
  type: 'showBuildLogs';
}

interface ShowBackendMenuMessage {
  type: 'showBackendMenu';
}

interface OpenInSimpleBrowserMessage {
  type: 'openInSimpleBrowser';
  url: string;
}

interface RevealInFinderMessage {
  type: 'revealInFinder';
  path: string;
}

interface RenameFileMessage {
  type: 'renameFile';
  oldPath: string;
  newPath: string;
}

interface DeleteFileMessage {
  type: 'deleteFile';
  path: string;
}

interface CreateFileMessage {
  type: 'createFile';
  path: string;
}

interface CreateFolderMessage {
  type: 'createFolder';
  path: string;
}

interface DuplicateFileMessage {
  type: 'duplicateFile';
  sourcePath: string;
  destPath: string;
  newRelativePath: string;
}

interface OpenInTerminalMessage {
  type: 'openInTerminal';
  path: string;
}

interface ListFilesMessage {
  type: 'listFiles';
  projectRoot: string;
  includeAll?: boolean;
}

interface LoadDirectoryMessage {
  type: 'loadDirectory';
  projectRoot: string;
  directoryPath: string;  // Relative path to directory
}

interface GetAtopileSettingsMessage {
  type: 'getAtopileSettings';
}

interface ThreeDModelBuildResultMessage {
  type: 'threeDModelBuildResult';
  success: boolean;
  error?: string | null;
}

interface WebviewReadyMessage {
  type: 'webviewReady';
}

interface WebviewDiagnosticMessage {
  type: 'webviewDiagnostic';
  phase: string;
  detail?: string;
}

interface OpenMigrateTabMessage {
  type: 'openMigrateTab';
  projectRoot: string;
}

type WebviewMessage =
  | OpenSignalsMessage
  | ConnectionStatusMessage
  | AtopileSettingsMessage
  | SelectionChangedMessage
  | BrowseAtopilePathMessage
  | BrowseProjectPathMessage
  | BrowseExportDirectoryMessage
  | OpenSourceControlMessage
  | ShowProblemsMessage
  | ShowInfoMessage
  | ShowErrorMessage
  | ReloadWindowMessage
  | ShowLogsMessage
  | ShowBuildLogsMessage
  | ShowBackendMenuMessage
  | OpenInSimpleBrowserMessage
  | RevealInFinderMessage
  | RenameFileMessage
  | DeleteFileMessage
  | CreateFileMessage
  | CreateFolderMessage
  | DuplicateFileMessage
  | OpenInTerminalMessage
  | ListFilesMessage
  | LoadDirectoryMessage
  | GetAtopileSettingsMessage
  | FetchProxyRequest
  | ThreeDModelBuildResultMessage
  | WebviewReadyMessage
  | WebviewDiagnosticMessage
  | OpenMigrateTabMessage
  | WsProxyConnect
  | WsProxySend
  | WsProxyClose;

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
  private _lastAtopileSettingsKey: string | null = null;
  private _wsProxies: Map<number, NodeWebSocket> = new Map();
  private _wsProxyRetryTimers: Map<number, NodeJS.Timeout> = new Map();
  private _fileWatcher?: vscode.FileSystemWatcher;
  private _watchedProjectRoot: string | null = null;
  private _fileChangeDebounce: NodeJS.Timeout | null = null;

  constructor(
    private readonly _extensionUri: vscode.Uri,
    private readonly _extensionVersion: string,
    private readonly _activationTime: number = Date.now()
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
    // Send updated atopile settings to webview when configuration changes
    this._disposables.push(
      vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration('atopile.ato') || e.affectsConfiguration('atopile.from')) {
          traceInfo('[SidebarProvider] Atopile settings changed, notifying webview');
          this._sendAtopileSettings();
        }
      })
    );
  }

  dispose(): void {
    for (const d of this._disposables) {
      d.dispose();
    }
    this._disposables = [];
    this._disposeFileWatcher();
    // Clean up all WebSocket proxy connections
    for (const ws of this._wsProxies.values()) {
      ws.removeAllListeners();
      ws.close();
    }
    this._wsProxies.clear();
    for (const timer of this._wsProxyRetryTimers.values()) {
      clearTimeout(timer);
    }
    this._wsProxyRetryTimers.clear();
  }

  private _disposeFileWatcher(): void {
    if (this._fileWatcher) {
      this._fileWatcher.dispose();
      this._fileWatcher = undefined;
    }
    if (this._fileChangeDebounce) {
      clearTimeout(this._fileChangeDebounce);
      this._fileChangeDebounce = null;
    }
  }

  /**
   * Set up a file watcher for the given project root.
   * Notifies the webview when files change so it can refresh.
   */
  private _setupFileWatcher(projectRoot: string): void {
    // Skip if already watching this project
    if (this._watchedProjectRoot === projectRoot && this._fileWatcher) {
      return;
    }

    // Dispose existing watcher
    this._disposeFileWatcher();
    this._watchedProjectRoot = projectRoot;

    // Watch all files in the project
    const pattern = new vscode.RelativePattern(projectRoot, '**/*');
    this._fileWatcher = vscode.workspace.createFileSystemWatcher(pattern);

    // Debounced notification to avoid flooding on bulk operations
    const notifyChange = (uri: vscode.Uri) => {
      // Ignore changes in .git directory
      const relativePath = uri.fsPath.substring(projectRoot.length);
      if (relativePath.includes('/.git/') || relativePath.includes('\\.git\\')) {
        return;
      }

      if (this._fileChangeDebounce) {
        clearTimeout(this._fileChangeDebounce);
      }
      this._fileChangeDebounce = setTimeout(() => {
        traceInfo(`[SidebarProvider] Files changed in ${projectRoot}`);
        this._view?.webview.postMessage({
          type: 'filesChanged',
          projectRoot,
        });
      }, 300); // 300ms debounce
    };

    this._fileWatcher.onDidCreate(notifyChange);
    this._fileWatcher.onDidDelete(notifyChange);
    this._fileWatcher.onDidChange(() => {
      // Don't notify on content changes, only create/delete/rename
      // Renames appear as delete + create, so they're covered
    });

    traceInfo(`[SidebarProvider] File watcher set up for ${projectRoot}`);
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

    this._refreshWebview();
    this._postWorkspaceRoot();
    this._postActiveFile(vscode.window.activeTextEditor);
    this._sendAtopileSettings();
  }

  /**
   * Get workspace folder path synchronously (for HTML generation).
   * Just returns the first workspace folder.
   */
  private _getWorkspaceRootSync(): string | null {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) return null;
    return folders[0].uri.fsPath;
  }

  /**
   * Get workspace folder path, preferring folders with atopile projects.
   */
  private async _getWorkspaceRoot(): Promise<string | null> {
    // Prefer workspace folders that contain atopile projects (ato.yaml)
    const atopileWorkspaces = await getAtopileWorkspaceFolders();
    if (atopileWorkspaces.length > 0) {
      return atopileWorkspaces[0].uri.fsPath;
    }

    // Fall back to first workspace folder
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
      traceVerbose('[SidebarProvider] Cannot post message - no view');
      return;
    }
    this._view.webview.postMessage(message);
  }

  /**
   * Send current atopile settings to the webview.
   * Used to initialize the toggle state correctly.
   */
  private async _sendAtopileSettings(): Promise<void> {
    try {
      const projectRoot = await getProjectRoot();
      const settings = await getWorkspaceSettings(projectRoot);
      traceInfo(`[SidebarProvider] Sending atopile settings: ato=${settings.ato}, from=${settings.from}`);
      this._postToWebview({
        type: 'atopileSettingsResponse',
        settings: {
          atoPath: settings.ato || null,
          fromSpec: settings.from || null,
        },
      });
    } catch (error) {
      traceError(`[SidebarProvider] Error getting atopile settings: ${error}`);
      this._postToWebview({
        type: 'atopileSettingsResponse',
        settings: {
          atoPath: null,
          fromSpec: null,
        },
      });
    }
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
        // Handle async - fire and forget but log errors
        this._handleAtopileSettings(message.atopile).catch((error) => {
          traceError(`[SidebarProvider] Error handling atopile settings: ${error}`);
        });
        break;
      case 'browseAtopilePath':
        this._handleBrowseAtopilePath().catch((error) => {
          traceError(`[SidebarProvider] Error browsing atopile path: ${error}`);
        });
        break;
      case 'browseProjectPath':
        this._handleBrowseProjectPath().catch((error) => {
          traceError(`[SidebarProvider] Error browsing project path: ${error}`);
        });
        break;
      case 'browseExportDirectory':
        this._handleBrowseExportDirectory().catch((error) => {
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
      case 'webviewReady': {
        traceMilestone('sidebar webview ready');
        break;
      }
      case 'webviewDiagnostic': {
        const detail = message.detail ? `: ${message.detail}` : '';
        traceInfo(`[SidebarProvider][webview] ${message.phase}${detail}`);
        break;
      }
      case 'showError':
        void vscode.window.showErrorMessage(message.message);
        break;
      case 'selectionChanged':
        void this._handleSelectionChanged(message);
        break;
      case 'reloadWindow':
        // Reload the VS Code window to apply new atopile settings
        vscode.commands.executeCommand('workbench.action.reloadWindow');
        break;
      case 'getAtopileSettings':
        // Send current atopile settings to the webview
        this._sendAtopileSettings();
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
        // Reveal file in OS file explorer (Finder on Mac, Explorer on Windows)
        void vscode.commands.executeCommand('revealFileInOS', vscode.Uri.file(message.path));
        break;
      case 'renameFile':
        // Rename file using workspace.fs
        {
          const oldUri = vscode.Uri.file(message.oldPath);
          const newUri = vscode.Uri.file(message.newPath);
          vscode.workspace.fs.rename(oldUri, newUri).then(
            () => {
              traceInfo(`[SidebarProvider] Renamed ${message.oldPath} to ${message.newPath}`);
            },
            (err) => {
              traceError(`[SidebarProvider] Failed to rename file: ${err}`);
              vscode.window.showErrorMessage(`Failed to rename: ${err.message || err}`);
            }
          );
        }
        break;
      case 'deleteFile':
        // Delete file with confirmation
        {
          const deleteUri = vscode.Uri.file(message.path);
          const fileName = path.basename(message.path);
          vscode.window.showWarningMessage(
            `Are you sure you want to delete "${fileName}"?`,
            { modal: true },
            'Delete'
          ).then((choice) => {
            if (choice === 'Delete') {
              vscode.workspace.fs.delete(deleteUri, { recursive: true, useTrash: true }).then(
                () => {
                  traceInfo(`[SidebarProvider] Deleted ${message.path}`);
                },
                (err) => {
                  traceError(`[SidebarProvider] Failed to delete file: ${err}`);
                  vscode.window.showErrorMessage(`Failed to delete: ${err.message || err}`);
                }
              );
            }
          });
        }
        break;
      case 'createFile':
        // Create new file - open input box for name
        {
          vscode.window.showInputBox({
            prompt: 'Enter the file name',
            placeHolder: 'filename.ato',
            validateInput: (value) => {
              if (!value || !value.trim()) {
                return 'File name cannot be empty';
              }
              if (value.includes('/') || value.includes('\\')) {
                return 'File name cannot contain path separators';
              }
              return null;
            }
          }).then((fileName) => {
            if (fileName) {
              const newFilePath = path.join(message.path, fileName);
              const newUri = vscode.Uri.file(newFilePath);
              vscode.workspace.fs.writeFile(newUri, new Uint8Array()).then(
                () => {
                  traceInfo(`[SidebarProvider] Created file ${newFilePath}`);
                  // Open the new file
                  vscode.workspace.openTextDocument(newUri).then((doc) => {
                    vscode.window.showTextDocument(doc);
                  });
                },
                (err) => {
                  traceError(`[SidebarProvider] Failed to create file: ${err}`);
                  vscode.window.showErrorMessage(`Failed to create file: ${err.message || err}`);
                }
              );
            }
          });
        }
        break;
      case 'createFolder':
        // Create new folder - open input box for name
        {
          vscode.window.showInputBox({
            prompt: 'Enter the folder name',
            placeHolder: 'new-folder',
            validateInput: (value) => {
              if (!value || !value.trim()) {
                return 'Folder name cannot be empty';
              }
              if (value.includes('/') || value.includes('\\')) {
                return 'Folder name cannot contain path separators';
              }
              return null;
            }
          }).then((folderName) => {
            if (folderName) {
              const newFolderPath = path.join(message.path, folderName);
              const newUri = vscode.Uri.file(newFolderPath);
              vscode.workspace.fs.createDirectory(newUri).then(
                () => {
                  traceInfo(`[SidebarProvider] Created folder ${newFolderPath}`);
                },
                (err) => {
                  traceError(`[SidebarProvider] Failed to create folder: ${err}`);
                  vscode.window.showErrorMessage(`Failed to create folder: ${err.message || err}`);
                }
              );
            }
          });
        }
        break;
      case 'duplicateFile':
        // Duplicate a file or folder
        {
          const sourceUri = vscode.Uri.file(message.sourcePath);
          const destUri = vscode.Uri.file(message.destPath);
          vscode.workspace.fs.copy(sourceUri, destUri, { overwrite: false }).then(
            () => {
              traceInfo(`[SidebarProvider] Duplicated ${message.sourcePath} to ${message.destPath}`);
              // Notify webview to start rename mode on the new file
              this._view?.webview.postMessage({
                type: 'fileDuplicated',
                newRelativePath: message.newRelativePath,
              });
            },
            (err) => {
              traceError(`[SidebarProvider] Failed to duplicate: ${err}`);
              vscode.window.showErrorMessage(`Failed to duplicate: ${err.message || err}`);
            }
          );
        }
        break;
      case 'openInTerminal':
        // Open terminal at the specified path
        {
          const terminal = vscode.window.createTerminal({
            cwd: message.path,
            name: `Terminal: ${path.basename(message.path)}`,
          });
          terminal.show();
          traceInfo(`[SidebarProvider] Opened terminal at ${message.path}`);
        }
        break;
      case 'listFiles':
        // List files in a project directory
        this._handleListFiles(message.projectRoot, message.includeAll ?? true);
        break;
      case 'loadDirectory':
        // Load contents of a lazy-loaded directory
        this._handleLoadDirectory(message.projectRoot, message.directoryPath);
        break;
      case 'fetchProxy':
        // Proxy HTTP requests from the webview through the extension host.
        // In OpenVSCode Server, webviews are served from HTTPS CDN which blocks
        // HTTP fetch() to the local backend (Mixed Content).
        this._handleFetchProxy(message);
        break;
      case 'wsProxyConnect':
        this._handleWsProxyConnect(message as WsProxyConnect);
        break;
      case 'wsProxySend':
        this._handleWsProxySend(message as WsProxySend);
        break;
      case 'wsProxyClose':
        this._handleWsProxyClose(message as WsProxyClose);
        break;
      case 'threeDModelBuildResult':
        // Handle 3D model build result from webview
        traceInfo(`[SidebarProvider] Received threeDModelBuildResult: success=${message.success}, error="${message.error}"`);
        handleThreeDModelBuildResult(message.success, message.error);
        break;
      case 'openMigrateTab':
        traceInfo(`[SidebarProvider] Opening migrate tab for: ${message.projectRoot}`);
        openMigratePreview(this._extensionUri, message.projectRoot);
        break;
      default:
        traceInfo(`[SidebarProvider] Unknown message type: ${(message as Record<string, unknown>).type}`);
    }
  }

  private _handleFetchProxy(req: FetchProxyRequest): void {
    // Rewrite the URL to use the internal backend address.
    // The webview sends the browser-visible URL (e.g. https://host/proxy/8501/...),
    // but the extension host should always connect directly to the local backend.
    let url = req.url;
    try {
      const externalBase = backendServer.apiUrl;
      const internalBase = backendServer.internalApiUrl || externalBase;
      if (externalBase && internalBase && url.startsWith(externalBase)) {
        url = internalBase + url.slice(externalBase.length);
      }
    } catch {
      // Use URL as-is if rewriting fails
    }

    const init: Record<string, unknown> = {
      method: req.method,
      headers: req.headers,
    };
    if (req.body && req.method !== 'GET' && req.method !== 'HEAD') {
      init.body = req.body;
    }

    // Use Node.js native fetch (available since Node 18)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (globalThis as any).fetch(url, init)
      .then(async (response: { text: () => Promise<string>; status: number; statusText: string; headers: { forEach: (cb: (v: string, k: string) => void) => void } }) => {
        const body = await response.text();
        const headers: Record<string, string> = {};
        response.headers.forEach((value: string, key: string) => {
          headers[key] = value;
        });
        this._view?.webview.postMessage({
          type: 'fetchProxyResult',
          id: req.id,
          status: response.status,
          statusText: response.statusText,
          headers,
          body,
        });
      })
      .catch((err: Error) => {
        this._view?.webview.postMessage({
          type: 'fetchProxyResult',
          id: req.id,
          error: String(err),
        });
      });
  }

  // --- WebSocket proxy: bridge webview WS connections through the extension host ---

  private _handleWsProxyConnect(msg: WsProxyConnect): void {
    this._clearWsProxyRetry(msg.id);

    // Close any existing proxy with the same id
    const existing = this._wsProxies.get(msg.id);
    if (existing) {
      existing.removeAllListeners();
      existing.close();
      this._wsProxies.delete(msg.id);
    }

    // Rewrite the URL to use the internal backend address.
    // The webview sends the browser-visible URL (e.g. wss://host/ws/state),
    // but the extension host should always connect directly to the local backend.
    let targetUrl = msg.url;
    try {
      const parsed = new URL(msg.url);
      const internalBase = backendServer.internalApiUrl || backendServer.apiUrl;
      if (internalBase) {
        const internal = new URL(internalBase);
        const wsProtocol = internal.protocol === 'https:' ? 'wss:' : 'ws:';
        const port = internal.port ? `:${internal.port}` : '';
        targetUrl = `${wsProtocol}//${internal.hostname}${port}${parsed.pathname}${parsed.search}`;
      }
    } catch {
      // Use the URL as-is if parsing fails
    }

    this._connectWsProxy(msg.id, targetUrl, 0);
  }

  private _clearWsProxyRetry(id: number): void {
    const timer = this._wsProxyRetryTimers.get(id);
    if (timer) {
      clearTimeout(timer);
      this._wsProxyRetryTimers.delete(id);
    }
  }

  private _scheduleWsProxyRetry(id: number, targetUrl: string, attempt: number): void {
    this._clearWsProxyRetry(id);

    const delayMs = 500;
    traceInfo(`[WsProxy] Retrying id=${id} in ${delayMs}ms (attempt ${attempt})`);

    const timer = setTimeout(() => {
      this._wsProxyRetryTimers.delete(id);
      // Do not reconnect if this socket id has been replaced or explicitly closed.
      if (this._wsProxies.has(id)) {
        return;
      }
      this._connectWsProxy(id, targetUrl, attempt);
    }, delayMs);

    this._wsProxyRetryTimers.set(id, timer);
  }

  private _isTransientWsProxyError(err: Error): boolean {
    const message = (err.message || '').toUpperCase();
    return (
      message.includes('ECONNREFUSED') ||
      message.includes('ECONNRESET') ||
      message.includes('EHOSTUNREACH') ||
      message.includes('ETIMEDOUT')
    );
  }

  private _connectWsProxy(id: number, targetUrl: string, attempt: number): void {
    traceInfo(`[WsProxy] Connecting id=${id} to ${targetUrl}${attempt > 0 ? ` (attempt ${attempt})` : ''}`);
    const ws = new NodeWebSocket(targetUrl);
    this._wsProxies.set(id, ws);

    let suppressClose = false;

    ws.on('open', () => {
      this._clearWsProxyRetry(id);
      traceInfo(`[WsProxy] Connected id=${id}`);
      this._view?.webview.postMessage({ type: 'wsProxyOpen', id });
    });

    ws.on('message', (data: Buffer | string) => {
      const payload = typeof data === 'string' ? data : data.toString('utf-8');
      this._view?.webview.postMessage({ type: 'wsProxyMessage', id, data: payload });
    });

    ws.on('close', (code: number, reason: Buffer) => {
      this._wsProxies.delete(id);
      if (suppressClose) {
        return;
      }

      traceInfo(`[WsProxy] Closed id=${id} code=${code}`);
      this._view?.webview.postMessage({
        type: 'wsProxyClose',
        id,
        code,
        reason: reason.toString('utf-8'),
      });
    });

    ws.on('error', (err: Error) => {
      // During crash/restart there is a short window where serverState can still be
      // "running" while the WS is already down. Treat that as transient too.
      const backendNotReady = backendServer.serverState !== 'running' || !backendServer.isConnected;
      const shouldRetry =
        this._isTransientWsProxyError(err) &&
        backendNotReady &&
        attempt < 8;

      if (shouldRetry) {
        suppressClose = true;
        this._wsProxies.delete(id);
        traceInfo(`[WsProxy] Backend starting, delaying id=${id}: ${err.message}`);
        this._scheduleWsProxyRetry(id, targetUrl, attempt + 1);
        try {
          ws.removeAllListeners();
          ws.close();
        } catch {
          // Ignore close failures during transient reconnect handling.
        }
        return;
      }

      traceError(`[WsProxy] Error id=${id}: ${err.message}`);
      this._view?.webview.postMessage({ type: 'wsProxyError', id, error: err.message });
    });
  }

  private _handleWsProxySend(msg: WsProxySend): void {
    const ws = this._wsProxies.get(msg.id);
    if (ws?.readyState === NodeWebSocket.OPEN) {
      ws.send(msg.data);
    }
  }

  private _handleWsProxyClose(msg: WsProxyClose): void {
    this._clearWsProxyRetry(msg.id);
    const ws = this._wsProxies.get(msg.id);
    if (ws) {
      ws.close(msg.code ?? 1000, msg.reason ?? '');
      this._wsProxies.delete(msg.id);
    }
  }

  private async _handleSelectionChanged(message: SelectionChangedMessage): Promise<void> {
    const projectRoot = message.projectRoot ?? null;
    setProjectRoot(projectRoot ?? undefined);

    // Set up file watcher for the selected project
    if (projectRoot) {
      this._setupFileWatcher(projectRoot);
    } else {
      this._disposeFileWatcher();
      this._watchedProjectRoot = null;
    }

    await loadBuilds();
    const builds = getBuilds();
    const projectBuilds = projectRoot ? builds.filter((build) => build.root === projectRoot) : [];
    const selectedBuilds = message.targetNames.length
      ? projectBuilds.filter((build) => message.targetNames.includes(build.name))
      : [];
    setSelectedTargets(selectedBuilds);

    // If the 3D model viewer is open, prepare viewer for the new target
    if (isModelViewerOpen() && selectedBuilds.length > 0) {
      const build = selectedBuilds[0];
      if (build?.root && build?.name && build?.model_path) {
        traceInfo(`[SidebarProvider] 3D viewer open, preparing viewer for new target: ${build.name}`);

        prepareThreeDViewer(build.model_path, () => {
          backendServer.sendToWebview({
            type: 'triggerBuild',
            projectRoot: build.root,
            targets: [build.name],
            includeTargets: ['glb-only'],
            excludeTargets: ['default'],
          });
        });

        await openModelViewerPreview();
      }
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
      void this._open3dPreview(msg.open3d);
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

  private _openLayoutPreview(_filePath: string): void {
    // The server already loaded the PCB via the openLayout action.
    // Just open the editor webview.
    void openLayoutEditor();
  }

  private _openWithKicad(filePath: string): void {
    const pcbPath = this._resolveFilePath(filePath, '.kicad_pcb');
    if (!pcbPath) {
      traceError(`[SidebarProvider] KiCad layout file not found: ${filePath}`);
      vscode.window.showErrorMessage('KiCad layout file not found. Run a build to generate it.');
      return;
    }

    const isWebIde =
      vscode.env.uiKind === vscode.UIKind.Web ||
      process.env.WEB_IDE_MODE === '1' ||
      Boolean(process.env.OPENVSCODE_SERVER_ROOT);

    if (isWebIde) {
      // Browser web-ide cannot launch native KiCad.
      vscode.window.showInformationMessage('KiCad is unavailable in web-ide. Use the Layout action instead.');
    } else {
      // Desktop VS Code: spawn pcbnew directly
      void openPcb(pcbPath).catch((error) => {
        traceError(`[SidebarProvider] Failed to open KiCad: ${error}`);
        vscode.window.showErrorMessage(`Failed to open KiCad: ${error instanceof Error ? error.message : error}`);
      });
    }
  }

  private async _open3dPreview(filePath: string): Promise<void> {
    await loadBuilds();

    const modelPath = this._resolveFilePath(filePath, '.glb') ?? filePath;
    const build = this._resolveBuildFor3dModel(modelPath);
    if (!build?.root || !build.name) {
      traceError('[SidebarProvider] No build target selected for 3D export.');
      await openModelViewerPreview();
      return;
    }

    // Keep extension target selection aligned with actions triggered from the web UI.
    setSelectedTargets([build]);

    const glbPath = modelPath.toLowerCase().endsWith('.glb') ? modelPath : build.model_path;

    prepareThreeDViewer(glbPath, () => {
      backendServer.sendToWebview({
        type: 'triggerBuild',
        projectRoot: build.root,
        targets: [build.name],
        includeTargets: ['glb-only'],
        excludeTargets: ['default'],
      });
    });

    await openModelViewerPreview();
  }

  private _resolveBuildFor3dModel(modelPath: string): Build | undefined {
    const selected = getBuildTarget();
    if (selected?.root && selected.name) {
      return selected;
    }

    const resolvedModelPath = path.resolve(modelPath);
    const builds = getBuilds();

    const byExactModelPath = builds.find(
      (build) => path.resolve(build.model_path) === resolvedModelPath
    );
    if (byExactModelPath) {
      return byExactModelPath;
    }

    for (const build of builds) {
      const buildDir = path.resolve(build.root, 'build', 'builds', build.name) + path.sep;
      if (resolvedModelPath.startsWith(buildDir)) {
        return build;
      }
    }

    const marker = `${path.sep}build${path.sep}builds${path.sep}`;
    const markerIndex = resolvedModelPath.lastIndexOf(marker);
    if (markerIndex !== -1) {
      const inferredRoot = resolvedModelPath.slice(0, markerIndex);
      const remaining = resolvedModelPath.slice(markerIndex + marker.length);
      const [targetName] = remaining.split(path.sep);

      if (targetName) {
        const fromManifest = builds.find(
          (build) =>
            build.name === targetName &&
            path.resolve(build.root) === path.resolve(inferredRoot)
        );
        if (fromManifest) {
          return fromManifest;
        }

        traceInfo(`[SidebarProvider] Inferred 3D target from path: ${targetName}`);
        return {
          name: targetName,
          entry: '',
          pcb_path: '',
          model_path: path.join(
            inferredRoot,
            'build',
            'builds',
            targetName,
            `${targetName}.pcba.glb`
          ),
          root: inferredRoot,
        };
      }
    }

    return undefined;
  }

  /**
   * Handle listFiles request - enumerate files in a project directory.
   * File enumeration is handled entirely by the VS Code extension.
   * Hidden directories (starting with .) are shown but not recursed into (lazy loaded).
   */
  private async _handleListFiles(projectRoot: string, includeAll: boolean): Promise<void> {
    traceInfo(`[SidebarProvider] Listing files for: ${projectRoot}, includeAll: ${includeAll}`);

    // Directories to completely exclude (not even show)
    const excludedDirs = new Set([
      '__pycache__',
      'node_modules',
      '.pytest_cache',
      '.mypy_cache',
      'dist',
      'egg-info',
    ]);

    // Hidden directories to show but lazy load (don't recurse into by default)
    const lazyLoadDirs = new Set([
      '.git',
      '.venv',
      '.ato',
      'build',
      'venv',
    ]);

    interface FileNode {
      name: string;
      path: string;
      type: 'file' | 'folder';
      extension?: string;
      children?: FileNode[];
      lazyLoad?: boolean;  // True if directory contents not yet loaded
    }

    const buildFileTree = async (dirUri: vscode.Uri, basePath: string): Promise<FileNode[]> => {
      const nodes: FileNode[] = [];

      try {
        const entries = await vscode.workspace.fs.readDirectory(dirUri);

        // Sort: directories first, then alphabetically
        entries.sort((a, b) => {
          const aIsDir = a[1] === vscode.FileType.Directory;
          const bIsDir = b[1] === vscode.FileType.Directory;
          if (aIsDir !== bIsDir) return aIsDir ? -1 : 1;
          return a[0].toLowerCase().localeCompare(b[0].toLowerCase());
        });

        for (const [name, fileType] of entries) {
          // Skip completely excluded directories
          if (excludedDirs.has(name)) continue;
          if (name.endsWith('.egg-info')) continue;

          const relativePath = basePath ? `${basePath}/${name}` : name;
          const itemUri = vscode.Uri.joinPath(dirUri, name);
          const isHidden = name.startsWith('.');

          if (fileType === vscode.FileType.Directory) {
            // Check if this directory should be lazy loaded
            const shouldLazyLoad = lazyLoadDirs.has(name) || (isHidden && !includeAll);

            if (shouldLazyLoad) {
              // Show the directory but mark it for lazy loading
              nodes.push({
                name,
                path: relativePath,
                type: 'folder',
                children: [],  // Empty - will be loaded on demand
                lazyLoad: true,
              });
            } else {
              const children = await buildFileTree(itemUri, relativePath);
              // Skip empty directories unless includeAll
              if (children.length > 0 || includeAll) {
                nodes.push({
                  name,
                  path: relativePath,
                  type: 'folder',
                  children,
                });
              }
            }
          } else if (fileType === vscode.FileType.File) {
            // Skip hidden files unless includeAll
            if (isHidden && !includeAll) continue;

            // If not includeAll, only include .ato and .py files
            if (!includeAll) {
              const ext = name.split('.').pop()?.toLowerCase();
              if (ext !== 'ato' && ext !== 'py') continue;
            }

            const ext = name.includes('.') ? name.split('.').pop()?.toLowerCase() : undefined;
            nodes.push({
              name,
              path: relativePath,
              type: 'file',
              extension: ext,
            });
          }
        }
      } catch (err) {
        traceError(`[SidebarProvider] Error reading directory ${dirUri.fsPath}: ${err}`);
      }

      return nodes;
    };

    try {
      const rootUri = vscode.Uri.file(projectRoot);
      const files = await buildFileTree(rootUri, '');

      // Count total files (excluding lazy-loaded directories)
      const countFiles = (nodes: FileNode[]): number => {
        let count = 0;
        for (const node of nodes) {
          if (node.type === 'file') {
            count++;
          } else if (node.children && !node.lazyLoad) {
            count += countFiles(node.children);
          }
        }
        return count;
      };

      const total = countFiles(files);

      // Send result back to webview
      this._view?.webview.postMessage({
        type: 'filesListed',
        projectRoot,
        files,
        total,
      });

      traceInfo(`[SidebarProvider] Listed ${total} files for ${projectRoot}`);
    } catch (err) {
      traceError(`[SidebarProvider] Failed to list files: ${err}`);
      this._view?.webview.postMessage({
        type: 'filesListed',
        projectRoot,
        files: [],
        total: 0,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }

  /**
   * Handle loadDirectory request - load contents of a lazy-loaded directory.
   */
  private async _handleLoadDirectory(projectRoot: string, directoryPath: string): Promise<void> {
    traceInfo(`[SidebarProvider] Loading directory: ${directoryPath} in ${projectRoot}`);

    interface FileNode {
      name: string;
      path: string;
      type: 'file' | 'folder';
      extension?: string;
      children?: FileNode[];
      lazyLoad?: boolean;
    }

    try {
      const dirUri = vscode.Uri.file(path.join(projectRoot, directoryPath));
      const entries = await vscode.workspace.fs.readDirectory(dirUri);
      const nodes: FileNode[] = [];

      // Sort: directories first, then alphabetically
      entries.sort((a, b) => {
        const aIsDir = a[1] === vscode.FileType.Directory;
        const bIsDir = b[1] === vscode.FileType.Directory;
        if (aIsDir !== bIsDir) return aIsDir ? -1 : 1;
        return a[0].toLowerCase().localeCompare(b[0].toLowerCase());
      });

      for (const [name, fileType] of entries) {
        const relativePath = `${directoryPath}/${name}`;

        if (fileType === vscode.FileType.Directory) {
          // All directories inside a lazy-loaded parent are also lazy-loaded
          // This allows them to be expanded on demand
          nodes.push({
            name,
            path: relativePath,
            type: 'folder',
            children: [],
            lazyLoad: true,  // All nested dirs are lazy-loaded
          });
        } else if (fileType === vscode.FileType.File) {
          const ext = name.includes('.') ? name.split('.').pop()?.toLowerCase() : undefined;
          nodes.push({
            name,
            path: relativePath,
            type: 'file',
            extension: ext,
          });
        }
      }

      // Send result back to webview
      this._view?.webview.postMessage({
        type: 'directoryLoaded',
        projectRoot,
        directoryPath,
        children: nodes,
      });

      traceInfo(`[SidebarProvider] Loaded ${nodes.length} items in ${directoryPath}`);
    } catch (err) {
      traceError(`[SidebarProvider] Failed to load directory: ${err}`);
      this._view?.webview.postMessage({
        type: 'directoryLoaded',
        projectRoot,
        directoryPath,
        children: [],
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }

  /**
   * Handle request to browse for a local atopile binary.
   * Shows a native file picker dialog and sends the selected path back to the webview.
   */
  private async _handleBrowseAtopilePath(): Promise<void> {
    traceInfo('[SidebarProvider] Browsing for local atopile path');

    const result = await vscode.window.showOpenDialog({
      canSelectFiles: true,
      canSelectFolders: false,
      canSelectMany: false,
      openLabel: 'Select atopile binary',
      title: 'Select atopile binary',
      filters: process.platform === 'win32'
        ? { 'Executables': ['exe', 'cmd'], 'All files': ['*'] }
        : undefined,
    });

    const selectedPath = result?.[0]?.fsPath ?? null;
    traceInfo(`[SidebarProvider] Browse result: ${selectedPath}`);

    // Send the result back to the webview
    this._view?.webview.postMessage({
      type: 'browseAtopilePathResult',
      path: selectedPath,
    });
  }

  /**
   * Handle request to browse for a project directory.
   * Shows a native folder picker dialog and sends the selected path back to the webview.
   */
  private async _handleBrowseProjectPath(): Promise<void> {
    traceInfo('[SidebarProvider] Browsing for project directory');

    const defaultUri = vscode.workspace.workspaceFolders?.[0]?.uri;

    const result = await vscode.window.showOpenDialog({
      canSelectFiles: false,
      canSelectFolders: true,
      canSelectMany: false,
      defaultUri,
      openLabel: 'Select folder',
      title: 'Select project directory',
    });

    const selectedPath = result?.[0]?.fsPath ?? null;
    traceInfo(`[SidebarProvider] Browse project path result: ${selectedPath}`);

    // Send the result back to the webview
    this._view?.webview.postMessage({
      type: 'browseProjectPathResult',
      path: selectedPath,
    });
  }

  /**
   * Handle request to browse for an export directory.
   * Shows a native folder picker dialog and sends the selected path back to the webview.
   */
  private async _handleBrowseExportDirectory(): Promise<void> {
    traceInfo('[SidebarProvider] Browsing for export directory');

    const defaultUri = vscode.workspace.workspaceFolders?.[0]?.uri;

    const result = await vscode.window.showOpenDialog({
      canSelectFiles: false,
      canSelectFolders: true,
      canSelectMany: false,
      defaultUri,
      openLabel: 'Select export folder',
      title: 'Select export directory for manufacturing files',
    });

    const selectedPath = result?.[0]?.fsPath ?? null;
    traceInfo(`[SidebarProvider] Browse export directory result: ${selectedPath}`);

    // Send the result back to the webview
    this._view?.webview.postMessage({
      type: 'browseExportDirectoryResult',
      path: selectedPath,
    });
  }

  /**
   * Handle atopile settings changes from the UI.
   * Syncs atopile settings to VS Code configuration.
   * Note: Does NOT restart the server - user must click the restart button.
   */
  private async _handleAtopileSettings(atopile: AtopileSettingsMessage['atopile']): Promise<void> {
    if (!atopile) return;

    traceInfo(`[SidebarProvider] _handleAtopileSettings received: ${JSON.stringify(atopile)}`);

    // Build a key for comparison to avoid unnecessary updates
    const settingsKey = JSON.stringify({
      source: atopile.source,
      localPath: atopile.localPath,
    });

    // Skip if nothing changed - this is called on every state update
    if (settingsKey === this._lastAtopileSettingsKey) {
      traceInfo(`[SidebarProvider] Skipping - settings unchanged: ${settingsKey}`);
      return;
    }

    traceInfo(`[SidebarProvider] Processing new settings: ${settingsKey}`);
    this._lastAtopileSettingsKey = settingsKey;

    const config = vscode.workspace.getConfiguration('atopile');
    const hasWorkspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length > 0;
    const target = hasWorkspace ? vscode.ConfigurationTarget.Workspace : vscode.ConfigurationTarget.Global;

    try {
      // Only manage atopile.ato setting - atopile.from is only set manually in settings
      if (atopile.source === 'local' && atopile.localPath) {
        // Local mode: set ato path
        traceInfo(`[SidebarProvider] Setting atopile.ato = ${atopile.localPath}`);
        await config.update('ato', atopile.localPath, target);
      } else {
        // Release mode: clear ato setting so the default is used
        traceInfo(`[SidebarProvider] Clearing atopile.ato (using default)`);
        await config.update('ato', undefined, target);
      }
      traceInfo(`[SidebarProvider] Atopile settings saved. User must restart to apply.`);
    } catch (error) {
      traceError(`[SidebarProvider] Failed to update atopile settings: ${error}`);

      // Notify UI of the error
      backendServer.sendToWebview({
        type: 'atopileInstallError',
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  /**
   * Get the webview HTML - loads from compiled assets.
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

    // Fetch/WS proxy: route backend traffic through the extension host.
    // The webview often runs in a CDN iframe where direct localhost access
    // is blocked (Mixed Content / cross-origin). This bridge keeps comms local.
    (function() {
      var originalAcquire = window.acquireVsCodeApi;
      var vsCodeApi = null;
      if (typeof originalAcquire === 'function') {
        window.acquireVsCodeApi = function() {
          if (!vsCodeApi) vsCodeApi = originalAcquire();
          return vsCodeApi;
        };
      }

      function getVsCodeApi() {
        try {
          return vsCodeApi || (window.acquireVsCodeApi ? window.acquireVsCodeApi() : null);
        } catch (err) {
          console.error('[atopile webview] Failed to acquire VS Code API:', err);
          return null;
        }
      }

      function postWebviewDiagnostic(phase, detail) {
        var payload = {
          type: 'webviewDiagnostic',
          phase: String(phase || ''),
          detail: detail == null ? undefined : String(detail),
        };
        if (!window.__ATOPILE_DIAG_QUEUE__) {
          window.__ATOPILE_DIAG_QUEUE__ = [];
        }
        window.__ATOPILE_DIAG_QUEUE__.push(payload);
        var attempts = 0;
        var flush = function() {
          var api = getVsCodeApi();
          if (!api) {
            attempts += 1;
            if (attempts < 40) {
              setTimeout(flush, 250);
            }
            return;
          }
          while (window.__ATOPILE_DIAG_QUEUE__.length > 0) {
            var msg = window.__ATOPILE_DIAG_QUEUE__.shift();
            try {
              api.postMessage(msg);
            } catch (err) {
              console.error('[atopile webview] Failed to post diagnostic:', err);
              break;
            }
          }
        };
        try {
          flush();
        } catch (err) {
          console.error('[atopile webview] Diagnostic flush failed:', err);
        }
      }

      window.__ATOPILE_POST_DIAG__ = postWebviewDiagnostic;
      postWebviewDiagnostic('inline-bootstrap-start');
      window.addEventListener('error', function(event) {
        var msg = (event && event.message) ? event.message : 'unknown error';
        postWebviewDiagnostic('window-error', msg);
      });
      window.addEventListener('unhandledrejection', function(event) {
        var reason = event && event.reason;
        var msg = reason && reason.message ? reason.message : String(reason);
        postWebviewDiagnostic('unhandled-rejection', msg);
      });

      function normalizeHeaders(headers) {
        if (!headers) return {};
        if (typeof Headers !== 'undefined' && headers instanceof Headers) {
          var out = {};
          headers.forEach(function(v, k) { out[k] = v; });
          return out;
        }
        if (Array.isArray(headers)) {
          var outArray = {};
          for (var i = 0; i < headers.length; i++) {
            var entry = headers[i];
            if (Array.isArray(entry) && entry.length >= 2) {
              outArray[String(entry[0])] = String(entry[1]);
            }
          }
          return outArray;
        }
        return headers;
      }

      function createCompatEvent(type, init) {
        var evt;
        try {
          if (type === 'message' && typeof MessageEvent === 'function') {
            evt = new MessageEvent('message', { data: init && init.data });
          } else if (type === 'close' && typeof CloseEvent === 'function') {
            evt = new CloseEvent('close', {
              code: (init && init.code) || 1000,
              reason: (init && init.reason) || '',
              wasClean: true,
            });
          } else {
            evt = new Event(type);
          }
        } catch {
          evt = document.createEvent('Event');
          evt.initEvent(type, false, false);
        }
        if (init && init.data !== undefined && evt.data === undefined) evt.data = init.data;
        if (init && init.code !== undefined && evt.code === undefined) evt.code = init.code;
        if (init && init.reason !== undefined && evt.reason === undefined) evt.reason = init.reason;
        return evt;
      }

      function createProxySocket(url, id) {
        var listeners = { open: [], message: [], close: [], error: [] };
        var target = {
          _readyState: 0,
          url: url,
          onopen: null,
          onmessage: null,
          onclose: null,
          onerror: null,
          CONNECTING: 0,
          OPEN: 1,
          CLOSING: 2,
          CLOSED: 3,
          addEventListener: function(type, cb) {
            if (!listeners[type] || typeof cb !== 'function') return;
            listeners[type].push(cb);
          },
          removeEventListener: function(type, cb) {
            if (!listeners[type]) return;
            listeners[type] = listeners[type].filter(function(fn) { return fn !== cb; });
          },
          dispatchEvent: function(evt) {
            var type = evt && evt.type ? evt.type : '';
            var fns = listeners[type] || [];
            for (var i = 0; i < fns.length; i++) {
              try { fns[i](evt); } catch (err) { console.error(err); }
            }
            return true;
          },
          send: function(data) {
            var api = getVsCodeApi();
            if (api) api.postMessage({ type: 'wsProxySend', id: id, data: data });
          },
          close: function(code, reason) {
            target._readyState = 2;
            var api = getVsCodeApi();
            if (api) api.postMessage({ type: 'wsProxyClose', id: id, code: code, reason: reason });
          },
        };
        Object.defineProperty(target, 'readyState', {
          get: function() { return target._readyState; },
        });
        return target;
      }

      // Fetch proxy: expose as an explicit global so the React app can use it
      // directly. Overriding window.fetch is unreliable in VS Code webview iframes
      // (the framework may freeze or re-assign it after our script runs).
      var _fpId = 0;
      var _fpPending = new Map();

      window.addEventListener('message', function(event) {
        var msg = event.data;
        if (msg && msg.type === 'fetchProxyResult' && _fpPending.has(msg.id)) {
          var handler = _fpPending.get(msg.id);
          _fpPending.delete(msg.id);
          handler(msg);
        }
      });

      window.__ATOPILE_PROXY_FETCH__ = function(url, init) {
        var id = ++_fpId;
        return new Promise(function(resolve, reject) {
          var timeout = setTimeout(function() {
            _fpPending.delete(id);
            reject(new TypeError('Fetch proxy timeout'));
          }, 30000);

          _fpPending.set(id, function(msg) {
            clearTimeout(timeout);
            if (msg.error) {
              reject(new TypeError(msg.error));
            } else {
              resolve(new Response(msg.body, {
                status: msg.status || 200,
                statusText: msg.statusText || 'OK',
                headers: msg.headers || {},
              }));
            }
          });

          var api = getVsCodeApi();
          if (api) {
            api.postMessage({
              type: 'fetchProxy',
              id: id,
              url: url,
              method: (init && init.method) || 'GET',
              headers: normalizeHeaders(init && init.headers),
              body: (init && init.body) || null,
            });
          } else {
            clearTimeout(timeout);
            _fpPending.delete(id);
            reject(new TypeError('VS Code API not available for fetch proxy'));
          }
        });
      };

      var wsProxyId = 0;
      var wsProxyInstances = new Map();
      var NativeWebSocket = window.WebSocket;

      function resolveFallbackWsUrl(url) {
        try {
          var parsed = new URL(url, window.location.href);
          if (parsed.hostname !== 'localhost' && parsed.hostname !== '127.0.0.1') {
            return url;
          }

          var parentOrigin = '';
          try {
            var params = new URLSearchParams(window.location.search);
            parentOrigin = params.get('parentOrigin') || '';
            if (parentOrigin) parentOrigin = decodeURIComponent(parentOrigin);
          } catch {}

          if (!parentOrigin && document.referrer) {
            try {
              parentOrigin = new URL(document.referrer).origin;
            } catch {}
          }

          if (!parentOrigin) {
            return url;
          }

          var parent = new URL(parentOrigin);
          var wsProtocol = parent.protocol === 'https:' ? 'wss:' : 'ws:';
          return wsProtocol + '//' + parent.host + parsed.pathname + parsed.search;
        } catch {
          return url;
        }
      }

      window.addEventListener('message', function(event) {
        var msg = event.data;
        if (!msg || !msg.type) return;
        var instance = msg.id != null ? wsProxyInstances.get(msg.id) : null;
        if (!instance) return;
        switch (msg.type) {
          case 'wsProxyOpen': {
            instance._readyState = 1;
            var openEvt = createCompatEvent('open');
            if (instance.onopen) instance.onopen(openEvt);
            instance.dispatchEvent(openEvt);
            break;
          }
          case 'wsProxyMessage': {
            var msgEvt = createCompatEvent('message', { data: msg.data });
            if (instance.onmessage) instance.onmessage(msgEvt);
            instance.dispatchEvent(msgEvt);
            break;
          }
          case 'wsProxyClose': {
            instance._readyState = 3;
            var closeEvt = createCompatEvent('close', { code: msg.code || 1000, reason: msg.reason || '' });
            if (instance.onclose) instance.onclose(closeEvt);
            instance.dispatchEvent(closeEvt);
            wsProxyInstances.delete(msg.id);
            break;
          }
          case 'wsProxyError': {
            var errEvt = createCompatEvent('error');
            if (instance.onerror) instance.onerror(errEvt);
            instance.dispatchEvent(errEvt);
            break;
          }
        }
      });

      function ProxyWebSocket(url, protocols) {
        var api = getVsCodeApi();
        if (!api && typeof NativeWebSocket === 'function') {
          var fallbackUrl = resolveFallbackWsUrl(url);
          return protocols !== undefined
            ? new NativeWebSocket(fallbackUrl, protocols)
            : new NativeWebSocket(fallbackUrl);
        }

        var id = ++wsProxyId;
        var target = createProxySocket(url, id);
        wsProxyInstances.set(id, target);
        if (api) {
          try {
            api.postMessage({ type: 'wsProxyConnect', id: id, url: url });
          } catch {
            wsProxyInstances.delete(id);
            if (typeof NativeWebSocket === 'function') {
              var fallbackUrl = resolveFallbackWsUrl(url);
              return protocols !== undefined
                ? new NativeWebSocket(fallbackUrl, protocols)
                : new NativeWebSocket(fallbackUrl);
            }
          }
        }
        return target;
      }
      ProxyWebSocket.CONNECTING = 0;
      ProxyWebSocket.OPEN = 1;
      ProxyWebSocket.CLOSING = 2;
      ProxyWebSocket.CLOSED = 3;
      window.WebSocket = ProxyWebSocket;
    })();

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
