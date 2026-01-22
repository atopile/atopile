/**
 * Thin WebSocket-based AppStateManager.
 *
 * All state lives in Python. This module:
 * - Connects to Python's /ws/state WebSocket endpoint
 * - Receives full AppState updates from Python
 * - Forwards actions to Python via WebSocket
 * - Notifies listeners when state changes
 */

import * as vscode from 'vscode';
import { traceInfo, traceError, traceVerbose } from './log/logging';

// eslint-disable-next-line @typescript-eslint/no-var-requires
const WebSocket = require('ws');

// Re-export types for compatibility
export type BuildStatus = 'queued' | 'building' | 'success' | 'warning' | 'failed';
export type StageStatus = 'success' | 'warning' | 'failed';
export type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'ALERT';

export interface LogEntry {
    timestamp: string;
    level: LogLevel;
    logger: string;
    stage: string;
    message: string;
    ato_traceback?: string;
    exc_info?: string;
}

export interface BuildStage {
    name: string;
    stage_id: string;
    elapsed_seconds: number;
    status: StageStatus;
    infos: number;
    warnings: number;
    errors: number;
    alerts: number;
}

export interface Build {
    name: string;
    display_name: string;
    project_name: string | null;
    status: BuildStatus;
    elapsed_seconds: number;
    warnings: number;
    errors: number;
    return_code: number | null;
    log_dir?: string;
    log_file?: string;
    stages?: BuildStage[];
}

export interface BuildTarget {
    name: string;
    entry: string;
    root: string;
}

export interface Project {
    root: string;
    name: string;
    targets: BuildTarget[];
}

export interface PackageInfo {
    identifier: string;
    name: string;
    publisher: string;
    version?: string;
    latest_version?: string;
    description?: string;
    summary?: string;
    homepage?: string;
    repository?: string;
    license?: string;
    installed: boolean;
    installed_in: string[];
    has_update?: boolean;
    downloads?: number;
    version_count?: number;
    keywords?: string[];
}

export interface Problem {
    id: string;
    level: 'error' | 'warning';
    message: string;
    file?: string;
    line?: number;
    column?: number;
    stage?: string;
    logger?: string;
    buildName?: string;
    projectName?: string;
    timestamp?: string;
    ato_traceback?: string;
}

export interface ModuleDefinition {
    name: string;
    type: 'module' | 'interface' | 'component';
    file: string;
    entry: string;
    line?: number;
    super_type?: string;
}

export interface FileTreeNode {
    name: string;
    path: string;
    type: 'file' | 'folder';
    extension?: string;
    children?: FileTreeNode[];
}

export interface AppState {
    isConnected: boolean;
    projects: Project[];
    selectedProjectRoot: string | null;
    selectedTargetNames: string[];
    builds: Build[];
    queuedBuilds: Build[];
    packages: PackageInfo[];
    isLoadingPackages: boolean;
    packagesError: string | null;
    stdlibItems: any[];
    isLoadingStdlib: boolean;
    bomData: any;
    isLoadingBOM: boolean;
    bomError: string | null;
    selectedPackageDetails: any;
    isLoadingPackageDetails: boolean;
    packageDetailsError: string | null;
    selectedBuildName: string | null;
    selectedProjectName: string | null;
    selectedStageIds: string[];
    logEntries: LogEntry[];
    isLoadingLogs: boolean;
    logFile: string | null;
    enabledLogLevels: LogLevel[];
    logSearchQuery: string;
    logTimestampMode: 'absolute' | 'delta';
    logAutoScroll: boolean;
    logCounts?: { DEBUG: number; INFO: number; WARNING: number; ERROR: number; ALERT: number };
    logTotalCount?: number;
    logHasMore?: boolean;
    expandedTargets: string[];
    version: string;
    logoUri: string;
    atopile: any;
    problems: Problem[];
    isLoadingProblems: boolean;
    problemFilter: { levels: ('error' | 'warning')[]; buildNames: string[]; stageIds: string[] };
    projectModules: Record<string, ModuleDefinition[]>;
    isLoadingModules: boolean;
    projectFiles: Record<string, FileTreeNode[]>;
    isLoadingFiles: boolean;
    currentVariablesData: any;
    isLoadingVariables: boolean;
    variablesError: string | null;
    // Open signals (one-shot signals from backend)
    openFile: string | null;
    openFileLine: number | null;
    openFileColumn: number | null;
    openLayout: string | null;
    openKicad: string | null;
    open3d: string | null;
}

