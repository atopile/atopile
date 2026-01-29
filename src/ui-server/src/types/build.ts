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
  target?: string;
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

export interface QueuedBuild {
  buildId: string;
  status: 'queued' | 'building' | 'success' | 'failed' | 'warning' | 'cancelled';
  projectRoot: string;
  target: string;
  entry?: string;
  startedAt: number;
  elapsedSeconds?: number;
  stages?: Array<{
    name: string;
    stageId?: string;
    displayName?: string;
    status: string;
    elapsedSeconds?: number;
  }>;
  error?: string;
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
  isDirect?: boolean;
  via?: string[];
  installedPath?: string;  // Absolute path where dependency is installed (null if not installed)
  summary?: string;  // Package summary/description from ato.yaml
  usageContent?: string;  // Content of usage.ato if it exists
  license?: string;  // License from ato.yaml package section
  homepage?: string;  // Homepage URL from ato.yaml package section
}

export interface Project {
  root: string;
  name: string;
  displayPath?: string;  // Relative path for display (e.g., "packages/proj")
  description?: string;  // Project description from ato.yaml
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

export interface PackageFileHashes {
  sha256: string;
}

export interface PackageAuthor {
  name: string;
  email?: string | null;
}

export interface PackageArtifact {
  filename: string;
  url: string;
  size: number;
  hashes: PackageFileHashes;
  buildName?: string;
}

export interface PackageLayout {
  buildName: string;
  url: string;
}

export interface PackageImportStatement {
  buildName: string;
  importStatement: string;
}

// Package dependency info
export interface PackageDependency {
  identifier: string;
  version?: string;
}

// Package build target info (from ato.yaml)
export interface PackageBuildTarget {
  name: string;
  entry: string;
}

// Detailed package info from registry (from /api/packages/{id}/details)
export interface PackageDetails {
  identifier: string;
  name: string;
  publisher: string;
  version: string;  // Latest version
  createdAt?: string | null;
  releasedAt?: string | null;
  authors?: PackageAuthor[];
  summary?: string;
  description?: string;
  homepage?: string;
  repository?: string;
  license?: string;
  usageContent?: string;
  readme?: string;
  // Stats
  downloads?: number;
  downloadsThisWeek?: number;
  downloadsThisMonth?: number;
  // Versions
  versions: PackageVersion[];
  versionCount: number;
  // Build outputs
  builds?: Array<string | PackageBuildTarget> | null;
  artifacts?: PackageArtifact[];
  layouts?: PackageLayout[];
  importStatements?: PackageImportStatement[];
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

export interface PartSearchItem {
  lcsc: string;
  manufacturer: string;
  mpn: string;
  package: string;
  description: string;
  datasheet_url: string;
  image_url?: string | null;
  stock: number;
  unit_cost: number;
  is_basic: boolean;
  is_preferred: boolean;
  price: { qFrom: number | null; qTo: number | null; price: number }[];
  attributes: Record<string, string>;
}

export interface PartSearchResponse {
  parts: PartSearchItem[];
  total: number;
  query: string;
  error?: string | null;
}

export interface PartDetailsResponse {
  part: PartSearchItem | null;
}

export interface InstalledPartItem {
  identifier: string;
  manufacturer: string;
  mpn: string;
  lcsc?: string | null;
  datasheet_url?: string | null;
  description?: string | null;
  image_url?: string | null;
  package?: string | null;
  stock?: number | null;
  unit_cost?: number | null;
  path: string;
}

export interface InstalledPartsResponse {
  parts: InstalledPartItem[];
  total: number;
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

  // Build queue items (active + latest completed per target) - display-ready
  // Backend formats/dedupes this data, frontend just renders
  queuedBuilds: Build[];

  // Build history from /api/builds/history (persists across restarts)
  buildHistory: Build[];

  // Packages (from dashboard API /api/packages/summary)
  packages: PackageInfo[];
  isLoadingPackages: boolean;
  packagesError: string | null;  // Registry error visibility
  installingPackageIds: string[];  // Packages currently being installed
  installError: string | null;  // Error from last install attempt
  updatingDependencyIds: string[];  // Dependencies currently being updated (format: projectRoot:dependencyId)

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

  // Log viewer
  logViewerBuildId: string | null;  // Build ID currently shown in log viewer

  // Sidebar UI
  expandedTargets: string[];
  activeEditorFile: string | null;
  lastAtoFile: string | null;  // Last focused .ato file (persists when switching to non-.ato files)

  // Atopile configuration
  atopile: {
    // Actual running atopile info
    actualVersion: string | null;
    actualSource: string | null;
    actualBinaryPath: string | null;
    // User selection state
    source: 'release' | 'local';
    localPath: string | null;
    isInstalling: boolean;
    installProgress: {
      message: string;
      percent?: number;
    } | null;
    error: string | null;
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

  // Project builds (from local ato.yaml for installed dependencies)
  // Map of project root to builds list
  projectBuilds: Record<string, BuildTarget[]>;
  isLoadingBuilds: boolean;

  // Variables (from /api/variables endpoint)
  // Current variables for selected project/target - frontend just displays this
  currentVariablesData: VariablesData | null;
  isLoadingVariables: boolean;
  variablesError: string | null;

  // One-shot open signals (cleared after broadcast)
  // These are set by the backend to trigger file/app opening in VS Code
  openFile?: string | null;
  openFileLine?: number | null;
  openFileColumn?: number | null;
  openLayout?: string | null;
  openKicad?: string | null;
  open3D?: string | null;

  // Test Explorer
  collectedTests: TestItem[];
  isLoadingTests: boolean;
  testsError: string | null;
  testCollectionErrors: Record<string, string>;
  selectedTestNodeIds: string[];
  testRun: TestRun;
  testFilter: string;
  testPaths: string;
  testMarkers: string;
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
  // For parameters: user-specified constraint (e.g., "50 kΩ ±10%", "0402")
  // Undefined means no constraint was specified
  spec?: string;
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

// --- Test Explorer Types ---

export interface TestItem {
  node_id: string;       // Full pytest node ID: "test/foo.py::TestClass::test_method"
  file: string;          // File path: "test/foo.py"
  class_name: string | null;  // Class name if test is in a class
  method_name: string;   // Test function/method name
  display_name: string;  // Human-readable display name
}

export interface TestRun {
  testRunId: string | null;
  isRunning: boolean;
}
