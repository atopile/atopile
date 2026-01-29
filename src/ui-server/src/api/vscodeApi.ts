/**
 * VS Code webview API wrapper.
 *
 * Provides access to the VS Code webview API for posting messages
 * back to the extension. Falls back gracefully when not in a VS Code webview.
 */

// Type declaration for VS Code's acquireVsCodeApi
interface VsCodeApi {
  postMessage(message: unknown): void;
  getState(): unknown;
  setState(state: unknown): void;
}

declare function acquireVsCodeApi(): VsCodeApi;

let vscodeApi: VsCodeApi | null = null;

/**
 * Get the VS Code API instance.
 * Returns null if not running inside a VS Code webview.
 */
export function getVsCodeApi(): VsCodeApi | null {
  if (!vscodeApi && typeof acquireVsCodeApi === 'function') {
    try {
      vscodeApi = acquireVsCodeApi();
    } catch {
      // Not in a VS Code webview context
      vscodeApi = null;
    }
  }
  return vscodeApi;
}

/**
 * Check if we're running inside a VS Code webview.
 */
export function isVsCodeWebview(): boolean {
  return getVsCodeApi() !== null;
}

/**
 * Post a message to the VS Code extension.
 * No-op if not running inside a VS Code webview.
 */
export function postToExtension(message: unknown): void {
  const api = getVsCodeApi();
  if (api) {
    api.postMessage(message);
  }
}

// Message types sent to extension
export interface OpenSignalsMessage {
  type: 'openSignals';
  openFile?: string | null;
  openFileLine?: number | null;
  openFileColumn?: number | null;
  openLayout?: string | null;
  openKicad?: string | null;
  open3d?: string | null;
}

export interface ConnectionStatusMessage {
  type: 'connectionStatus';
  isConnected: boolean;
}

export interface AtopileSettingsMessage {
  type: 'atopileSettings';
  atopile: {
    source?: string;
    localPath?: string | null;
  };
}

export interface SelectionChangedMessage {
  type: 'selectionChanged';
  projectRoot: string | null;
  targetNames: string[];
}

export interface BrowseAtopilePathMessage {
  type: 'browseAtopilePath';
}

export interface ReloadWindowMessage {
  type: 'reloadWindow';
}

export interface RestartExtensionMessage {
  type: 'restartExtension';
}

export interface ShowLogsMessage {
  type: 'showLogs';
}

export interface ShowBackendMenuMessage {
  type: 'showBackendMenu';
}

export interface OpenInSimpleBrowserMessage {
  type: 'openInSimpleBrowser';
  url: string;
}

export type ExtensionMessage =
  | OpenSignalsMessage
  | ConnectionStatusMessage
  | AtopileSettingsMessage
  | SelectionChangedMessage
  | BrowseAtopilePathMessage
  | ReloadWindowMessage
  | RestartExtensionMessage
  | ShowLogsMessage
  | ShowBackendMenuMessage
  | OpenInSimpleBrowserMessage;

/**
 * Type-safe helper to post messages to the extension.
 */
export function postMessage(message: ExtensionMessage): void {
  postToExtension(message);
}

// Message types received FROM the extension
export interface TriggerBuildMessage {
  type: 'triggerBuild';
  projectRoot: string;
  targets: string[];
  requestId?: string;  // For tracking responses
}

export interface SetAtopileInstallingMessage {
  type: 'setAtopileInstalling';
  installing: boolean;
  error?: string | null;
}

export interface ActiveFileMessage {
  type: 'activeFile';
  filePath: string | null;
}

export interface BrowseAtopilePathResultMessage {
  type: 'browseAtopilePathResult';
  path: string | null;
}

export interface AtopileInstallingMessage {
  type: 'atopileInstalling';
  message?: string;
  source?: string;
  version?: string;
  branch?: string;
}

export interface AtopileInstallErrorMessage {
  type: 'atopileInstallError';
  error?: string;
}

export interface ServerReadyMessage {
  type: 'serverReady';
  port: number;
}

export type ExtensionToWebviewMessage =
  | TriggerBuildMessage
  | SetAtopileInstallingMessage
  | ActiveFileMessage
  | BrowseAtopilePathResultMessage
  | AtopileInstallingMessage
  | AtopileInstallErrorMessage
  | ServerReadyMessage;

// Callback type for extension message handlers
type ExtensionMessageHandler = (message: ExtensionToWebviewMessage) => void;

let extensionMessageHandlers: ExtensionMessageHandler[] = [];

/**
 * Register a handler for messages from the extension.
 */
export function onExtensionMessage(handler: ExtensionMessageHandler): () => void {
  extensionMessageHandlers.push(handler);
  return () => {
    extensionMessageHandlers = extensionMessageHandlers.filter(h => h !== handler);
  };
}

/**
 * Initialize listener for messages from the VS Code extension.
 * Call this once at app startup.
 */
export function initExtensionMessageListener(): void {
  if (typeof window === 'undefined') return;

  window.addEventListener('message', (event) => {
    const message = event.data;
    if (!message || typeof message !== 'object') return;

    // Handle messages from extension (triggerBuild, atopileInstalling, etc.)
    if (
      message.type === 'triggerBuild' ||
      message.type === 'atopileInstalling' ||
      message.type === 'atopileInstallError' ||
      message.type === 'activeFile' ||
      message.type === 'browseAtopilePathResult' ||
      message.type === 'serverReady'
    ) {
      for (const handler of extensionMessageHandlers) {
        handler(message as ExtensionToWebviewMessage);
      }
    }
  });
}