const DEFAULT_STATE: AppState = {
    isConnected: false,
    projects: [],
    selectedProjectRoot: null,
    selectedTargetNames: [],
    builds: [],
    queuedBuilds: [],
    packages: [],
    isLoadingPackages: false,
    packagesError: null,
    stdlibItems: [],
    isLoadingStdlib: false,
    bomData: null,
    isLoadingBOM: false,
    bomError: null,
    selectedPackageDetails: null,
    isLoadingPackageDetails: false,
    packageDetailsError: null,
    selectedBuildName: null,
    selectedProjectName: null,
    selectedStageIds: [],
    logEntries: [],
    isLoadingLogs: false,
    logFile: null,
    enabledLogLevels: ['INFO', 'WARNING', 'ERROR', 'ALERT'],
    logSearchQuery: '',
    logTimestampMode: 'absolute',
    logAutoScroll: true,
    logCounts: { DEBUG: 0, INFO: 0, WARNING: 0, ERROR: 0, ALERT: 0 },
    logTotalCount: 0,
    logHasMore: false,
    expandedTargets: [],
    version: '',
    logoUri: '',
    atopile: {
        currentVersion: '',
        source: 'release',
        localPath: null,
        branch: null,
        availableVersions: [],
        availableBranches: [],
        detectedInstallations: [],
        isInstalling: false,
        installProgress: null,
        error: null,
    },
    problems: [],
    isLoadingProblems: false,
    problemFilter: { levels: ['error', 'warning'], buildNames: [], stageIds: [] },
    projectModules: {},
    isLoadingModules: false,
    projectFiles: {},
    isLoadingFiles: false,
    currentVariablesData: null,
    isLoadingVariables: false,
    variablesError: null,
    openFile: null,
    openFileLine: null,
    openFileColumn: null,
    openLayout: null,
    openKicad: null,
    open3d: null,
};

const DEFAULT_PORT = 8501;
const RECONNECT_INTERVAL = 3000;

// Dynamic port - can be updated by backendServer when port is discovered
let _currentPort = DEFAULT_PORT;

/**
 * Get the WebSocket URL using the current port.
 */
function getWsUrl(): string {
    return `ws://localhost:${_currentPort}/ws/state`;
}

/**
 * Update the port used for WebSocket connections.
 * Called by backendServer when port is discovered.
 */
export function setServerPort(port: number): void {
    if (port !== _currentPort) {
        traceInfo(`AppState: Server port updated to ${port}`);
        _currentPort = port;
        // Reconnect with new port
        appStateManager.reconnect();
    }
}

type StateChangeListener = (state: AppState) => void;

class WebSocketAppStateManager {
    private _state: AppState = { ...DEFAULT_STATE };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    private _ws: any = null;
    private _reconnectTimer: NodeJS.Timeout | null = null;
    private _listeners: StateChangeListener[] = [];
    private _isConnecting = false;
    private _requestCounter = 0;
    private _pendingRequests = new Map<string, {
        resolve: (message: any) => void;
        reject: (error: Error) => void;
        timeoutId: NodeJS.Timeout;
    }>();

    constructor() {
        this.connect();
    }

    getState(): AppState {
        return this._state;
    }

    onStateChange(listener: StateChangeListener): vscode.Disposable {
        this._listeners.push(listener);
        return new vscode.Disposable(() => {
            const idx = this._listeners.indexOf(listener);
            if (idx >= 0) this._listeners.splice(idx, 1);
        });
    }

    private _notifyListeners(): void {
        for (const listener of this._listeners) {
            try {
                listener(this._state);
            } catch (e) {
                traceError(`State listener error: ${e}`);
            }
        }
    }

