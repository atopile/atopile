/**
 * AppStateManager - THE SINGLE source of truth for all UI state.
 *
 * All state lives in AppState. Webviews receive this state read-only
 * and send actions back to mutate it.
 */

import * as vscode from 'vscode';
import axios from 'axios';
import { traceInfo, traceError, traceVerbose } from './log/logging';

// Types - import from shared location to avoid duplication
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

export interface BuildSummary {
    timestamp: string;
    totals: {
        builds: number;
        successful: number;
        failed: number;
        warnings: number;
        errors: number;
    };
    builds: Build[];
    error?: string;
}

// API response type for /api/logs/query
interface LogQueryResponse {
    logs: Array<{
        id: number;
        timestamp: string;
        stage: string;
        level: string;
        level_no: number;
        audience: string;
        message: string;
        ato_traceback: string | null;
        python_traceback: string | null;
        build_dir: string;
    }>;
    total: number;
}

/**
 * THE SINGLE APP STATE - All state lives here.
 */
export interface AppState {
    // Connection
    isConnected: boolean;

    // Projects (from ato.yaml)
    projects: Project[];
    selectedProjectRoot: string | null;
    selectedTargetNames: string[];

    // Builds (from dashboard API)
    builds: Build[];

    // Build/Log selection
    selectedBuildName: string | null;
    selectedStageIds: string[];
    logEntries: LogEntry[];
    isLoadingLogs: boolean;
    logFile: string | null;

    // Log viewer UI
    enabledLogLevels: LogLevel[];
    logSearchQuery: string;
    logTimestampMode: 'absolute' | 'delta';
    logAutoScroll: boolean;

    // Sidebar UI
    expandedTargets: string[];

    // Extension info
    version: string;
    logoUri: string;
}

const DEFAULT_LOG_LEVELS: LogLevel[] = ['INFO', 'WARNING', 'ERROR', 'ALERT'];

function getDashboardApiUrl(): string {
    const config = vscode.workspace.getConfiguration('atopile');
    return config.get<string>('dashboardApiUrl', 'http://localhost:8501');
}

class AppStateManager {
    private _state: AppState = {
        // Connection
        isConnected: false,

        // Projects
        projects: [],
        selectedProjectRoot: null,
        selectedTargetNames: [],

        // Builds
        builds: [],

        // Log viewing
        selectedBuildName: null,
        selectedStageIds: [],
        logEntries: [],
        isLoadingLogs: false,
        logFile: null,

        // Log viewer UI
        enabledLogLevels: [...DEFAULT_LOG_LEVELS],
        logSearchQuery: '',
        logTimestampMode: 'absolute',
        logAutoScroll: true,

        // Sidebar UI
        expandedTargets: [],

        // Extension info
        version: '',
        logoUri: '',
    };

    private _pollTimer: NodeJS.Timeout | null = null;
    private _logPollTimer: NodeJS.Timeout | null = null;
    private _lastLogId: number = 0;

    // SINGLE EVENT for all state changes
    private readonly _onStateChange = new vscode.EventEmitter<AppState>();
    public readonly onStateChange = this._onStateChange.event;

    getState(): AppState {
        return { ...this._state };
    }

    private _emit(): void {
        this._onStateChange.fire(this.getState());
    }

    // --- Extension info ---

    setExtensionInfo(version: string, logoUri: string): void {
        this._state.version = version;
        this._state.logoUri = logoUri;
        this._emit();
    }

    // --- Projects ---

    setProjects(projects: Project[]): void {
        this._state.projects = projects;
        this._emit();
    }

    selectProject(root: string | null): void {
        this._state.selectedProjectRoot = root;
        if (root) {
            const project = this._state.projects.find(p => p.root === root);
            this._state.selectedTargetNames = project?.targets.map(t => t.name) ?? [];
        } else {
            this._state.selectedTargetNames = [];
        }
        this._emit();
    }

    setSelectedProjectRoot(root: string | null): void {
        this._state.selectedProjectRoot = root;
        this._emit();
    }

    setSelectedTargetNames(names: string[]): void {
        this._state.selectedTargetNames = names;
        this._emit();
    }

    toggleTarget(name: string): void {
        const idx = this._state.selectedTargetNames.indexOf(name);
        if (idx >= 0) {
            this._state.selectedTargetNames = this._state.selectedTargetNames.filter(n => n !== name);
        } else {
            this._state.selectedTargetNames = [...this._state.selectedTargetNames, name];
        }
        this._emit();
    }

    // --- Builds ---

    async selectBuild(buildName: string | null): Promise<void> {
        if (this._state.selectedBuildName === buildName) return;

        this._stopPollingLogs();

        this._state.selectedBuildName = buildName;
        this._state.selectedStageIds = [];
        this._state.logEntries = [];
        this._state.logFile = null;
        this._lastLogId = 0;

        const build = this._state.builds.find(b => b.display_name === buildName);
        if (build?.log_dir) {
            this._state.isLoadingLogs = true;
            this._state.logFile = build.log_file ?? null;
            this._emit();
            await this._startPollingLogs(build.display_name);
        } else {
            this._state.isLoadingLogs = false;
            this._emit();
        }
    }

