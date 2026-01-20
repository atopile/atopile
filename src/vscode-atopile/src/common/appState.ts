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

// Active build in the queue (from /api/builds/active)
export interface ActiveBuild {
    build_id: string;
    status: 'queued' | 'building' | 'success' | 'failed' | 'cancelled';
    project_root: string;
    targets: string[];
    entry?: string;
    started_at: number;
    elapsed_seconds?: number;
    stages?: BuildStage[];
    error?: string;
}

export interface BuildTargetStageStatus {
    name: string;  // Internal stage name
    display_name: string;  // User-friendly name
    status: string;  // 'pending', 'success', 'warning', 'error', 'skipped'
    elapsed_seconds?: number;
}

export interface BuildTargetStatus {
    status: string;  // 'success', 'warning', 'failed', 'building', 'queued'
    timestamp: string;  // ISO format timestamp of when the build completed
    elapsed_seconds?: number;
    warnings: number;
    errors: number;
    stages?: BuildTargetStageStatus[];  // Stage breakdown from last build
}

export interface BuildTarget {
    name: string;
    entry: string;
    root: string;
    last_build?: BuildTargetStatus;  // Persisted status from last build
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
    has_more: boolean;
    max_id: number;
}

// API response type for /api/logs/counts
interface LogCountsResponse {
    counts: {
        DEBUG: number;
        INFO: number;
        WARNING: number;
        ERROR: number;
        ALERT: number;
    };
    total: number;
}

// Standard Library Types
export type StdLibItemType = 'interface' | 'module' | 'component' | 'trait' | 'parameter';

export interface StdLibChild {
    name: string;
    type: string;
    item_type: StdLibItemType;
    children: StdLibChild[];
}

export interface StdLibItem {
    id: string;
    name: string;
    type: StdLibItemType;
    description: string;
    usage: string | null;
    children: StdLibChild[];
    parameters: { name: string; type: string }[];
}

// Package Types
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
    downloads?: number;
    version_count?: number;
    keywords?: string[];
}

// Package version/release info (from /api/packages/{id}/details)
export interface PackageVersion {
    version: string;
    released_at: string | null;
    requires_atopile?: string;
    size?: number;
}

// Detailed package info from registry (from /api/packages/{id}/details)
export interface PackageDetails {
    identifier: string;
    name: string;
    publisher: string;
    version: string;  // Latest version
    summary?: string;
    description?: string;
    homepage?: string;
    repository?: string;
    license?: string;
    // Stats
    downloads?: number;
    downloads_this_week?: number;
    downloads_this_month?: number;
    // Versions
    versions: PackageVersion[];
    version_count: number;
    // Installation status
    installed: boolean;
    installed_version?: string;
    installed_in: string[];
}

// BOM Types (from /api/bom endpoint)
export type BOMComponentType =
    | 'resistor' | 'capacitor' | 'inductor' | 'ic' | 'connector'
    | 'led' | 'diode' | 'transistor' | 'crystal' | 'other';

export interface BOMParameter {
    name: string;
    value: string;
    unit?: string;
}

export interface BOMUsage {
    address: string;      // Atopile address e.g., "App.power_supply.r_top"
    designator: string;   // e.g., "R1"
}

export interface BOMComponent {
    id: string;
    lcsc?: string;
    manufacturer?: string;
    mpn?: string;
    type: BOMComponentType;
    value: string;
    package: string;
    description?: string;
    quantity: number;
    unitCost?: number;
    stock?: number;
    isBasic?: boolean;
    isPreferred?: boolean;
    source: string;       // 'picked' | 'specified' | 'manual'
    parameters: BOMParameter[];
    usages: BOMUsage[];
}

export interface BOMData {
    version: string;
    components: BOMComponent[];
}

// Problem Types
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
    exc_info?: string;
}

export interface ProblemFilter {
    levels: ('error' | 'warning')[];
    buildNames: string[];
    stageIds: string[];
}

// Module Definition Types (from /api/modules endpoint)
export interface ModuleDefinition {
    name: string;
    type: 'module' | 'interface' | 'component';
    file: string;
    entry: string;
    line?: number;
    super_type?: string;
}

