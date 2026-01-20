/**
 * AppStateManager - THE SINGLE source of truth for all UI state.
 *
 * All state lives in AppState. Webviews receive this state read-only
 * and send actions back to mutate it.
 *
 * Uses WebSockets for real-time push updates from the backend.
 */

import * as vscode from 'vscode';
import * as WebSocket from 'ws';
import { traceInfo, traceError, traceVerbose } from './log/logging';
import { backendServer } from './backendServer';

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
    project_path?: string;  // Path to the project root (for multi-project workspaces)
    timestamp?: string;  // ISO timestamp when the build completed
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
    // Backend server status
    isBackendRunning: boolean;

    // Connection to dashboard API
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
    availableStages: string[];  // Stages available for current build
    enabledStages: string[];    // Stages to show (empty = all)
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
        // Backend server status
        isBackendRunning: false,

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
        availableStages: [],
        enabledStages: [],  // Empty = all stages
        logSearchQuery: '',
        logTimestampMode: 'absolute',
        logAutoScroll: true,

        // Sidebar UI
        expandedTargets: [],

        // Extension info
        version: '',
        logoUri: '',
    };


    // WebSocket connection
    private _ws: WebSocket | null = null;
    private _wsConnected: boolean = false;
    private _wsReconnectTimer: NodeJS.Timeout | null = null;
    private _wsClientId: string | null = null;
    private _isListening: boolean = false;

    // Log subscription tracking
    private _isSubscribedToLogs: boolean = false;

    // SINGLE EVENT for all state changes
    private readonly _onStateChange = new vscode.EventEmitter<AppState>();
    public readonly onStateChange = this._onStateChange.event;

    getState(): AppState {
        return { ...this._state };
    }

    private _emit(): void {
        this._onStateChange.fire(this.getState());
    }

    /**
     * Send a message over WebSocket.
     */
    private _sendWsMessage(type: string, data: Record<string, unknown>): void {
        if (!this._ws || !this._wsConnected) {
            traceVerbose(`AppState: cannot send ${type} - WebSocket not connected`);
            return;
        }
        try {
            this._ws.send(JSON.stringify({ type, data }));
            traceVerbose(`AppState: sent WebSocket message: ${type}`);
        } catch (err) {
            traceError(`AppState: failed to send WebSocket message: ${err}`);
        }
    }

    /**
     * Get the minimum log level name from enabled levels.
     * Returns the lowest enabled level (DEBUG < INFO < WARNING < ERROR < ALERT).
     */
    private _getMinLevel(): string {
        const levelOrder: LogLevel[] = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'ALERT'];
        for (const level of levelOrder) {
            if (this._state.enabledLogLevels.includes(level)) {
                return level;
            }
        }
        return 'INFO'; // Default
    }

    /**
     * Get enabled stages for server-side filtering.
     * Empty array = all stages (no filter), non-empty = filter to those stages.
     */
    private _getEnabledStages(): string[] {
        return this._state.enabledStages;
    }

    /**
     * Send subscribe_logs message to backend.
     * This starts a new subscription - backend will stream all matching logs from beginning.
     *
     * If we have a build_id (e.g., from selecting a historical build or build_started event), send it.
     * Otherwise, backend will look up the latest build for the target.
     *
     * Server-side filtering: build_id (required), level, and stages
     *
     * @param overrideBuildId - Optional build_id to use instead of looking up from builds list
     *                          (used when build_started event provides the new build_id)
     */
    private _sendSubscribeLogs(overrideBuildId?: string): void {
        const build = this._state.builds.find(
            b => b.display_name === this._state.selectedBuildName
        );
        if (!build) {
            traceVerbose('AppState: cannot subscribe - no build selected');
            return;
        }

        const projectPath = build.project_path || this._state.selectedProjectRoot || '';
        const target = build.name;

        // Use override build_id if provided (from build_started event), otherwise use build's id
        const buildId = overrideBuildId || build.build_id || null;

        // Clear existing logs - backend will send all matching logs after handshake
        this._state.logEntries = [];
        this._state.isLoadingLogs = true;

        // Send subscription request - include build_id if we have one
        // Backend will respond with "subscribed" containing the confirmed build_id
        this._sendWsMessage('subscribe_logs', {
            project_path: projectPath,
            target: target,
            build_id: buildId,
            min_level: this._getMinLevel(),
            stages: this._getEnabledStages(),
        });

        this._isSubscribedToLogs = true;
        traceInfo(`AppState: subscribing to logs for ${target} (build_id=${buildId || 'latest'})`);
    }

    /**
     * Send update_filters message to backend when filters change.
     * Both level and stage filtering is done server-side.
     */
    private _sendUpdateFilters(): void {
        if (!this._isSubscribedToLogs) {
            return; // Not subscribed, no need to update
        }

        // Clear local logs - backend will re-send all matching logs
        this._state.logEntries = [];
        this._state.isLoadingLogs = true;

        // Send both level and stage filters
        this._sendWsMessage('update_filters', {
            min_level: this._getMinLevel(),
            stages: this._getEnabledStages(),
        });
        traceInfo(`AppState: updated filters (min_level=${this._getMinLevel()}, stages=${this._getEnabledStages().join(',')})`);
    }

    /**
     * Send unsubscribe_logs message to backend.
     */
    private _sendUnsubscribeLogs(): void {
        if (!this._isSubscribedToLogs) {
            return;
        }

        this._sendWsMessage('unsubscribe_logs', {});
        this._isSubscribedToLogs = false;
        traceInfo('AppState: unsubscribed from logs');
    }

    /**
     * Request summary for a project via WebSocket.
     */
    private _requestSummary(projectPath: string): void {
        this._sendWsMessage('request_summary', { project_path: projectPath });
        traceInfo(`AppState: requested summary for ${projectPath}`);
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
        const projectChanged = this._state.selectedProjectRoot !== root;
        this._state.selectedProjectRoot = root;
        if (root) {
            const project = this._state.projects.find(p => p.root === root);
            this._state.selectedTargetNames = project?.targets.map(t => t.name) ?? [];
        } else {
            this._state.selectedTargetNames = [];
        }

        // Clear selected build when switching projects to avoid showing logs from wrong project
        if (projectChanged) {
                        this._state.selectedBuildName = null;
            this._state.selectedBuildId = null;
            this._state.currentBuildInfo = null;
            this._state.logEntries = [];
            this._state.availableStages = [];
            this._state.enabledStages = [];
            // Request summary for new project via WebSocket
            if (root && this._wsConnected) {
                this._requestSummary(root);
            }
        }

        this._emit();
    }

    setSelectedProjectRoot(root: string | null): void {
        const projectChanged = this._state.selectedProjectRoot !== root;
        this._state.selectedProjectRoot = root;

        // Clear selected build when switching projects to avoid showing logs from wrong project
        if (projectChanged) {
                        this._state.selectedBuildName = null;
            this._state.selectedBuildId = null;
            this._state.currentBuildInfo = null;
            this._state.logEntries = [];
            this._state.availableStages = [];
            this._state.enabledStages = [];
            // Request summary for new project via WebSocket
            if (root && this._wsConnected) {
                this._requestSummary(root);
            }
        }

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

    selectBuild(buildName: string | null): void {
        // Unsubscribe from previous build's logs
        this._sendUnsubscribeLogs();
        
        this._state.selectedBuildName = buildName;
        this._state.selectedBuildId = null;
        this._state.currentBuildInfo = null;
        this._state.logEntries = [];
        this._state.availableStages = [];
        this._state.enabledStages = [];

        const build = this._state.builds.find(b => b.display_name === buildName);
        if (build?.build_id) {
            this._state.selectedBuildId = build.build_id;
            this._state.isLoadingLogs = true;
            this._emit();

            // Subscribe to logs via WebSocket - backend will stream logs
            if (this._wsConnected) {
                this._sendSubscribeLogs();
            }
        } else {
            this._state.isLoadingLogs = false;
            this._emit();
        }
    }

    // --- Log viewer UI ---

    toggleLogLevel(level: LogLevel): void {
        const idx = this._state.enabledLogLevels.indexOf(level);
        if (idx >= 0) {
            this._state.enabledLogLevels = this._state.enabledLogLevels.filter(l => l !== level);
        } else {
            this._state.enabledLogLevels = [...this._state.enabledLogLevels, level];
        }
        // Send filter update to backend - it will re-stream matching logs
        this._sendUpdateFilters();
        this._emit();
    }

    toggleStage(stage: string): void {
        const idx = this._state.enabledStages.indexOf(stage);
        if (idx >= 0) {
            // Unchecking a stage - remove it from the filter list
            this._state.enabledStages = this._state.enabledStages.filter(s => s !== stage);
        } else {
            // Checking a stage - add it to the filter list
            this._state.enabledStages = [...this._state.enabledStages, stage];
        }
        // Send filter update to backend - it will re-stream matching logs
        this._sendUpdateFilters();
        this._emit();
    }

    clearStageFilters(): void {
        // Clear all stage filters - empty array means "show all stages"
        this._state.enabledStages = [];
        this._sendUpdateFilters();
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

    // --- Summary handling ---

    /**
     * Handle summary data received via WebSocket push.
     * This avoids the need for HTTP polling when WebSocket is connected.
     */
    private _handleSummaryData(data: { builds: Build[]; project_path: string }): void {
        this._state.isConnected = true;

        // Filter builds to only show those from the selected project (if any)
        let builds = data.builds || [];
        if (this._state.selectedProjectRoot) {
            builds = builds.filter(b =>
                !b.project_path || b.project_path === this._state.selectedProjectRoot
            );
        }
        this._state.builds = builds;

        // Auto-select first build if none selected
        if (!this._state.selectedBuildName && this._state.builds.length > 0) {
            this.selectBuild(this._state.builds[0].display_name);
            return;
        }

        // Update selectedBuildId if it changed
        if (this._state.selectedBuildName) {
            const currentBuild = this._state.builds.find(
                b => b.display_name === this._state.selectedBuildName
            );
            if (currentBuild && currentBuild.build_id !== this._state.selectedBuildId) {
                traceInfo(`AppState: build_id updated for ${this._state.selectedBuildName}`);
                this._state.selectedBuildId = currentBuild.build_id;
            }
        }

        this._emit();
        traceVerbose(`AppState: received summary via WebSocket with ${this._state.builds.length} builds`);
    }

    // --- WebSocket connection ---

    /**
     * Start listening for updates via WebSocket.
     */
    startListening(): void {
        this.stopListening();
        this._isListening = true;
        traceInfo('AppState: startListening() called - connecting to WebSocket');
        this._connectWebSocket();
    }

    /**
     * Stop listening for updates.
     */
    stopListening(): void {
        this._isListening = false;
        this._disconnectWebSocket();
                traceInfo('AppState: stopped listening');
    }

    /**
     * Connect to the WebSocket endpoint for real-time updates.
     */
    private _connectWebSocket(): void {
        if (this._ws) {
            traceVerbose('AppState: WebSocket already connected, skipping');
            return; // Already connected
        }

        const apiUrl = getDashboardApiUrl();
        // Convert http:// to ws:// or https:// to wss://
        const wsUrl = apiUrl.replace(/^http/, 'ws') + '/ws';
        traceInfo(`AppState: connecting to WebSocket at ${wsUrl}`);

        try {
            this._ws = new WebSocket(wsUrl);

            this._ws.on('open', () => {
                traceInfo('AppState: WebSocket connected successfully');
                this._wsConnected = true;
                this._state.isConnected = true;
                this._state.isBackendRunning = true;
                backendServer.setConnected(true);
                this._emit();
            });

            this._ws.on('message', (data: WebSocket.Data) => {
                try {
                    const message = JSON.parse(data.toString());
                    this._handleMessage(message.type, message.data);
                } catch (err) {
                    traceError(`AppState: failed to parse WebSocket message: ${err}`);
                }
            });

            this._ws.on('close', () => {
                traceInfo('AppState: WebSocket connection closed');
                this._wsConnected = false;
                this._state.isConnected = false;
                this._state.isBackendRunning = false;
                this._ws = null;
                backendServer.setConnected(false);
                this._emit();
                this._scheduleWSReconnect();
            });

            this._ws.on('error', (err: Error) => {
                if ((err as NodeJS.ErrnoException).code === 'ECONNREFUSED') {
                    traceVerbose('AppState: WebSocket connection refused (server not running?)');
                } else {
                    traceError(`AppState: WebSocket error: ${err.message}`);
                }
                this._wsConnected = false;
                this._state.isConnected = false;
                this._state.isBackendRunning = false;
                this._ws = null;
                backendServer.setConnected(false);
                this._emit();
                this._scheduleWSReconnect();
            });
        } catch (err) {
            traceError(`AppState: Failed to create WebSocket connection: ${err}`);
            this._ws = null;
            this._scheduleWSReconnect();
        }
    }

    /**
     * Disconnect from WebSocket.
     */
    private _disconnectWebSocket(): void {
        if (this._wsReconnectTimer) {
            clearTimeout(this._wsReconnectTimer);
            this._wsReconnectTimer = null;
        }

        if (this._ws) {
            this._ws.close();
            this._ws = null;
        }

        this._wsConnected = false;
        this._wsClientId = null;
        this._isSubscribedToLogs = false;
    }

    /**
     * Schedule WebSocket reconnection after a delay.
     */
    private _scheduleWSReconnect(): void {
        if (this._wsReconnectTimer) {
            return; // Already scheduled
        }

        traceVerbose('AppState: scheduling WebSocket reconnect in 2 seconds');
        this._wsReconnectTimer = setTimeout(() => {
            this._wsReconnectTimer = null;
            // Reconnect if we're still supposed to be listening
            if (!this._wsConnected && this._isListening) {
                traceVerbose('AppState: attempting WebSocket reconnect');
                this._connectWebSocket();
            } else {
                traceVerbose(`AppState: skipping WebSocket reconnect (connected=${this._wsConnected}, listening=${this._isListening})`);
            }
        }, 2000); // Reconnect after 2 seconds
    }

    /**
     * Handle a WebSocket message.
     */
    private _handleMessage(eventType: string, data: Record<string, unknown>): void {
        traceVerbose(`AppState: WebSocket message: ${eventType}`);

        switch (eventType) {
            case 'connected':
                this._wsClientId = data.client_id as string;
                traceInfo(`AppState: WebSocket client ID: ${this._wsClientId}`);
                // Request initial summary for selected project
                if (this._state.selectedProjectRoot) {
                    this._requestSummary(this._state.selectedProjectRoot);
                }
                // Re-subscribe to logs if we have a build selected
                if (this._state.selectedBuildName && this._state.selectedBuildId) {
                    this._sendSubscribeLogs();
                }
                break;

            case 'build_started': {
                const targets = data.targets as string[] | undefined;
                traceInfo(`AppState: build started - ${targets?.join(', ')} in ${data.project_path}`);

                // Check if this is for the selected project
                if (!this._state.selectedProjectRoot ||
                    data.project_path === this._state.selectedProjectRoot) {

                    // Unsubscribe from any current logs
                    this._sendUnsubscribeLogs();

                    // Clear selection - user will click a target to view logs for that build
                    // This avoids timing issues with build_id lookup before the build entry exists
                    traceInfo('AppState: clearing selection for new build - click a target to view logs');
                    this._state.selectedBuildName = null;
                    this._state.selectedBuildId = null;
                    this._state.logEntries = [];
                    this._state.availableStages = [];
                    this._state.enabledStages = [];
                    this._state.currentBuildInfo = null;
                            this._state.isLoadingLogs = false;
                    this._emit();
                }
                // Server will send summary_updated with full data shortly
                break;
            }

            case 'build_completed':
                traceInfo(`AppState: build completed - success=${data.success}`);
                // Server sends summary_updated right after this with full data
                break;

            case 'summary_updated':
                // Project summary pushed from server - use it directly
                if (!this._state.selectedProjectRoot ||
                    data.project_path === this._state.selectedProjectRoot) {
                    this._handleSummaryData(data as {
                        builds: Build[];
                        project_path: string;
                    });
                }
                break;

            case 'subscribed':
                // Subscription confirmed with build_id from server
                traceInfo(`AppState: subscribed to build_id=${data.build_id}, target=${data.target}`);
                this._state.selectedBuildId = data.build_id as string;
                this._state.currentBuildInfo = {
                    buildId: data.build_id as string,
                    projectPath: data.project_path as string,
                    target: data.target as string,
                    timestamp: (data.build_timestamp as string) || '',
                };
                this._emit();
                break;

            case 'subscription_error':
                // Subscription failed (e.g., no builds found)
                traceError(`AppState: subscription error - ${data.message}`);
                this._state.isLoadingLogs = false;
                this._isSubscribedToLogs = false;
                this._emit();
                break;

            case 'log_batch':
                // Batch of log entries from server
                this._handleLogBatch(data as {
                    logs: Array<{
                        id: number;
                        build_id: string;
                        timestamp: string;
                        stage: string;
                        level: string;
                        message: string;
                        ato_traceback?: string | null;
                        python_traceback?: string | null;
                        project_path: string;
                        target: string;
                    }>;
                    last_id: number;
                    count: number;
                });
                break;

            default:
                traceVerbose(`AppState: unknown WebSocket message type: ${eventType}`);
        }
    }

    /**
     * Handle a batch of log entries from WebSocket.
     */
    private _handleLogBatch(data: {
        logs: Array<{
            id: number;
            build_id: string;
            timestamp: string;
            stage: string;
            level: string;
            message: string;
            ato_traceback?: string | null;
            python_traceback?: string | null;
            project_path: string;
            target: string;
        }>;
        last_id: number;
        count: number;
    }): void {
        if (data.logs.length === 0) {
            return;
        }

        const firstLog = data.logs[0];

        // Update selectedBuildId if not set (happens after build_started clears it)
        if (!this._state.selectedBuildId && this._state.selectedBuildName) {
            traceInfo(`AppState: setting build_id to ${firstLog.build_id} for target ${firstLog.target}`);
            this._state.selectedBuildId = firstLog.build_id;
        }

        // Convert to LogEntry format
        const newEntries: LogEntry[] = data.logs.map(log => ({
            timestamp: log.timestamp,
            level: log.level as LogLevel,
            logger: 'atopile',
            stage: log.stage,
            message: log.message,
            ato_traceback: log.ato_traceback ?? undefined,
            exc_info: log.python_traceback ?? undefined,
        }));

        // Update available stages from this batch
        const newStages = new Set(this._state.availableStages);
        for (const log of data.logs) {
            if (log.stage && !newStages.has(log.stage)) {
                newStages.add(log.stage);
            }
        }
        if (newStages.size !== this._state.availableStages.length) {
            this._state.availableStages = Array.from(newStages);
        }

        // Update current build info
        this._state.currentBuildInfo = {
            buildId: firstLog.build_id,
            projectPath: firstLog.project_path,
            target: firstLog.target,
            timestamp: firstLog.timestamp,
        };

        // Append logs to state
        this._state.logEntries = [...this._state.logEntries, ...newEntries];
        this._state.isLoadingLogs = false;

        this._emit();
        traceVerbose(`AppState: received ${data.count} log entries (last_id=${data.last_id})`);
    }

    dispose(): void {
        this.stopListening();
        this._onStateChange.dispose();
    }
}

// Singleton instance
export const appStateManager = new AppStateManager();