    // --- Stage filter ---

    toggleStageFilter(stageId: string): void {
        const idx = this._state.selectedStageIds.indexOf(stageId);
        if (idx >= 0) {
            this._state.selectedStageIds = this._state.selectedStageIds.filter(id => id !== stageId);
        } else {
            this._state.selectedStageIds = [...this._state.selectedStageIds, stageId];
        }
        this._emit();
    }

    clearStageFilter(): void {
        this._state.selectedStageIds = [];
        this._emit();
    }

    // --- Log viewer UI ---

    toggleLogLevel(level: LogLevel): void {
        const idx = this._state.enabledLogLevels.indexOf(level);
        if (idx >= 0) {
            this._state.enabledLogLevels = this._state.enabledLogLevels.filter(l => l !== level);
        } else {
            this._state.enabledLogLevels = [...this._state.enabledLogLevels, level];
        }
        this._emit();
    }

    setLogSearchQuery(query: string): void {
        this._state.logSearchQuery = query;
        this._emit();
    }

    toggleLogTimestampMode(): void {
        this._state.logTimestampMode = this._state.logTimestampMode === 'absolute' ? 'delta' : 'absolute';
        this._emit();
    }

    setLogAutoScroll(enabled: boolean): void {
        this._state.logAutoScroll = enabled;
        this._emit();
    }

    // --- Sidebar UI ---

    toggleTargetExpanded(targetName: string): void {
        const idx = this._state.expandedTargets.indexOf(targetName);
        if (idx >= 0) {
            this._state.expandedTargets = this._state.expandedTargets.filter(t => t !== targetName);
        } else {
            this._state.expandedTargets = [...this._state.expandedTargets, targetName];
        }
        this._emit();
    }

    // --- API polling ---

    async fetchSummary(): Promise<void> {
        const apiUrl = getDashboardApiUrl();

        try {
            const response = await axios.get<BuildSummary>(`${apiUrl}/api/summary`, { timeout: 5000 });
            this._state.isConnected = true;
            this._state.builds = response.data.builds;

            if (!this._state.selectedBuildName && this._state.builds.length > 0) {
                await this.selectBuild(this._state.builds[0].display_name);
                return;
            }
            this._emit();
            traceVerbose(`AppState: fetched summary with ${this._state.builds.length} builds`);
        } catch {
            const wasConnected = this._state.isConnected;
            this._state.isConnected = false;
            if (wasConnected) {
                this._emit();
                traceInfo('AppState: disconnected from API');
            }
        }
    }

    startPolling(interval: number = 500): void {
        this.stopPolling();
        traceInfo(`AppState: starting polling at ${interval}ms interval`);
        this.fetchSummary();
        this._pollTimer = setInterval(() => this.fetchSummary(), interval);
    }

    stopPolling(): void {
        if (this._pollTimer) {
            clearInterval(this._pollTimer);
            this._pollTimer = null;
        }
        this._stopPollingLogs();
        traceInfo('AppState: stopped polling');
    }

    // --- Log API polling ---

    private async _fetchLogs(buildName: string): Promise<void> {
        const apiUrl = getDashboardApiUrl();

        try {
            const response = await axios.get<LogQueryResponse>(
                `${apiUrl}/api/logs/query`,
                {
                    params: {
                        build_name: buildName,
                        limit: 10000,
                    },
                    timeout: 5000,
                }
            );

            // Convert API response to LogEntry format
            // API returns logs in descending order (newest first), reverse for display
            const newEntries: LogEntry[] = response.data.logs
                .reverse()
                .map(log => ({
                    timestamp: log.timestamp,
                    level: log.level as LogLevel,
                    logger: 'atopile',  // API doesn't return logger name
                    stage: log.stage,
                    message: log.message,
                    ato_traceback: log.ato_traceback ?? undefined,
                    exc_info: log.python_traceback ?? undefined,
                }));

            // Track the highest log ID for incremental updates
            if (response.data.logs.length > 0) {
                this._lastLogId = Math.max(...response.data.logs.map(l => l.id));
            }

            // Update state with new entries
            this._state.logEntries = newEntries;
            this._state.isLoadingLogs = false;
            this._emit();

            traceVerbose(`AppState: fetched ${newEntries.length} log entries for ${buildName}`);
        } catch (error) {
            traceError(`AppState: failed to fetch logs: ${error}`);
            this._state.isLoadingLogs = false;
            this._emit();
        }
    }

    private async _startPollingLogs(buildName: string): Promise<void> {
        // Initial fetch
        await this._fetchLogs(buildName);

        // Start polling for updates
        this._logPollTimer = setInterval(async () => {
            if (this._state.selectedBuildName === buildName) {
                await this._fetchLogs(buildName);
            }
        }, 500);

        traceInfo(`AppState: started polling logs for ${buildName}`);
    }

    private _stopPollingLogs(): void {
        if (this._logPollTimer) {
            clearInterval(this._logPollTimer);
            this._logPollTimer = null;
        }
        this._lastLogId = 0;
    }

    dispose(): void {
        this.stopPolling();
        this._onStateChange.dispose();
    }
}

// Singleton instance
export const appStateManager = new AppStateManager();