// Variable Types (from /api/variables endpoint)
export type VariableType = 'voltage' | 'current' | 'resistance' | 'capacitance' | 'ratio' | 'frequency' | 'power' | 'percentage' | 'dimensionless';
export type VariableSource = 'user' | 'derived' | 'picked' | 'datasheet';

export interface Variable {
    name: string;
    spec?: string;
    specTolerance?: string;
    actual?: string;
    actualTolerance?: string;
    unit?: string;
    type: VariableType;
    meetsSpec?: boolean;
    source?: VariableSource;
}

export interface VariableNode {
    name: string;
    type: 'module' | 'interface' | 'component';
    path: string;
    typeName?: string;
    variables?: Variable[];
    children?: VariableNode[];
}

export interface VariablesData {
    version: string;
    nodes: VariableNode[];
}

// File Tree Types (from /api/files endpoint)
export interface FileTreeNode {
    name: string;
    path: string;
    type: 'file' | 'folder';
    extension?: string;  // 'ato' | 'py'
    children?: FileTreeNode[];
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

    // Builds (from dashboard API summary)
    builds: Build[];

    // Active builds in queue (from /api/builds/active)
    activeBuilds: ActiveBuild[];

    // Standard Library
    stdlibItems: StdLibItem[];
    isLoadingStdlib: boolean;

    // Packages
    packages: PackageInfo[];
    isLoadingPackages: boolean;
    packagesError: string | null;  // Exposed for UI error display (e.g., registry unavailable)

    // BOM (Bill of Materials)
    bomData: BOMData | null;
    isLoadingBOM: boolean;
    bomError: string | null;

    // Package Details (from /api/packages/{id}/details)
    selectedPackageDetails: PackageDetails | null;
    isLoadingPackageDetails: boolean;
    packageDetailsError: string | null;

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

    // Log counts (from /api/logs/counts for efficient badge display)
    logCounts: {
        DEBUG: number;
        INFO: number;
        WARNING: number;
        ERROR: number;
        ALERT: number;
    };
    logTotalCount: number;
    logHasMore: boolean;

    // Sidebar UI
    expandedTargets: string[];

    // Extension info
    version: string;
    logoUri: string;

    // Atopile configuration
    atopile: {
        currentVersion: string;           // Currently active version (e.g., "0.14.0")
        source: 'release' | 'branch' | 'local';  // Source type
        localPath: string | null;         // Local path when source is 'local'
        branch: string | null;            // Git branch when source is 'branch'
        availableVersions: string[];      // List of versions from PyPI
        availableBranches: string[];      // List of branches from GitHub
        detectedInstallations: {          // Local installations found on system
            path: string;
            version: string | null;
            source: 'path' | 'venv' | 'manual';
        }[];
        isInstalling: boolean;            // Installation in progress
        installProgress: {                // Progress info during install
            message: string;
            percent?: number;
        } | null;
        error: string | null;             // Any error message
    };

    // Problems/diagnostics (parsed from log files)
    problems: Problem[];
    isLoadingProblems: boolean;
    problemFilter: ProblemFilter;

    // Project modules (from /api/modules endpoint)
    // Map of project root to available modules
    projectModules: Record<string, ModuleDefinition[]>;
    isLoadingModules: boolean;

    // Project files (from /api/files endpoint)
    // Map of project root to file tree (.ato and .py files)
    projectFiles: Record<string, FileTreeNode[]>;
    isLoadingFiles: boolean;

    // Variables (from /api/variables endpoint)
    // Current variables for selected project/target - frontend just displays this
    currentVariablesData: VariablesData | null;
    isLoadingVariables: boolean;
    variablesError: string | null;
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

        // Active builds in queue
        activeBuilds: [],

        // Standard Library
        stdlibItems: [],
        isLoadingStdlib: false,

        // Packages
        packages: [],
        isLoadingPackages: false,
        packagesError: null,

        // BOM
        bomData: null,
        isLoadingBOM: false,
        bomError: null,

        // Package Details
        selectedPackageDetails: null,
        isLoadingPackageDetails: false,
        packageDetailsError: null,

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

