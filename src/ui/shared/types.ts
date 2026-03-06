/**
 * Canonical shared types for the atopile UI.
 *
 * Imported by both the hub (Node process) and webview (React) code.
 */

export class StoreState {
  hubConnected: boolean = false;
  coreStatus = new CoreStatus();
  extensionSettings = new ExtensionSettings();
  projectState = new ProjectState();
  projects: Project[] = [];
  projectFiles: FileNode[] = [];
  currentBuilds: Build[] = [];
  previousBuilds: Build[] = [];
  packagesSummary: PackagesSummaryData = new PackagesSummaryData();
  partsSearch: PartsSearchData = new PartsSearchData();
  installedParts: InstalledPartsData = new InstalledPartsData();
  stdlibData: StdLibData = new StdLibData();
  structureData: StructureData = new StructureData();
  variablesData: VariablesData = new VariablesData();
  bomData: BOMData = new BOMData();
}

export class ExtensionSettings {
  devPath: string = "";
  autoInstall: boolean = true;
}

export class CoreStatus {
  hubCoreConnected: boolean = false;
  logCoreConnected: boolean = false;
  error: string | null = null;
  uvPath: string = "";
  atoBinary: string = "";
  mode: "local" | "production" = "production";
  version: string = "";
  coreServerPort: number = 0;
}

export class ProjectState {
  selectedProject: string | null = null;
  selectedTarget: string | null = null;
  activeFilePath: string | null = null;
}

export class Project {
  root: string = "";
  name: string = "";
  targets: string[] = [];
}

export class FileNode {
  name: string = "";
  children?: FileNode[];
}

export class BuildStage {
  name: string = "";
  stageId?: string;
  elapsedSeconds: number = 0;
  status: string = "";
  infos?: number;
  warnings?: number;
  errors?: number;
}

export class Build {
  name: string = "";
  buildId?: string;
  status: string = "";
  elapsedSeconds: number = 0;
  projectRoot?: string;
  entry?: string;
  startedAt?: number;
  stages?: BuildStage[];
  currentStage?: BuildStage | null;
  totalStages?: number | null;
  warnings?: number;
  errors?: number;
  error?: string;
  returnCode?: number | null;
}

export interface BuildTarget {
  name: string;
  entry: string;
  pcb_path: string;
  model_path: string;
  root: string;
}

export interface AtoYaml {
  paths?: {
    layout?: string;
  };
  builds: Record<
    string,
    {
      entry: string;
      paths?: {
        layout?: string;
      };
    }
  >;
}

// -- Packages panel types --------------------------------------------------

export interface PackageSummaryItem {
  identifier: string;
  name: string;
  publisher: string;
  installed: boolean;
  version: string | null;
  latest_version: string | null;
  has_update: boolean;
  summary: string | null;
  description: string | null;
  homepage: string | null;
  repository: string | null;
  license: string | null;
  downloads: number | null;
  keywords: string[];
}

export class PackagesSummaryData {
  packages: PackageSummaryItem[] = [];
  total: number = 0;
  installedCount: number = 0;
}

// -- Parts panel types -----------------------------------------------------

export interface PartSearchItem {
  lcsc: string;
  mpn: string;
  manufacturer: string;
  description: string;
  stock: number;
  unit_cost: number | null;
  datasheet_url: string | null;
  package: string | null;
  is_basic: boolean;
  is_preferred: boolean;
  attributes: Record<string, string>;
}

export class PartsSearchData {
  parts: PartSearchItem[] = [];
  error: string | null = null;
}

export interface InstalledPartItem {
  identifier: string;
  manufacturer: string;
  mpn: string;
  lcsc: string | null;
  datasheet_url: string | null;
  description: string;
  path: string;
}

export class InstalledPartsData {
  parts: InstalledPartItem[] = [];
}

// -- Standard library panel types ------------------------------------------

export interface StdLibChild {
  name: string;
  type: string;
  item_type: string;
  children: StdLibChild[];
  enum_values: string[];
}

export interface StdLibItem {
  id: string;
  name: string;
  type: string;
  description: string;
  usage: string | null;
  children: StdLibChild[];
  parameters: Record<string, string>[];
}

