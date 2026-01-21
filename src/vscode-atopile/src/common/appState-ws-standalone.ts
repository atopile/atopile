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
};

const WS_URL = 'ws://localhost:8501/ws/state';
const RECONNECT_INTERVAL = 3000;

type StateChangeListener = (state: AppState) => void;

class WebSocketAppStateManager {
    private _state: AppState = { ...DEFAULT_STATE };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    private _ws: any = null;
    private _reconnectTimer: NodeJS.Timeout | null = null;
    private _listeners: StateChangeListener[] = [];
    private _isConnecting = false;

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

    connect(): void {
        if (this._isConnecting || (this._ws && this._ws.readyState === WebSocket.OPEN)) {
            return;
        }

        this._isConnecting = true;
        traceInfo(`Connecting to Python backend: ${WS_URL}`);

        try {
            this._ws = new WebSocket(WS_URL);

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
                        this._state = { ...message.data, isConnected: true };
                        this._notifyListeners();
                    } else if (message.type === 'action_result') {
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
            traceInfo(`Atopile settings changed in UI, updating extension settings`);

            const config = vscode.workspace.getConfiguration('atopile');
            const atopile = state.atopile;

            if (atopile?.source === 'local' && atopile.localPath) {
                // For local mode, set the 'ato' setting directly
                await config.update('ato', atopile.localPath, vscode.ConfigurationTarget.Workspace);
                await config.update('from', undefined, vscode.ConfigurationTarget.Workspace);
            } else {
                // For release/branch mode, set the 'from' setting
                const fromValue = atopileSettingsToFrom(atopile);
                await config.update('from', fromValue, vscode.ConfigurationTarget.Workspace);
                await config.update('ato', undefined, vscode.ConfigurationTarget.Workspace);
            }
            // The configuration change will trigger findbin's onDidChangeConfiguration listener
            // which will fire onDidChangeAtoBinInfoEvent and trigger a server restart
        }

        previousAtopileSettings = newSettings;
    });

    return disposable;
}