        // Log counts (from server)
        logCounts: { DEBUG: 0, INFO: 0, WARNING: 0, ERROR: 0, ALERT: 0 },
        logTotalCount: 0,
        logHasMore: false,

        // Sidebar UI
        expandedTargets: [],

        // Extension info
        version: '',
        logoUri: '',

        // Atopile configuration
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

        // Problems
        problems: [],
        isLoadingProblems: false,
        problemFilter: {
            levels: ['error', 'warning'],
            buildNames: [],
            stageIds: [],
        },

        // Project modules
        projectModules: {},
        isLoadingModules: false,

        // Project files
        projectFiles: {},
        isLoadingFiles: false,

        // Variables
        currentVariablesData: null,
        isLoadingVariables: false,
        variablesError: null,
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

    // --- Atopile configuration ---

    setAtopileVersion(version: string): void {
        this._state.atopile.currentVersion = version;
        this._emit();
    }

    setAtopileSource(source: 'release' | 'branch' | 'local'): void {
        this._state.atopile.source = source;
        this._emit();
    }

    setAtopileLocalPath(path: string | null): void {
        this._state.atopile.localPath = path;
        this._emit();
    }

    setAtopileBranch(branch: string | null): void {
        this._state.atopile.branch = branch;
        this._emit();
    }

    setAtopileAvailableVersions(versions: string[]): void {
        this._state.atopile.availableVersions = versions;
        this._emit();
    }

    setAtopileAvailableBranches(branches: string[]): void {
        this._state.atopile.availableBranches = branches;
        this._emit();
    }

    setAtopileDetectedInstallations(installations: { path: string; version: string | null; source: 'path' | 'venv' | 'manual' }[]): void {
        this._state.atopile.detectedInstallations = installations;
        this._emit();
    }

    setAtopileInstalling(installing: boolean, progress?: { message: string; percent?: number }): void {
        this._state.atopile.isInstalling = installing;
        this._state.atopile.installProgress = progress ?? null;
        if (!installing) {
            this._state.atopile.error = null;
        }
        this._emit();
    }

    setAtopileError(error: string | null): void {
        this._state.atopile.error = error;
        this._state.atopile.isInstalling = false;
        this._state.atopile.installProgress = null;
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
        const changed = this._state.selectedProjectRoot !== root;
        this._state.selectedProjectRoot = root;
        this._emit();
        // Auto-fetch variables when selection changes
        if (changed && root) {
            const target = this._state.selectedTargetNames[0] || 'default';
            this.fetchVariables(root, target);
        }
    }

    setSelectedTargetNames(names: string[]): void {
        const changed = JSON.stringify(this._state.selectedTargetNames) !== JSON.stringify(names);
        this._state.selectedTargetNames = names;
        this._emit();
        // Auto-fetch variables when selection changes
        if (changed && this._state.selectedProjectRoot && names.length > 0) {
            this.fetchVariables(this._state.selectedProjectRoot, names[0]);
        }
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

        // If null (All builds), fetch logs from all builds
        if (buildName === null) {
            this._state.isLoadingLogs = true;
            this._emit();
            await this._startPollingLogs(null);
            return;
        }

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
        // Trigger server refresh with new stage filter
        this._triggerLogRefresh();
    }

    clearStageFilter(): void {
        this._state.selectedStageIds = [];
        this._emit();
        // Trigger server refresh with new filter
        this._triggerLogRefresh();
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
        // Trigger server refresh with new level filter
        this._triggerLogRefresh();
    }