    private _handleOpenSignals(state: AppState): void {
        // Handle open file signal
        if (state.openFile) {
            const filePath = state.openFile;
            const line = state.openFileLine;
            const column = state.openFileColumn;
            traceInfo(`Open file signal: ${filePath}${line ? `:${line}` : ''}`);

            const uri = vscode.Uri.file(filePath);
            vscode.workspace.openTextDocument(uri).then(
                (doc) => {
                    const options: vscode.TextDocumentShowOptions = {};
                    if (line !== null && line !== undefined) {
                        const position = new vscode.Position(Math.max(0, line - 1), column ?? 0);
                        options.selection = new vscode.Range(position, position);
                    }
                    vscode.window.showTextDocument(doc, options);
                },
                (err) => {
                    traceError(`Failed to open file ${filePath}: ${err}`);
                }
            );
        }

        // Handle open layout signal
        if (state.openLayout) {
            const layoutPath = state.openLayout;
            traceInfo(`Open layout signal: ${layoutPath}`);

            // Open the layout file in VS Code
            const uri = vscode.Uri.file(layoutPath);
            vscode.commands.executeCommand('vscode.open', uri);
        }

        // Handle open KiCad signal
        if (state.openKicad) {
            const kicadPath = state.openKicad;
            traceInfo(`Open KiCad signal: ${kicadPath}`);

            // Use the system command to open KiCad
            const { exec } = require('child_process');
            const platform = process.platform;

            if (platform === 'darwin') {
                exec(`open "${kicadPath}"`, (err: Error | null) => {
                    if (err) {
                        traceError(`Failed to open KiCad: ${err}`);
                        vscode.window.showErrorMessage(`Failed to open KiCad: ${err.message}`);
                    }
                });
            } else if (platform === 'win32') {
                exec(`start "" "${kicadPath}"`, (err: Error | null) => {
                    if (err) {
                        traceError(`Failed to open KiCad: ${err}`);
                        vscode.window.showErrorMessage(`Failed to open KiCad: ${err.message}`);
                    }
                });
            } else {
                exec(`xdg-open "${kicadPath}"`, (err: Error | null) => {
                    if (err) {
                        traceError(`Failed to open KiCad: ${err}`);
                        vscode.window.showErrorMessage(`Failed to open KiCad: ${err.message}`);
                    }
                });
            }
        }

        // Handle open 3D signal
        if (state.open3d) {
            const modelPath = state.open3d;
            traceInfo(`Open 3D signal: ${modelPath}`);

            // Open the 3D model file with the system default viewer
            const { exec } = require('child_process');
            const platform = process.platform;

            if (platform === 'darwin') {
                exec(`open "${modelPath}"`, (err: Error | null) => {
                    if (err) {
                        traceError(`Failed to open 3D model: ${err}`);
                        vscode.window.showErrorMessage(`Failed to open 3D model: ${err.message}`);
                    }
                });
            } else if (platform === 'win32') {
                exec(`start "" "${modelPath}"`, (err: Error | null) => {
                    if (err) {
                        traceError(`Failed to open 3D model: ${err}`);
                        vscode.window.showErrorMessage(`Failed to open 3D model: ${err.message}`);
                    }
                });
            } else {
                exec(`xdg-open "${modelPath}"`, (err: Error | null) => {
                    if (err) {
                        traceError(`Failed to open 3D model: ${err}`);
                        vscode.window.showErrorMessage(`Failed to open 3D model: ${err.message}`);
                    }
                });
            }
        }
    }

    /**
     * Reconnect to the server (e.g., after port change).
     */
    reconnect(): void {
        if (this._ws) {
            this._ws.close();
            this._ws = null;
        }
        if (this._reconnectTimer) {
            clearTimeout(this._reconnectTimer);
            this._reconnectTimer = null;
        }
        this._isConnecting = false;
        this.connect();
    }

    connect(): void {
        if (this._isConnecting || (this._ws && this._ws.readyState === WebSocket.OPEN)) {
            return;
        }

        this._isConnecting = true;
        const wsUrl = getWsUrl();
        traceInfo(`Connecting to Python backend: ${wsUrl}`);

        try {
            this._ws = new WebSocket(wsUrl);

            this._ws.on('open', () => {
                this._isConnecting = false;
                this._state.isConnected = true;
                traceInfo('Connected to Python backend');
                this._notifyListeners();
            });

            this._ws.on('message', (data: Buffer | ArrayBuffer | Buffer[]) => {
                try {
                    const message = JSON.parse(data.toString());
                    if (message.type === 'state') {
                        const newState = { ...message.data, isConnected: true };

                        // Handle open signals before updating state
                        this._handleOpenSignals(newState);

                        this._state = newState;
                        this._notifyListeners();
                    } else if (message.type === 'action_result') {
                        const requestId = typeof message.payload?.requestId === 'string'
                            ? message.payload.requestId
                            : null;
                        if (requestId && this._pendingRequests.has(requestId)) {
                            const pending = this._pendingRequests.get(requestId)!;
                            clearTimeout(pending.timeoutId);
                            this._pendingRequests.delete(requestId);
                            const result = message.result || message;
                            if (result.success) {
                                pending.resolve(message);
                            } else {
                                pending.reject(new Error(String(result.error || 'Action failed')));
                            }
                        }
                        traceVerbose(`Action result: ${JSON.stringify(message)}`);
                    }
                } catch (e) {
                    traceError(`Failed to parse message: ${e}`);
                }
            });

            this._ws.on('close', () => {
                this._isConnecting = false;
                this._state.isConnected = false;
                traceInfo('Disconnected from Python backend');
                this._notifyListeners();
                this._scheduleReconnect();
            });

            this._ws.on('error', (err: Error) => {
                this._isConnecting = false;
                traceError(`WebSocket error: ${err.message}`);
                this._scheduleReconnect();
            });

        } catch (e) {
            this._isConnecting = false;
            traceError(`Failed to create WebSocket: ${e}`);
            this._scheduleReconnect();
        }
    }

