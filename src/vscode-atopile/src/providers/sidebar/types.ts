/**
 * Message type interfaces for SidebarProvider webview communication.
 */

import type { FetchProxyRequest, WsProxyConnect, WsProxySend, WsProxyClose } from '../../common/webview-bridge';

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

export interface BrowseProjectPathMessage {
  type: 'browseProjectPath';
}

export interface BrowseExportDirectoryMessage {
  type: 'browseExportDirectory';
}

export interface OpenSourceControlMessage {
  type: 'openSourceControl';
}

export interface ShowProblemsMessage {
  type: 'showProblems';
}

export interface ShowInfoMessage {
  type: 'showInfo';
  message: string;
}

export interface ShowErrorMessage {
  type: 'showError';
  message: string;
}

export interface ReloadWindowMessage {
  type: 'reloadWindow';
}

export interface ShowLogsMessage {
  type: 'showLogs';
}

export interface ShowBuildLogsMessage {
  type: 'showBuildLogs';
}

export interface ShowBackendMenuMessage {
  type: 'showBackendMenu';
}

export interface OpenInSimpleBrowserMessage {
  type: 'openInSimpleBrowser';
  url: string;
}

export interface RevealInFinderMessage {
  type: 'revealInFinder';
  path: string;
}

export interface RenameFileMessage {
  type: 'renameFile';
  oldPath: string;
  newPath: string;
}

export interface DeleteFileMessage {
  type: 'deleteFile';
  path: string;
}

export interface CreateFileMessage {
  type: 'createFile';
  path: string;
}

export interface CreateFolderMessage {
  type: 'createFolder';
  path: string;
}

export interface DuplicateFileMessage {
  type: 'duplicateFile';
  sourcePath: string;
  destPath: string;
  newRelativePath: string;
}

export interface OpenInTerminalMessage {
  type: 'openInTerminal';
  path: string;
}

export interface ListFilesMessage {
  type: 'listFiles';
  projectRoot: string;
  includeAll?: boolean;
}

export interface LoadDirectoryMessage {
  type: 'loadDirectory';
  projectRoot: string;
  directoryPath: string;
}

export interface GetAtopileSettingsMessage {
  type: 'getAtopileSettings';
}

export interface ThreeDModelBuildResultMessage {
  type: 'threeDModelBuildResult';
  success: boolean;
  error?: string | null;
}

export interface WebviewReadyMessage {
  type: 'webviewReady';
}

export interface WebviewDiagnosticMessage {
  type: 'webviewDiagnostic';
  phase: string;
  detail?: string;
}

export interface OpenMigrateTabMessage {
  type: 'openMigrateTab';
  projectRoot: string;
}

export type WebviewMessage =
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
