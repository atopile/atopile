/**
 * Canonical shared types for the atopile UI.
 *
 * Imported by both the hub (Node process) and webview (React) code.
 */

export class StoreState {
  hubStatus = new HubStatus();
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

export class HubStatus {
  connected: boolean = false;
}

export class CoreStatus {
  connected: boolean = false;
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