    private _scheduleReconnect(): void {
        if (this._reconnectTimer) return;
        this._reconnectTimer = setTimeout(() => {
            this._reconnectTimer = null;
            this.connect();
        }, RECONNECT_INTERVAL);
    }

    disconnect(): void {
        if (this._reconnectTimer) {
            clearTimeout(this._reconnectTimer);
            this._reconnectTimer = null;
        }
        if (this._pendingRequests.size > 0) {
            for (const [requestId, pending] of this._pendingRequests.entries()) {
                clearTimeout(pending.timeoutId);
                pending.reject(new Error('WebSocket disconnected'));
                this._pendingRequests.delete(requestId);
            }
        }
        if (this._ws) {
            this._ws.close();
            this._ws = null;
        }
    }

    // Send an action to Python backend
    sendAction(action: string, payload: Record<string, any> = {}): void {
        if (!this._ws || this._ws.readyState !== WebSocket.OPEN) {
            traceError(`Cannot send action ${action}: not connected`);
            return;
        }
        const message = { type: 'action', action, payload };
        this._ws.send(JSON.stringify(message));
        traceVerbose(`Sent action: ${action}`);
    }

    // Send an action and await a response
    sendActionWithResponse(
        action: string,
        payload: Record<string, any> = {},
        options?: { timeoutMs?: number },
    ): Promise<any> {
        if (!this._ws || this._ws.readyState !== WebSocket.OPEN) {
            return Promise.reject(new Error(`Cannot send action ${action}: not connected`));
        }

        this._requestCounter += 1;
        const requestId = `${Date.now()}-${this._requestCounter}`;
        const timeoutMs = options?.timeoutMs ?? 10000;

        return new Promise((resolve, reject) => {
            const timeoutId = setTimeout(() => {
                this._pendingRequests.delete(requestId);
                reject(new Error(`Action timeout: ${action}`));
            }, timeoutMs);

            this._pendingRequests.set(requestId, { resolve, reject, timeoutId });
            this.sendAction(action, { ...payload, requestId });
        });
    }

    // Action helpers - forward to Python
    selectProject(projectRoot: string | null): void {
        this.sendAction('selectProject', { projectRoot });
    }

    toggleTarget(targetName: string): void {
        this.sendAction('toggleTarget', { targetName });
    }

    toggleTargetExpanded(targetName: string): void {
        this.sendAction('toggleTargetExpanded', { targetName });
    }

    selectBuild(buildName: string | null): void {
        this.sendAction('selectBuild', { buildName });
    }

    toggleLogLevel(level: LogLevel): void {
        this.sendAction('toggleLogLevel', { level });
    }

    setLogSearchQuery(query: string): void {
        this.sendAction('setLogSearchQuery', { query });
    }

    setLogTimestampMode(mode: 'absolute' | 'delta'): void {
        this.sendAction('setLogTimestampMode', { mode });
    }

    toggleLogTimestampMode(): void {
        this.sendAction('toggleLogTimestampMode', {});
    }

    setLogAutoScroll(enabled: boolean): void {
        this.sendAction('setLogAutoScroll', { enabled });
    }

    // Data refresh actions - Python handles these
    refreshProjects(): void {
        this.sendAction('refreshProjects', {});
    }

    refreshPackages(forceRefresh: boolean = false): void {
        this.sendAction('refreshPackages', { forceRefresh });
    }

    refreshStdlib(forceRefresh: boolean = false): void {
        this.sendAction('refreshStdlib', { forceRefresh });
    }

    refreshBOM(projectRoot?: string, target: string = 'default'): void {
        this.sendAction('refreshBOM', { projectRoot, target });
    }

    refreshProblems(): void {
        this.sendAction('refreshProblems', {});
    }

