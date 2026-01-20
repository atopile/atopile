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
    status: StageStatus;
    warnings: number;
    errors: number;
}

export interface Build {
    name: string;  // Target name for matching
    display_name: string;
    build_id: string;
    status: BuildStatus;
    elapsed_seconds: number;
    warnings: number;
    errors: number;
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
        build_id: string;
        timestamp: string;
        stage: string;
        level: string;
        audience: string;
        message: string;
        ato_traceback: string | null;
        python_traceback: string | null;
        objects: Record<string, unknown> | null;
        project_path: string;
        target: string;
        build_timestamp: string;
    }>;
    total: number;
    builds: Array<{
        build_id: string;
        project_path: string;
        target: string;
        timestamp: string;
        created_at: string;
    }>;
}

// Info about the currently displayed build's logs
export interface CurrentBuildInfo {
    buildId: string;
    projectPath: string;
    target: string;
    timestamp: string;
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
    selectedBuildId: string | null;  // Track the actual build_id being polled
    currentBuildInfo: CurrentBuildInfo | null;  // Info about currently displayed logs
    logEntries: LogEntry[];
    isLoadingLogs: boolean;

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
        selectedBuildId: null,
        currentBuildInfo: null,
        logEntries: [],
        isLoadingLogs: false,

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
        this._state.selectedBuildId = null;
        this._state.currentBuildInfo = null;
        this._state.logEntries = [];
        this._lastLogId = 0;

        const build = this._state.builds.find(b => b.display_name === buildName);
        if (build?.build_id) {
            this._state.selectedBuildId = build.build_id;
            this._state.isLoadingLogs = true;
            this._emit();
            await this._startPollingLogs(build.build_id);
        } else {
            this._state.isLoadingLogs = false;
            this._emit();
        }
    }

    // --- Log viewer UI ---

    async toggleLogLevel(level: LogLevel): Promise<void> {
        const idx = this._state.enabledLogLevels.indexOf(level);
        if (idx >= 0) {
            this._state.enabledLogLevels = this._state.enabledLogLevels.filter(l => l !== level);
        } else {
            this._state.enabledLogLevels = [...this._state.enabledLogLevels, level];
        }
        this._emit();
        // Re-fetch logs with new filter
        if (this._state.selectedBuildId) {
            await this._fetchLogs(this._state.selectedBuildId);
        }
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

            // Auto-select first build if none selected
            if (!this._state.selectedBuildName && this._state.builds.length > 0) {
                await this.selectBuild(this._state.builds[0].display_name);
                return;
            }

            // Check if the selected build's build_id has changed (new build for same target)
            // This happens when a new build is triggered for the same target
            if (this._state.selectedBuildName && this._state.selectedBuildId) {
                const currentBuild = this._state.builds.find(
                    b => b.display_name === this._state.selectedBuildName
                );
                if (currentBuild && currentBuild.build_id !== this._state.selectedBuildId) {
                    traceInfo(`AppState: build_id changed for ${this._state.selectedBuildName}, restarting log polling`);
                    // Restart log polling with new build_id
                    this._stopPollingLogs();
                    this._state.selectedBuildId = currentBuild.build_id;
                    this._state.currentBuildInfo = null;
                    this._state.logEntries = [];
                    this._lastLogId = 0;
                    this._state.isLoadingLogs = true;
                    this._emit();
                    await this._startPollingLogs(currentBuild.build_id);
                    return;
                }
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

    private async _fetchLogs(buildId: string): Promise<void> {
        const apiUrl = getDashboardApiUrl();

        // Build filter params from current state
        const params: Record<string, string | number> = {
            build_id: buildId,
            limit: 10000,
        };

        // Add level filter (comma-separated)
        if (this._state.enabledLogLevels.length > 0) {
            params.levels = this._state.enabledLogLevels.join(',');
        }

        try {
            const response = await axios.get<LogQueryResponse>(
                `${apiUrl}/api/logs/query`,
                {
                    params,
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

                // Extract build info from first log entry (all logs share same build info)
                const firstLog = response.data.logs[0];
                this._state.currentBuildInfo = {
                    buildId: firstLog.build_id,
                    projectPath: firstLog.project_path,
                    target: firstLog.target,
                    timestamp: firstLog.build_timestamp,
                };
            }

            // Update state with new entries
            this._state.logEntries = newEntries;
            this._state.isLoadingLogs = false;
            this._emit();

            traceVerbose(`AppState: fetched ${newEntries.length} log entries for build ${buildId}`);
        } catch (error) {
            traceError(`AppState: failed to fetch logs: ${error}`);
            this._state.isLoadingLogs = false;
            this._emit();
        }
    }

    private async _startPollingLogs(buildId: string): Promise<void> {
        // Initial fetch
        await this._fetchLogs(buildId);

        // Start polling for updates
        this._logPollTimer = setInterval(async () => {
            const build = this._state.builds.find(b => b.build_id === buildId);
            if (build && this._state.selectedBuildName === build.display_name) {
                await this._fetchLogs(buildId);
            }
        }, 500);

        traceInfo(`AppState: started polling logs for build ${buildId}`);
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