    setLogSearchQuery(query: string): void {
        this._state.logSearchQuery = query;
        this._emit();

        // Debounce search queries to avoid hammering the server
        if (this._searchDebounceTimer) {
            clearTimeout(this._searchDebounceTimer);
        }

        // Only trigger refresh if search actually changed
        if (query !== this._lastSearchQuery) {
            this._searchDebounceTimer = setTimeout(() => {
                this._lastSearchQuery = query;
                this._triggerLogRefresh();
            }, 300);  // 300ms debounce
        }
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
            // Fetch both summary and active builds in parallel
            const [summaryResponse, activeResponse] = await Promise.all([
                axios.get<BuildSummary>(`${apiUrl}/api/summary`, { timeout: 5000 }),
                axios.get<{ builds: ActiveBuild[] }>(`${apiUrl}/api/builds/active`, { timeout: 5000 }).catch(() => ({ data: { builds: [] } })),
            ]);

            const newBuilds = summaryResponse.data.builds || [];
            const newActiveBuilds = activeResponse.data.builds || [];

            // Only emit if data actually changed to avoid unnecessary re-renders
            const buildsChanged = JSON.stringify(newBuilds) !== JSON.stringify(this._state.builds);
            const activeBuildsChanged = JSON.stringify(newActiveBuilds) !== JSON.stringify(this._state.activeBuilds);
            const connectionChanged = !this._state.isConnected;

            // Detect builds that just completed (transitioned from building to success/warning/failed)
            const completedBuilds: Build[] = [];
            for (const newBuild of newBuilds) {
                const oldBuild = this._state.builds.find(b => b.display_name === newBuild.display_name);
                if (oldBuild?.status === 'building' &&
                    (newBuild.status === 'success' || newBuild.status === 'warning' || newBuild.status === 'failed')) {
                    completedBuilds.push(newBuild);
                }
            }

            this._state.isConnected = true;
            this._state.builds = newBuilds;
            this._state.activeBuilds = newActiveBuilds;

            // Note: No auto-selection of builds - let users manually select
            // to avoid overriding "All" selection or user preferences

            // Only emit if something actually changed
            if (buildsChanged || activeBuildsChanged || connectionChanged) {
                this._emit();
                traceVerbose(`AppState: fetched summary with ${this._state.builds.length} builds, ${this._state.activeBuilds.length} active (changed: ${buildsChanged || activeBuildsChanged})`);
            }

            // Auto-fetch variables for completed builds (only if it's the selected project)
            for (const build of completedBuilds) {
                traceInfo(`AppState: build "${build.display_name}" completed, refreshing variables`);
                // Find the project root from matching project
                const project = this._state.projects.find(p =>
                    p.targets.some(t => t.name === build.name)
                );
                if (project && project.root === this._state.selectedProjectRoot) {
                    // Refresh variables for the completed build
                    this.fetchVariables(project.root, build.name);
                    // Also refresh problems
                    this.fetchProblems();
                }
            }
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

    // --- Standard Library ---

    async fetchStdlib(forceRefresh: boolean = false): Promise<void> {
        const apiUrl = getDashboardApiUrl();

        // Skip if already loaded and not forcing refresh
        if (this._state.stdlibItems.length > 0 && !forceRefresh) {
            return;
        }

        this._state.isLoadingStdlib = true;
        this._emit();

        try {
            const params = forceRefresh ? '?refresh=true' : '';
            const response = await axios.get<{ items: StdLibItem[]; total: number }>(
                `${apiUrl}/api/stdlib${params}`,
                { timeout: 30000 } // stdlib can take a while to load
            );
            this._state.stdlibItems = response.data.items || [];
            this._state.isLoadingStdlib = false;
            this._emit();
            traceInfo(`AppState: loaded ${this._state.stdlibItems.length} stdlib items`);
        } catch (error) {
            traceError(`AppState: failed to fetch stdlib: ${error}`);
            this._state.isLoadingStdlib = false;
            this._emit();
        }
    }

    // --- Packages ---

    /**
     * Fetch packages from the unified /api/packages/summary endpoint.
     *
     * This is the SINGLE call for the packages panel. The backend handles:
     * - Merging installed packages with registry metadata
     * - Pre-computing has_update flag
     * - Reporting registry status for error visibility
     *
     * No merge logic needed here - backend provides display-ready data.
     */
    async fetchPackages(forceRefresh: boolean = false): Promise<void> {
        const apiUrl = getDashboardApiUrl();

        // Skip if already loaded and not forcing refresh
        if (this._state.packages.length > 0 && !forceRefresh) {
            return;
        }

        this._state.isLoadingPackages = true;
        this._state.packagesError = null;
        this._emit();

        try {
            // Get workspace paths for the request
            const workspaceFolders = vscode.workspace.workspaceFolders;
            const pathsParam = workspaceFolders
                ? `?paths=${encodeURIComponent(workspaceFolders.map(f => f.uri.fsPath).join(','))}`
                : '';

            // SINGLE CALL - backend does all merging
            const response = await axios.get<{
                packages: PackageInfo[];
                total: number;
                installed_count: number;
                registry_status: { available: boolean; error: string | null };
            }>(
                `${apiUrl}/api/packages/summary${pathsParam}`,
                { timeout: 15000 }
            );

            this._state.packages = response.data.packages || [];
            this._state.isLoadingPackages = false;

            // Expose registry status for UI feedback
            if (!response.data.registry_status.available) {
                this._state.packagesError = response.data.registry_status.error;
            } else {
                this._state.packagesError = null;
            }

            this._emit();
            traceInfo(`AppState: loaded ${this._state.packages.length} packages (${response.data.installed_count} installed)`);
        } catch (error) {
            traceError(`AppState: failed to fetch packages: ${error}`);
            this._state.isLoadingPackages = false;
            this._state.packagesError = 'Failed to fetch packages';
            this._emit();
        }
    }

    // --- BOM (Bill of Materials) ---

    async fetchBOM(projectRoot?: string, target: string = 'default'): Promise<void> {
        const apiUrl = getDashboardApiUrl();

        // Use provided projectRoot or fall back to selected project
        const root = projectRoot || this._state.selectedProjectRoot;
        if (!root) {
            traceInfo('AppState: no project root for BOM fetch');
            return;
        }

        this._state.isLoadingBOM = true;
        this._state.bomError = null;
        this._emit();

        try {
            const response = await axios.get<BOMData>(
                `${apiUrl}/api/bom`,
                {
                    params: { project_root: root, target },
                    timeout: 15000,
                }
            );

            this._state.bomData = response.data;
            this._state.isLoadingBOM = false;
            this._state.bomError = null;
            this._emit();
            traceInfo(`AppState: loaded BOM with ${response.data.components?.length || 0} components`);
        } catch (error: any) {
            const errorMessage = error.response?.data?.detail || error.message || 'Failed to fetch BOM';
            traceError(`AppState: failed to fetch BOM: ${errorMessage}`);
            this._state.bomData = null;
            this._state.isLoadingBOM = false;
            this._state.bomError = errorMessage;
            this._emit();
        }
    }

    clearBOM(): void {
        this._state.bomData = null;
        this._state.bomError = null;
        this._emit();
    }

    // --- Package Details ---

    async fetchPackageDetails(packageId: string): Promise<void> {
        const apiUrl = getDashboardApiUrl();

        this._state.isLoadingPackageDetails = true;
        this._state.packageDetailsError = null;
        this._emit();

        try {
            // Include workspace paths to check installation status
            const workspaceFolders = vscode.workspace.workspaceFolders;
            const pathsParam = workspaceFolders
                ? `?paths=${encodeURIComponent(workspaceFolders.map(f => f.uri.fsPath).join(','))}`
                : '';

            // Note: Don't encode the packageId as it contains a slash (e.g., "atopile/bosch-bme280")
            // and FastAPI expects the path format, not URL-encoded
            const response = await axios.get<PackageDetails>(
                `${apiUrl}/api/packages/${packageId}/details${pathsParam}`,
                { timeout: 15000 }
            );

            this._state.selectedPackageDetails = response.data;
            this._state.isLoadingPackageDetails = false;
            this._emit();
            traceInfo(`AppState: loaded package details for ${packageId}: ${response.data.version_count} versions`);
        } catch (error: any) {
            const errorMessage = error.response?.data?.detail || error.message || 'Failed to fetch package details';
            traceError(`AppState: failed to fetch package details: ${errorMessage}`);
            this._state.selectedPackageDetails = null;
            this._state.isLoadingPackageDetails = false;
            this._state.packageDetailsError = errorMessage;
            this._emit();
        }
    }

    clearPackageDetails(): void {
        this._state.selectedPackageDetails = null;
        this._state.packageDetailsError = null;
        this._emit();
    }

    // --- Problems ---

    async fetchProblems(): Promise<void> {
        const apiUrl = getDashboardApiUrl();

        this._state.isLoadingProblems = true;
        this._emit();

        try {
            const response = await axios.get<{ problems: Problem[] }>(
                `${apiUrl}/api/problems`,
                { timeout: 10000 }
            );

            this._state.problems = response.data.problems || [];
            this._state.isLoadingProblems = false;
            this._emit();
            traceInfo(`AppState: loaded ${this._state.problems.length} problems`);
        } catch (error) {
            traceError(`AppState: failed to fetch problems: ${error}`);
            // Fallback: parse problems from log entries in state
            this._parseProblemsFromLogEntries();
            this._state.isLoadingProblems = false;
            this._emit();
        }
    }

    private _parseProblemsFromLogEntries(): void {
        // Parse problems from current log entries
        const problems: Problem[] = [];
        let problemId = 0;

        for (const entry of this._state.logEntries) {
            if (entry.level === 'WARNING' || entry.level === 'ERROR' || entry.level === 'ALERT') {
                // Parse source location from ato_traceback if available
                let file: string | undefined;
                let line: number | undefined;
                let column: number | undefined;

                if (entry.ato_traceback) {
                    // Parse traceback format like: File "path/to/file.ato", line 23, column 8
                    const match = entry.ato_traceback.match(/File "([^"]+)", line (\d+)(?:, column (\d+))?/);
                    if (match) {
                        file = match[1];
                        line = parseInt(match[2], 10);
                        column = match[3] ? parseInt(match[3], 10) : undefined;
                    }
                }

                problems.push({
                    id: `log-${problemId++}`,
                    level: entry.level === 'WARNING' ? 'warning' : 'error',
                    message: entry.message,
                    file,
                    line,
                    column,
                    stage: entry.stage,
                    logger: entry.logger,
                    buildName: this._state.selectedBuildName || undefined,
                    timestamp: entry.timestamp,
                    ato_traceback: entry.ato_traceback,
                    exc_info: entry.exc_info,
                });
            }
        }

        this._state.problems = problems;
    }