    // Build actions
    build(projectRoot: string, targets: string[]): void {
        this.sendAction('build', { projectRoot, targets });
    }

    cancelBuild(buildId: string): void {
        this.sendAction('cancelBuild', { buildId });
    }

    // Package actions
    installPackage(packageId: string, projectRoot: string, version?: string): void {
        this.sendAction('installPackage', { packageId, projectRoot, version });
    }

    removePackage(packageId: string, projectRoot: string): void {
        this.sendAction('removePackage', { packageId, projectRoot });
    }

    getPackageDetails(packageId: string): void {
        this.sendAction('getPackageDetails', { packageId });
    }

    clearPackageDetails(): void {
        this.sendAction('clearPackageDetails', {});
    }

    // Module/File fetching
    fetchModules(projectRoot: string, forceRefresh: boolean = false): void {
        this.sendAction('fetchModules', { projectRoot, forceRefresh });
    }

    fetchFiles(projectRoot: string, forceRefresh: boolean = false): void {
        this.sendAction('fetchFiles', { projectRoot, forceRefresh });
    }

    fetchVariables(projectRoot: string, target: string = 'default'): void {
        this.sendAction('fetchVariables', { projectRoot, target });
    }

    // Extension info
    setExtensionInfo(version: string, logoUri: string): void {
        this._state.version = version;
        this._state.logoUri = logoUri;
        this._notifyListeners();
    }

    dispose(): void {
        this.disconnect();
        this._listeners = [];
    }
}

/**
 * Convert UI atopile settings to a VS Code 'atopile.from' setting value.
 */
function atopileSettingsToFrom(atopile: AppState['atopile']): string {
    if (!atopile) return 'atopile';

    switch (atopile.source) {
        case 'release':
            // Use version if specified, otherwise just 'atopile'
            return atopile.currentVersion
                ? `atopile@${atopile.currentVersion}`
                : 'atopile';
        case 'branch':
            // Use git+ URL for branch
            return `git+https://github.com/atopile/atopile.git@${atopile.branch || 'main'}`;
        case 'local':
            // For local, we use the path directly as the 'ato' setting
            // Return empty string to indicate local mode
            return atopile.localPath || '';
        default:
            return 'atopile';
    }
}

// Singleton instance
export const appStateManager = new WebSocketAppStateManager();

/**
 * Initialize atopile settings sync between UI and extension.
 * Call this after extension activation to connect UI settings to the extension.
 */
export function initAtopileSettingsSync(_context: vscode.ExtensionContext): vscode.Disposable {
    let previousAtopileSettings: string | null = null;

    const disposable = appStateManager.onStateChange(async (state) => {
        const newSettings = JSON.stringify({
            source: state.atopile?.source,
            currentVersion: state.atopile?.currentVersion,
            branch: state.atopile?.branch,
            localPath: state.atopile?.localPath,
        });

        // Only update if settings actually changed
        if (previousAtopileSettings !== null && previousAtopileSettings !== newSettings) {
            traceInfo(`Atopile settings changed in UI: ${newSettings}`);

            const config = vscode.workspace.getConfiguration('atopile');
            const atopile = state.atopile;

            // Determine config target - use workspace if available, otherwise global
            const hasWorkspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length > 0;
            const target = hasWorkspace ? vscode.ConfigurationTarget.Workspace : vscode.ConfigurationTarget.Global;
            traceInfo(`Updating atopile settings (target: ${hasWorkspace ? 'workspace' : 'global'})`);

            try {
                if (atopile?.source === 'local' && atopile.localPath) {
                    // For local mode, set the 'ato' setting directly
                    traceInfo(`Setting atopile.ato = ${atopile.localPath}`);
                    await config.update('ato', atopile.localPath, target);
                    await config.update('from', undefined, target);
                } else {
                    // For release/branch mode, set the 'from' setting
                    const fromValue = atopileSettingsToFrom(atopile);
                    traceInfo(`Setting atopile.from = ${fromValue}`);
                    await config.update('from', fromValue, target);
                    await config.update('ato', undefined, target);
                }
                traceInfo('Atopile settings updated successfully');
                // The configuration change will trigger findbin's onDidChangeConfiguration listener
                // which will fire onDidChangeAtoBinInfoEvent and trigger a server restart
            } catch (error) {
                traceError(`Failed to update atopile settings: ${error}`);
            }
        }

        previousAtopileSettings = newSettings;
    });

    return disposable;
}
