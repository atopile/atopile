/**
 * BuildStateManager - Centralized state manager for build data.
 *
 * Polls /api/summary at configurable interval, maintains build list/status/stages,
 * tracks selected build/stage for log viewing, and fires VS Code events for
 * TreeView and LogViewer to react.
 */

import * as vscode from 'vscode';
import axios from 'axios';
import { traceInfo, traceError, traceVerbose } from './log/logging';

// Types matching the build summary API
export type BuildStatus = 'queued' | 'building' | 'success' | 'warning' | 'failed';
export type StageStatus = 'success' | 'warning' | 'failed';
export type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'ALERT';

export interface LogEntry {
    timestamp: string;
    level: LogLevel;
    logger: string;
    message: string;
    ato_traceback?: string;
    exc_info?: string;
}

export interface BuildStage {
    name: string;
    elapsed_seconds: number;
    status: StageStatus;
    infos: number;
    warnings: number;
    errors: number;
    alerts: number;
    log_file?: string;
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
    stages?: BuildStage[];
}

export interface BuildTotals {
    builds: number;
    successful: number;
    failed: number;
    warnings: number;
    errors: number;
}

export interface BuildSummary {
    timestamp: string;
    totals: BuildTotals;
    builds: Build[];
    error?: string;
}

/**
 * Get the dashboard API URL from settings.
 */
function getDashboardApiUrl(): string {
    const config = vscode.workspace.getConfiguration('atopile');
    return config.get<string>('dashboardApiUrl', 'http://localhost:8501');
}

class BuildStateManager {
    private _summary: BuildSummary | null = null;
    private _isConnected: boolean = false;
    private _isPolling: boolean = false;
    private _pollInterval: number = 500;
    private _pollTimer: NodeJS.Timeout | null = null;

    private _selectedBuildName: string | null = null;
    private _selectedStageName: string | null = null;

    // Events
    private readonly _onDidChangeBuilds = new vscode.EventEmitter<BuildSummary | null>();
    public readonly onDidChangeBuilds = this._onDidChangeBuilds.event;

    private readonly _onDidChangeSelectedStage = new vscode.EventEmitter<{ build: Build; stage: BuildStage } | null>();
    public readonly onDidChangeSelectedStage = this._onDidChangeSelectedStage.event;

    private readonly _onDidChangeConnection = new vscode.EventEmitter<boolean>();
    public readonly onDidChangeConnection = this._onDidChangeConnection.event;

    // Getters
    get summary(): BuildSummary | null {
        return this._summary;
    }

    get isConnected(): boolean {
        return this._isConnected;
    }

    get isPolling(): boolean {
        return this._isPolling;
    }

    get selectedBuildName(): string | null {
        return this._selectedBuildName;
    }

    get selectedStageName(): string | null {
        return this._selectedStageName;
    }

    getBuilds(): Build[] {
        return this._summary?.builds ?? [];
    }

    getSelectedBuild(): Build | null {
        if (!this._summary || !this._selectedBuildName) return null;
        return this._summary.builds.find(b => b.display_name === this._selectedBuildName) ?? null;
    }

    getSelectedStage(): BuildStage | null {
        const build = this.getSelectedBuild();
        if (!build || !this._selectedStageName || !build.stages) return null;
        return build.stages.find(s => s.name === this._selectedStageName) ?? null;
    }

    /**
     * Fetch the build summary from the API.
     */
    async fetchSummary(): Promise<void> {
        const apiUrl = getDashboardApiUrl();

        try {
            const response = await axios.get<BuildSummary>(`${apiUrl}/api/summary`, {
                timeout: 5000,
            });

            const wasConnected = this._isConnected;
            this._isConnected = true;
            this._summary = response.data;

            if (!wasConnected) {
                this._onDidChangeConnection.fire(true);
            }

            // Auto-select first build if none selected
            if (!this._selectedBuildName && this._summary.builds.length > 0) {
                this._selectedBuildName = this._summary.builds[0].display_name;
            }

            this._onDidChangeBuilds.fire(this._summary);
            traceVerbose(`BuildState: fetched summary with ${this._summary.builds.length} builds`);
        } catch (error) {
            const wasConnected = this._isConnected;
            this._isConnected = false;

            if (wasConnected) {
                this._onDidChangeConnection.fire(false);
                traceInfo('BuildState: disconnected from API');
            }
        }
    }

    /**
     * Select a build by display name.
     */
    selectBuild(buildName: string | null): void {
        if (this._selectedBuildName === buildName) return;

        this._selectedBuildName = buildName;
        this._selectedStageName = null;
        this._onDidChangeSelectedStage.fire(null);
        this._onDidChangeBuilds.fire(this._summary);
    }

    /**
     * Select a stage by name (within the currently selected build).
     */
    selectStage(stageName: string | null): void {
        if (this._selectedStageName === stageName) return;

        this._selectedStageName = stageName;

        const build = this.getSelectedBuild();
        const stage = this.getSelectedStage();

        if (build && stage) {
            this._onDidChangeSelectedStage.fire({ build, stage });
        } else {
            this._onDidChangeSelectedStage.fire(null);
        }
    }

    /**
     * Fetch log entries for a specific build and stage.
     */
    async fetchLogEntries(buildName: string, stage: BuildStage): Promise<LogEntry[]> {
        const apiUrl = getDashboardApiUrl();

        if (!stage.log_file) {
            throw new Error('No log file available for this stage');
        }

        // Extract just the filename from the full path
        const filename = stage.log_file.split('/').pop() || stage.log_file;

        try {
            const response = await axios.get(
                `${apiUrl}/api/logs/${encodeURIComponent(buildName)}/${encodeURIComponent(filename)}`,
                { timeout: 10000 }
            );

            const content = response.data;

            // Parse JSON Lines format
            const entries: LogEntry[] = content
                .split('\n')
                .filter((line: string) => line.trim())
                .map((line: string) => {
                    try {
                        return JSON.parse(line) as LogEntry;
                    } catch {
                        return {
                            timestamp: new Date().toISOString(),
                            level: 'INFO' as const,
                            logger: 'unknown',
                            message: line,
                        };
                    }
                });

            return entries;
        } catch (error) {
            const message = error instanceof Error ? error.message : 'Unknown error';
            throw new Error(`Failed to fetch logs: ${message}`);
        }
    }

    /**
     * Start polling the API for build updates.
     */
    startPolling(interval?: number): void {
        if (this._pollTimer) {
            clearInterval(this._pollTimer);
        }

        if (interval !== undefined) {
            this._pollInterval = interval;
        }

        this._isPolling = true;
        traceInfo(`BuildState: starting polling at ${this._pollInterval}ms interval`);

        // Initial fetch
        this.fetchSummary();

        // Start polling
        this._pollTimer = setInterval(() => {
            this.fetchSummary();
        }, this._pollInterval);
    }

    /**
     * Stop polling.
     */
    stopPolling(): void {
        if (this._pollTimer) {
            clearInterval(this._pollTimer);
            this._pollTimer = null;
        }
        this._isPolling = false;
        traceInfo('BuildState: stopped polling');
    }

    /**
     * Dispose of resources.
     */
    dispose(): void {
        this.stopPolling();
        this._onDidChangeBuilds.dispose();
        this._onDidChangeSelectedStage.dispose();
        this._onDidChangeConnection.dispose();
    }
}

// Singleton instance
export const buildStateManager = new BuildStateManager();