    setProblems(problems: Problem[]): void {
        this._state.problems = problems;
        this._emit();
    }

    setProblemFilter(filter: Partial<ProblemFilter>): void {
        this._state.problemFilter = { ...this._state.problemFilter, ...filter };
        this._emit();
    }

    toggleProblemLevelFilter(level: 'error' | 'warning'): void {
        const idx = this._state.problemFilter.levels.indexOf(level);
        if (idx >= 0) {
            this._state.problemFilter.levels = this._state.problemFilter.levels.filter(l => l !== level);
        } else {
            this._state.problemFilter.levels = [...this._state.problemFilter.levels, level];
        }
        this._emit();
    }

    clearProblemFilter(): void {
        this._state.problemFilter = {
            levels: ['error', 'warning'],
            buildNames: [],
            stageIds: [],
        };
        this._emit();
    }

    // --- Project Modules ---

    async fetchModules(projectRoot: string, forceRefresh: boolean = false): Promise<ModuleDefinition[]> {
        const apiUrl = getDashboardApiUrl();

        // Check cache first (unless forcing refresh)
        if (!forceRefresh && this._state.projectModules[projectRoot]) {
            return this._state.projectModules[projectRoot];
        }

        this._state.isLoadingModules = true;
        this._emit();

        try {
            const response = await axios.get<{ modules: ModuleDefinition[]; total: number }>(
                `${apiUrl}/api/modules`,
                {
                    params: { project_root: projectRoot },
                    timeout: 15000,
                }
            );

            const modules = response.data.modules || [];

            // Cache the modules for this project
            this._state.projectModules = {
                ...this._state.projectModules,
                [projectRoot]: modules,
            };
            this._state.isLoadingModules = false;
            this._emit();
            traceInfo(`AppState: loaded ${modules.length} modules for project ${projectRoot}`);
            return modules;
        } catch (error) {
            traceError(`AppState: failed to fetch modules: ${error}`);
            this._state.isLoadingModules = false;
            this._emit();
            return [];
        }
    }

