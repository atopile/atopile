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
  atoTraceback?: string;
  excInfo?: string;
}

export interface BuildStage {
  name: string;
  stageId: string;
  displayName?: string;  // User-friendly name
  elapsedSeconds: number;
  status: StageStatus;
  infos: number;
  warnings: number;
  errors: number;
  alerts: number;
}

export interface Build {
  // Core identification
  name: string;
  displayName: string;
  projectName: string | null;
  buildId?: string;  // Present for active/tracked builds

  // Status
  status: BuildStatus;
  elapsedSeconds: number;
  warnings: number;
  errors: number;
  returnCode: number | null;
  error?: string;  // Error message from build failure

  // Context (present for active builds)
  projectRoot?: string;
  targets?: string[];
  entry?: string;
  startedAt?: number;  // Unix timestamp

  // Stages and logs
  stages?: BuildStage[];
  // TODO: Replace this estimate once builds are defined in the graph
  // This is the expected total number of stages for progress calculation
  totalStages?: number;  // Default: 14 (from backend estimate)
  logDir?: string;
  logFile?: string;

  // Queue info
  queuePosition?: number;  // Position in queue (1-indexed), only set when status is 'queued'
}

export interface BuildTargetStageStatus {
  name: string;  // Internal stage name
  displayName: string;  // User-friendly name
  status: StageStatus;
  elapsedSeconds?: number;
}

export interface BuildTargetStatus {
  status: BuildStatus;
  timestamp: string;  // ISO format timestamp of when the build completed
  elapsedSeconds?: number;
  warnings: number;
  errors: number;
  stages?: BuildTargetStageStatus[];  // Stage breakdown from last build
}

export interface BuildTarget {
  name: string;
  entry: string;
  root: string;
  lastBuild?: BuildTargetStatus;  // Persisted status from last build
}

// Dependency info (from ato.yaml)
export interface ProjectDependency {
  identifier: string;  // e.g., "atopile/resistors"
  version: string;     // Installed version
  latestVersion?: string;  // Latest available version
  name: string;        // e.g., "resistors"
  publisher: string;   // e.g., "atopile"
  repository?: string;
  hasUpdate?: boolean;
}

export interface Project {
  root: string;
  name: string;
  targets: BuildTarget[];
  dependencies?: ProjectDependency[];  // Project dependencies from ato.yaml
}

/**
 * THE SINGLE APP STATE - All state lives here.
 * UI server owns this; it is synced from the backend.
 */
// --- Package Types ---

export interface PackageInfo {
  identifier: string;  // e.g., "atopile/bosch-bme280"
  name: string;        // e.g., "bosch-bme280"
  publisher: string;   // e.g., "atopile"
  version?: string;    // Installed version
  latestVersion?: string;  // Latest available (camelCase from backend)
  description?: string;
  summary?: string;
  homepage?: string;
  repository?: string;
  license?: string;
  installed: boolean;
  installedIn: string[];  // List of project roots where installed (camelCase from backend)
  hasUpdate?: boolean;
  // Package stats (from registry) - these may come from registry API later
  downloads?: number;
  versionCount?: number;
  keywords?: string[];
}

// Package version/release info (from /api/packages/{id}/details)
export interface PackageVersion {
  version: string;
  releasedAt: string | null;
  requiresAtopile?: string;
  size?: number;
}

// Package dependency info
export interface PackageDependency {
  identifier: string;
  version?: string;
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
  downloadsThisWeek?: number;
  downloadsThisMonth?: number;
  // Versions
  versions: PackageVersion[];
  versionCount: number;
  // Installation status
  installed: boolean;
  installedVersion?: string;
  installedIn: string[];
  // Dependencies
  dependencies?: PackageDependency[];
}

// --- Package Summary Types (from /api/packages/summary) ---

/**
 * Display-ready package info from the unified packages endpoint.
 * Backend merges installed + registry data and pre-computes hasUpdate.
 */
export interface PackageSummaryItem {
  identifier: string;  // e.g., "atopile/bosch-bme280"
  name: string;        // e.g., "bosch-bme280"
  publisher: string;   // e.g., "atopile"

  // Installation status (matches PackageInfo field names)
  installed: boolean;
  version?: string;  // Installed version (same as PackageInfo.version)
  installedIn: string[];

  // Registry info (pre-merged by backend)
  latestVersion?: string;
  hasUpdate: boolean;  // Pre-computed: version < latestVersion

  // Display metadata
  summary?: string;
  description?: string;
  homepage?: string;
  repository?: string;
  license?: string;

