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
import { setProjectRoot, setSelectedTargets } from '../common/target';
import { loadBuilds, getBuilds } from '../common/manifest';
import { openKiCanvasPreview } from '../ui/kicanvas';
import { openModelViewerPreview } from '../ui/modelviewer';
import { getAtopileWorkspaceFolders } from '../common/vscodeapi';

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

interface ReloadWindowMessage {
  type: 'reloadWindow';
}

interface RestartExtensionMessage {
  type: 'restartExtension';
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

type WebviewMessage =
  | OpenSignalsMessage
  | ConnectionStatusMessage
  | AtopileSettingsMessage
  | SelectionChangedMessage
  | BrowseAtopilePathMessage
  | BrowseProjectPathMessage
  | ReloadWindowMessage
  | RestartExtensionMessage
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
  | LoadDirectoryMessage;

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
  private _lastAtopileSettingsKey: string | null = null;
  private _fileWatcher?: vscode.FileSystemWatcher;
  private _watchedProjectRoot: string | null = null;
  private _fileChangeDebounce: NodeJS.Timeout | null = null;

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
    this._disposeFileWatcher();
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
          vscode.Uri.file(path.join(extensionPath, 'resources', 'model-viewer')),
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
      case 'selectionChanged':
        void this._handleSelectionChanged(message);
        break;
      case 'reloadWindow':
        // Reload the VS Code window to apply new atopile settings
        vscode.commands.executeCommand('workbench.action.reloadWindow');
        break;
      case 'restartExtension':
        // Restart the extension host to apply new atopile settings
        vscode.commands.executeCommand('workbench.action.restartExtensionHost');
        break;
      case 'showLogs':
        backendServer.showLogs();
        break;
      case 'showBuildLogs':
        void vscode.commands.executeCommand('atopile.logViewer.focus');
        break;
      case 'showBackendMenu':
        void vscode.commands.executeCommand('atopile.backendStatus');
        break;
      case 'showBackendMenu':
        void vscode.commands.executeCommand('atopile.backendStatus');
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
      default:
        traceInfo(`[SidebarProvider] Unknown message type: ${(message as Record<string, unknown>).type}`);
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
   * Handle request to browse for a local atopile path.
   * Shows a native folder picker dialog and sends the selected path back to the webview.
   */
  private async _handleBrowseAtopilePath(): Promise<void> {
    traceInfo('[SidebarProvider] Browsing for local atopile path');

    const result = await vscode.window.showOpenDialog({
      canSelectFiles: true,
      canSelectFolders: true,
      canSelectMany: false,
      openLabel: 'Select atopile installation',
      title: 'Select atopile installation directory or binary',
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
      // Only manage atopile.ato setting - never touch atopile.from
      // When local mode is on with a path, set ato; otherwise clear it
      if (atopile.source === 'local' && atopile.localPath) {
        traceInfo(`[SidebarProvider] Setting atopile.ato = ${atopile.localPath}`);
        await config.update('ato', atopile.localPath, target);
      } else {
        // Clear ato setting to fall back to extension-managed uv
        traceInfo(`[SidebarProvider] Clearing atopile.ato (using uv fallback)`);
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
   * Restart the atopile backend server without reloading the entire VS Code window.
   * This applies new atopile settings by restarting just the backend process.
   */
  private async _handleRestartExtension(): Promise<void> {
    traceInfo('[SidebarProvider] Restarting atopile backend...');

    // Restart the backend server - this will pick up new settings
    const success = await backendServer.restartServer();

    if (success) {
      traceInfo('[SidebarProvider] Backend restarted successfully');
      // The webview will reconnect automatically via WebSocket
    } else {
      traceError('[SidebarProvider] Failed to restart backend');
      // Notify the webview of the error
      backendServer.sendToWebview({
        type: 'atopileInstallError',
        error: 'Failed to restart atopile backend. Try reloading the window.',
      });
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
    const workspaceRoot = this._getWorkspaceRootSync();

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
    img-src https: http: data:;
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
    connect-src ${webview.cspSource} ${apiUrl} ${wsOrigin} blob:;
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