    getModulesForProject(projectRoot: string): ModuleDefinition[] {
        return this._state.projectModules[projectRoot] || [];
    }

    clearModulesCache(): void {
        this._state.projectModules = {};
        this._emit();
    }

    // --- Project Files ---

    async fetchFiles(projectRoot: string, forceRefresh: boolean = false): Promise<FileTreeNode[]> {
        const apiUrl = getDashboardApiUrl();

        // Check cache first (unless forcing refresh)
        if (!forceRefresh && this._state.projectFiles[projectRoot]) {
            return this._state.projectFiles[projectRoot];
        }

        this._state.isLoadingFiles = true;
        this._emit();

        try {
            const response = await axios.get<{ files: FileTreeNode[]; total: number }>(
                `${apiUrl}/api/files`,
                {
                    params: { project_root: projectRoot },
                    timeout: 15000,
                }
            );

            const files = response.data.files || [];

            // Cache the files for this project
            this._state.projectFiles = {
                ...this._state.projectFiles,
                [projectRoot]: files,
            };
            this._state.isLoadingFiles = false;
            this._emit();
            traceInfo(`AppState: loaded ${files.length} file tree nodes for project ${projectRoot}`);
            return files;
        } catch (error) {
            traceError(`AppState: failed to fetch files: ${error}`);
            this._state.isLoadingFiles = false;
            this._emit();
            return [];
        }
    }

