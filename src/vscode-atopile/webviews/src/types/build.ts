/**
 * TypeScript types for build state.
 * This is the SINGLE source of truth for all types.
 */

export type BuildStatus = 'queued' | 'building' | 'success' | 'warning' | 'failed' | 'cancelled';
export type StageStatus = 'pending' | 'running' | 'success' | 'warning' | 'failed' | 'error' | 'skipped';
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
  display_name?: string;  // User-friendly name
  elapsed_seconds: number;
  status: StageStatus;
  infos: number;
  warnings: number;
  errors: number;
  alerts: number;
}

export interface Build {
  // Core identification
  name: string;
  display_name: string;
  project_name: string | null;
  build_id?: string;  // Present for active/tracked builds

  // Status
  status: BuildStatus;
  elapsed_seconds: number;
  warnings: number;
  errors: number;
  return_code: number | null;

  // Context (present for active builds)
  project_root?: string;
  targets?: string[];
  entry?: string;
  started_at?: number;  // Unix timestamp

  // Stages and logs
  stages?: BuildStage[];
  log_dir?: string;
  log_file?: string;

  // Queue info
  queue_position?: number;  // Position in queue (1-indexed), only set when status is 'queued'
}

export interface BuildTargetStageStatus {
  name: string;  // Internal stage name
  display_name: string;  // User-friendly name
  status: StageStatus;
  elapsed_seconds?: number;
}

export interface BuildTargetStatus {
  status: BuildStatus;
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

/**
 * THE SINGLE APP STATE - All state lives here.
 * Extension owns this, webviews receive it read-only.
 */
// --- Package Types ---

export interface PackageInfo {
  identifier: string;  // e.g., "atopile/bosch-bme280"
  name: string;        // e.g., "bosch-bme280"
  publisher: string;   // e.g., "atopile"
  version?: string;    // Installed version
  latest_version?: string;  // Latest available (snake_case from backend)
  description?: string;
  summary?: string;
  homepage?: string;
  repository?: string;
  license?: string;
  installed: boolean;
  installed_in: string[];  // List of project roots where installed (snake_case from backend)
  // Package stats (from registry) - these may come from registry API later
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

// --- Standard Library Types ---

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

// --- BOM Types (from /api/bom endpoint) ---

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

export interface AppState {
  // Connection
  isConnected: boolean;

  // Projects (from ato.yaml)
  projects: Project[];
  selectedProjectRoot: string | null;
  selectedTargetNames: string[];

  // Builds from /api/summary - completed builds and project context
  builds: Build[];

  // Queued builds from /api/builds/active - display-ready for queue panel
  // Backend formats this data, frontend just renders
  queuedBuilds: Build[];

  // Packages (from dashboard API)
  packages: PackageInfo[];
  isLoadingPackages: boolean;

  // Standard Library (from dashboard API)
  stdlibItems: StdLibItem[];
  isLoadingStdlib: boolean;

  // BOM (from dashboard API /api/bom)
  bomData: BOMData | null;
  isLoadingBOM: boolean;
  bomError: string | null;

  // Package details (from /api/packages/{id}/details)
  selectedPackageDetails: PackageDetails | null;
  isLoadingPackageDetails: boolean;
  packageDetailsError: string | null;

  // Build/Log selection
  selectedBuildName: string | null;
  selectedProjectName: string | null;  // Filter logs by project (when project selected, not specific build)
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
  logCounts?: {
    DEBUG: number;
    INFO: number;
    WARNING: number;
    ERROR: number;
    ALERT: number;
  };
  logTotalCount?: number;
  logHasMore?: boolean;

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
      source: 'path' | 'venv' | 'manual';  // Where it was found
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
  problemFilter: {
    levels: ('error' | 'warning')[];
    buildNames: string[];
    stageIds: string[];
  };

  // Project modules (from /api/modules endpoint)
  // Map of project root to available modules
  projectModules: Record<string, ModuleDefinition[]>;
  isLoadingModules: boolean;

  // Variables (from /api/variables endpoint)
  // Current variables for selected project/target - frontend just displays this
  currentVariablesData: VariablesData | null;
  isLoadingVariables: boolean;
  variablesError: string | null;
}

// --- Problem Types ---

export interface Problem {
  id: string;
  level: 'error' | 'warning';
  message: string;
  file?: string;
  line?: number;
  column?: number;
  stage?: string;        // Build stage that produced this problem
  logger?: string;       // Logger name (e.g., "faebryk.libs.picker")
  buildName?: string;    // Which build target
  projectName?: string;  // Which project
  timestamp?: string;    // When it occurred
  ato_traceback?: string; // Source traceback if available
  exc_info?: string;     // Exception info if available
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

// --- Variable Types (from /api/variables endpoint) ---

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

// VS Code API type
export interface VSCodeAPI {
  postMessage(message: unknown): void;
  getState(): unknown;
  setState(state: unknown): void;
}

declare global {
  function acquireVsCodeApi(): VSCodeAPI;
}