export class StdLibData {
  items: StdLibItem[] = [];
  total: number = 0;
}

// -- Structure panel types -------------------------------------------------

export interface ModuleChild {
  name: string;
  type_name: string;
  item_type: string;
  children: ModuleChild[];
  spec: string | null;
}

export interface StructureModule {
  name: string;
  type: string;
  file: string;
  entry: string;
  line: number | null;
  super_type: string | null;
  children: ModuleChild[];
}

export class StructureData {
  modules: StructureModule[] = [];
  total: number = 0;
}

// -- Parameters (variables) panel types ------------------------------------

export interface Variable {
  name: string;
  spec: string | null;
  actual: string | null;
  tolerance: string | null;
  status: string | null;
}

export interface VariableNode {
  name: string;
  variables: Variable[];
  children: VariableNode[];
}

export class VariablesData {
  nodes: VariableNode[] = [];
}

// -- BOM panel types -------------------------------------------------------

export interface BOMParameter {
  name: string;
  value: string;
}

export interface BOMUsage {
  module: string;
  instance: string;
  file: string | null;
  line: number | null;
}

export interface BOMComponent {
  mpn: string;
  manufacturer: string;
  description: string;
  value: string | null;
  package_name: string | null;
  lcsc: string | null;
  stock: number | null;
  unit_cost: number | null;
  quantity: number;
  type: string | null;
  parameters: BOMParameter[];
  usages: BOMUsage[];
}

export class BOMData {
  components: BOMComponent[] = [];
  totalQuantity: number = 0;
  uniqueParts: number = 0;
  estimatedCost: number | null = null;
  outOfStock: number = 0;
}

// -- Log viewer types ------------------------------------------------------

export type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'ALERT';
export type Audience = 'user' | 'developer' | 'agent';
export type TimeMode = 'delta' | 'wall';
export type SourceMode = 'source' | 'logger';
export type LogConnectionState = 'disconnected' | 'connecting' | 'connected';

export const LEVEL_SHORT: Record<LogLevel, string> = {
  DEBUG: 'D',
  INFO: 'I',
  WARNING: 'W',
  ERROR: 'E',
  ALERT: 'A',
};

export const SOURCE_COLORS = [
  '#cba6f7', '#f38ba8', '#fab387', '#f9e2af',
  '#a6e3a1', '#94e2d5', '#89dceb', '#74c7ec',
  '#89b4fa', '#b4befe', '#f5c2e7', '#eba0ac',
];

export class LogEntry {
  id?: number;
  timestamp: string = "";
  level: LogLevel = "INFO";
  audience: Audience = "user";
  logger_name: string = "";
  message: string = "";
  stage?: string | null;
  source_file?: string | null;
  source_line?: number | null;
  ato_traceback?: string | null;
  python_traceback?: string | null;
  objects?: unknown;
}

export type LogMessage =
  | { type: 'logs_stream'; logs: LogEntry[]; last_id: number }
  | { type: 'logs_error'; error: string };

export class TreeNode {
  entry: LogEntry = new LogEntry();
  depth: number = 0;
  content: string = "";
  children: TreeNode[] = [];
}

export class LogTreeGroup {
  type: 'standalone' | 'tree' = 'standalone';
  root: TreeNode = new TreeNode();
}

export class BuildLogRequest {
  build_id: string = "";
  stage?: string | null;
  log_levels?: LogLevel[] | null;
  audience?: Audience | null;
  count?: number;
}

// -- WebSocket protocol messages -------------------------------------------

export const MSG_TYPE = {
  SUBSCRIBE: "subscribe",
  STATE: "state",
  ACTION: "action",
} as const;

export interface SubscribeMessage {
  type: typeof MSG_TYPE.SUBSCRIBE;
  keys: string[];
}

export interface StateMessage {
  type: typeof MSG_TYPE.STATE;
  key: string;
  data: unknown;
}

export interface ActionMessage {
  type: typeof MSG_TYPE.ACTION;
  action: string;
  [key: string]: unknown;
}

export type WebSocketMessage = SubscribeMessage | StateMessage | ActionMessage;