    getFilesForProject(projectRoot: string): FileTreeNode[] {
        return this._state.projectFiles[projectRoot] || [];
    }

    clearFilesCache(): void {
        this._state.projectFiles = {};
        this._emit();
    }

    // --- Variables ---

    async fetchVariables(projectRoot: string, target: string = 'default'): Promise<VariablesData | null> {
        const apiUrl = getDashboardApiUrl();

        this._state.isLoadingVariables = true;
        this._state.variablesError = null;
        this._emit();

        try {
            const response = await axios.get<VariablesData>(
                `${apiUrl}/api/variables`,
                {
                    params: { project_root: projectRoot, target },
                    timeout: 15000,
                }
            );

            this._state.currentVariablesData = response.data;
            this._state.isLoadingVariables = false;
            this._state.variablesError = null;
            this._emit();
            traceInfo(`AppState: loaded variables for ${projectRoot}:${target} with ${response.data.nodes?.length || 0} nodes`);
            return response.data;
        } catch (error: any) {
            const errorMessage = error.response?.status === 404
                ? 'Variables not found. Run "ato build" first.'
                : error.response?.data?.detail || error.message || 'Failed to fetch variables';
            traceError(`AppState: failed to fetch variables: ${errorMessage}`);
            this._state.currentVariablesData = null;
            this._state.isLoadingVariables = false;
            this._state.variablesError = errorMessage;
            this._emit();
            return null;
        }
    }

    clearVariables(): void {
        this._state.currentVariablesData = null;
        this._state.variablesError = null;
        this._emit();
    }

    // --- Log API polling ---

    // Debounce timer for search queries
    private _searchDebounceTimer: NodeJS.Timeout | null = null;
    private _lastSearchQuery: string = '';