  // Stats
  downloads?: number;
  versionCount?: number;
  keywords?: string[];
}

/**
 * Registry connection status for error visibility.
 */
export interface RegistryStatus {
  available: boolean;
  error: string | null;
}

/**
 * Response from /api/packages/summary endpoint.
 */
export interface PackagesSummaryResponse {
  packages: PackageSummaryItem[];
  total: number;
  installedCount: number;
  registryStatus: RegistryStatus;
}

// --- Standard Library Types ---

export type StdLibItemType = 'interface' | 'module' | 'component' | 'trait' | 'parameter';

export interface StdLibChild {
  name: string;
  type: string;
  itemType: StdLibItemType;
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
  build_id?: string;  // Build ID that produced this BOM (links to build history)
  components: BOMComponent[];
}

export interface LcscPartPrice {
  qFrom: number | null;
  qTo: number | null;
  price: number;
}

export interface LcscPartData {
  lcsc: string;
  manufacturer: string;
  mpn: string;
  package: string;
  description: string;
  datasheet_url: string;
  stock: number;
  unit_cost: number;
  is_basic: boolean;
  is_preferred: boolean;
  price: LcscPartPrice[];
}

export interface LcscPartsResponse {
  parts: Record<string, LcscPartData | null>;
}

export interface AppState {
  // Connection
  isConnected: boolean;

  // Projects (from ato.yaml)
  projects: Project[];
  isLoadingProjects: boolean;
  projectsError: string | null;
  selectedProjectRoot: string | null;
  selectedTargetNames: string[];

  // Builds from /api/summary - completed builds and project context
  builds: Build[];

  // Queued builds from /api/builds/active - display-ready for queue panel
  // Backend formats this data, frontend just renders
  queuedBuilds: Build[];

  // Packages (from dashboard API /api/packages/summary)
  packages: PackageInfo[];
  isLoadingPackages: boolean;
  packagesError: string | null;  // Registry error visibility
  installingPackageIds: string[];  // Packages currently being installed
  installError: string | null;  // Error from last install attempt

  // Standard Library (from dashboard API)
  stdlibItems: StdLibItem[];
  isLoadingStdlib: boolean;

  // BOM (from dashboard API /api/bom)
  // Note: Python camelCase converts is_loading_bom to isLoadingBom (not isLoadingBOM)
  bomData: BOMData | null;
  isLoadingBom: boolean;
  bomError: string | null;

  // Package details (from /api/packages/{id}/details)
  selectedPackageDetails: PackageDetails | null;
  isLoadingPackageDetails: boolean;
  packageDetailsError: string | null;

  // Build selection
  selectedBuildId: string | null;  // Primary identifier for selected build
  selectedBuildName: string | null;  // For display/backwards compatibility
  selectedProjectName: string | null;

  // Sidebar UI
  expandedTargets: string[];

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

  // Developer mode - shows all log audiences instead of just 'user'
  developerMode: boolean;

  // Project modules (from /api/modules endpoint)
  // Map of project root to available modules
  projectModules: Record<string, ModuleDefinition[]>;
  isLoadingModules: boolean;

  // Project files (from /api/files endpoint)
  // Map of project root to file tree (.ato and .py files)
  projectFiles: Record<string, FileTreeNode[]>;
  isLoadingFiles: boolean;

  // Project dependencies (from ato.yaml)
  // Map of project root to dependencies list
  projectDependencies: Record<string, ProjectDependency[]>;
  isLoadingDependencies: boolean;

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
  atoTraceback?: string; // Source traceback if available
  excInfo?: string;     // Exception info if available
}

// Module Definition Types (from /api/modules endpoint)
// Child field within a module (from TypeGraph introspection)
export interface ModuleChild {
  name: string;
  typeName: string;  // The type name (e.g., "Electrical", "Resistor", "V")
  itemType: 'interface' | 'module' | 'component' | 'parameter' | 'trait';
  children: ModuleChild[];  // Nested children (recursive)
}

export interface ModuleDefinition {
  name: string;
  type: 'module' | 'interface' | 'component';
  file: string;
  entry: string;
  line?: number;
  superType?: string;
  children?: ModuleChild[];  // Nested children from TypeGraph introspection
}

// File Tree Types (from /api/files endpoint)
export interface FileTreeNode {
  name: string;
  path: string;
  type: 'file' | 'folder';
  extension?: string;  // 'ato' | 'py'
  children?: FileTreeNode[];
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
  build_id?: string;  // Build ID that produced this variables data (links to build history)
  nodes: VariableNode[];
}