    /**
     * Fetch logs with server-side filtering.
     * Passes enabled levels, stage filter, and search query to the backend.
     */
    private async _fetchLogs(buildName: string | null, incremental: boolean = false): Promise<void> {
        const apiUrl = getDashboardApiUrl();

        try {
            // Build query params with current filter state
            const params: Record<string, string | number | undefined> = {
                limit: 500,  // Reduced from 10000 - server now filters
            };

            // Only include build_name if specified (null = all builds)
            if (buildName) {
                params.build_name = buildName;
            }

            // Pass enabled levels to server
            if (this._state.enabledLogLevels.length > 0 && this._state.enabledLogLevels.length < 5) {
                params.levels = this._state.enabledLogLevels.join(',');
            }

            // Pass stage filter if set
            if (this._state.selectedStageIds.length > 0) {
                params.stage = this._state.selectedStageIds[0];
            }

            // Pass search query (debounced)
            if (this._state.logSearchQuery.trim()) {
                params.search = this._state.logSearchQuery.trim();
            }

            // For incremental polling, only fetch new logs
            if (incremental && this._lastLogId > 0) {
                params.after_id = this._lastLogId;
            }

            const response = await axios.get<LogQueryResponse>(
                `${apiUrl}/api/logs/query`,
                { params, timeout: 5000 }
            );

            // Convert API response to LogEntry format
            const newEntries: LogEntry[] = response.data.logs
                .map(log => ({
                    timestamp: log.timestamp,
                    level: log.level as LogLevel,
                    logger: 'atopile',
                    stage: log.stage,
                    message: log.message,
                    ato_traceback: log.ato_traceback ?? undefined,
                    exc_info: log.python_traceback ?? undefined,
                }));

            // For incremental updates, append to existing; otherwise replace
            if (incremental && this._lastLogId > 0 && newEntries.length > 0) {
                // Append new entries (they're in ASC order from server when using after_id)
                this._state.logEntries = [...this._state.logEntries, ...newEntries];
            } else if (!incremental) {
                // Full refresh - reverse to get chronological order for display
                this._state.logEntries = newEntries.reverse();
            }

            // Update tracking
            this._lastLogId = response.data.max_id || this._lastLogId;
            this._state.logTotalCount = response.data.total;
            this._state.logHasMore = response.data.has_more;
            this._state.isLoadingLogs = false;

            this._emit();
            traceVerbose(`AppState: fetched ${newEntries.length} log entries for ${buildName} (total: ${response.data.total}, incremental: ${incremental})`);
        } catch (error) {
            traceError(`AppState: failed to fetch logs: ${error}`);
            this._state.isLoadingLogs = false;
            this._emit();
        }
    }

    /**
     * Fetch log counts by level for UI badges.
     * Much more efficient than fetching all logs.
     */
    private async _fetchLogCounts(buildName: string | null): Promise<void> {
        const apiUrl = getDashboardApiUrl();

        try {
            const params: Record<string, string | undefined> = {};

            // Only include build_name if specified (null = all builds)
            if (buildName) {
                params.build_name = buildName;
            }

            // Pass stage filter if set
            if (this._state.selectedStageIds.length > 0) {
                params.stage = this._state.selectedStageIds[0];
            }

            const response = await axios.get<LogCountsResponse>(
                `${apiUrl}/api/logs/counts`,
                { params, timeout: 3000 }
            );

            this._state.logCounts = response.data.counts;
            // Don't emit here - we'll emit after fetching logs
        } catch (error) {
            traceError(`AppState: failed to fetch log counts: ${error}`);
        }
    }

    private async _startPollingLogs(buildName: string | null): Promise<void> {
        // Initial fetch (full refresh)
        await Promise.all([
            this._fetchLogs(buildName, false),
            this._fetchLogCounts(buildName),
        ]);

        // Start polling for incremental updates
        this._logPollTimer = setInterval(async () => {
            if (this._state.selectedBuildName === buildName) {
                // Use incremental fetch for polling
                await this._fetchLogs(buildName, true);
            }
        }, 1000);  // Reduced frequency since server does filtering

        traceInfo(`AppState: started polling logs for ${buildName}`);
    }

    private _stopPollingLogs(): void {
        if (this._logPollTimer) {
            clearInterval(this._logPollTimer);
            this._logPollTimer = null;
        }
        if (this._searchDebounceTimer) {
            clearTimeout(this._searchDebounceTimer);
            this._searchDebounceTimer = null;
        }
        this._lastLogId = 0;
        this._lastSearchQuery = '';
    }

    /**
     * Trigger a log refresh when filters change.
     * Called when level filters, stage filters, or search query change.
     */
    private _triggerLogRefresh(): void {
        // Trigger for specific build or all builds (null)
        if (this._state.selectedBuildName !== undefined) {
            // Reset for full refresh with new filters
            this._lastLogId = 0;
            this._state.isLoadingLogs = true;
            this._emit();
            this._fetchLogs(this._state.selectedBuildName, false);
            this._fetchLogCounts(this._state.selectedBuildName);
        }
    }

    dispose(): void {
        this.stopPolling();
        this._onStateChange.dispose();
    }
}

// Singleton instance
export const appStateManager = new AppStateManager();
