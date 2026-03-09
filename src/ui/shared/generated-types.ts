// Generated from src/atopile/dataclasses.py by scripts/generate_types.py
// Do not edit by hand.

type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };

function cloneGenerated<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export type BuildStatus = "queued" | "building" | "success" | "warning" | "failed" | "cancelled";

export type StageStatus = "pending" | "running" | "success" | "warning" | "failed" | "error" | "skipped";

export type StdLibItemType = "interface" | "module" | "component" | "trait" | "parameter";

export type UiAudience = "user" | "developer" | "agent";

export type UiLogLevel = "DEBUG" | "INFO" | "WARNING" | "ERROR" | "ALERT";

export interface Build {
  name: string;
  projectName: string | null;
  buildId: string | null;
  status: BuildStatus;
  elapsedSeconds: number;
  warnings: number;
  errors: number;
  returnCode: number | null;
  error: string | null;
  projectRoot: string | null;
  entry: string | null;
  startedAt: number | null;
  standalone: boolean;
  frozen: boolean | null;
  stages: BuildStage[];
  totalStages: number | null;
}

export interface BuildRequest {
  projectRoot: string;
  targets: string[];
  frozen: boolean;
  entry: string | null;
  standalone: boolean;
  includeTargets: string[];
  excludeTargets: string[];
}

export interface BuildStage {
  name: string;
  stageId: string;
  elapsedSeconds: number;
  status: StageStatus;
  infos: number;
  warnings: number;
  errors: number;
}

export interface BuildsResponse {
  builds: Build[];
  total: number | null;
}

export interface DependencyInfo {
  identifier: string;
  version: string;
  latestVersion: string | null;
  name: string;
  publisher: string;
  repository: string | null;
  hasUpdate: boolean;
  isDirect: boolean;
  via: string[] | null;
  status: string | null;
}

export interface FileNode {
  name: string;
  children: FileNode[] | null;
}

export interface ModuleChild {
  name: string;
  typeName: string;
  itemType: "interface" | "module" | "component" | "parameter" | "trait";
  children: ModuleChild[];
  spec: string | null;
}

export interface ModuleDefinition {
  name: string;
  type: "module" | "interface" | "component";
  file: string;
  entry: string;
  line: number | null;
  superType: string | null;
  children: ModuleChild[];
}

export interface OpenLayoutRequest {
  projectRoot: string;
  target: string;
}

export interface PackageActionRequest {
  packageIdentifier: string;
  projectRoot: string;
  version: string | null;
}

export interface PackageActionResponse {
  success: boolean;
  message: string;
  action: string;
}

export interface PackageArtifact {
  filename: string;
  url: string;
  size: number;
  hashes: PackageFileHashes;
  buildName: string | null;
}

export interface PackageAuthor {
  name: string;
  email: string | null;
}

export interface PackageDependency {
  identifier: string;
  version: string | null;
}

export interface PackageDetails {
  identifier: string;
  name: string;
  publisher: string;
  version: string;
  createdAt: string | null;
  releasedAt: string | null;
  authors: PackageAuthor[];
  summary: string | null;
  description: string | null;
  homepage: string | null;
  repository: string | null;
  license: string | null;
  downloads: number | null;
  downloadsThisWeek: number | null;
  downloadsThisMonth: number | null;
  versions: PackageVersion[];
  readme: string | null;
  builds: string[] | null;
  artifacts: PackageArtifact[];
  layouts: PackageLayout[];
  importStatements: PackageImportStatement[];
  installed: boolean;
  installedVersion: string | null;
  dependencies: PackageDependency[];
}

export interface PackageFileHashes {
  sha256: string;
}

export interface PackageImportStatement {
  buildName: string;
  importStatement: string;
}

export interface PackageInfo {
  identifier: string;
  name: string;
  publisher: string;
  version: string | null;
  latestVersion: string | null;
  description: string | null;
  summary: string | null;
  homepage: string | null;
  repository: string | null;
  license: string | null;
  installed: boolean;
  hasUpdate: boolean;
  downloads: number | null;
  keywords: string[] | null;
}

export interface PackageInfoVeryBrief {
  identifier: string;
  version: string;
  summary: string;
}

export interface PackageLayout {
  buildName: string;
  url: string;
}

export interface PackageSummaryItem {
  identifier: string;
  name: string;
  publisher: string;
  installed: boolean;
  version: string | null;
  latestVersion: string | null;
  hasUpdate: boolean;
  summary: string | null;
  description: string | null;
  homepage: string | null;
  repository: string | null;
  license: string | null;
  downloads: number | null;
  keywords: string[];
}

export interface PackageVersion {
  version: string;
  releasedAt: string | null;
  requiresAtopile: string | null;
  size: number | null;
}

export interface PackagesResponse {
  packages: PackageInfo[];
  total: number;
}

export interface PackagesSummaryData {
  packages: PackageSummaryItem[];
  total: number;
  installedCount: number;
}

export interface Project {
  root: string;
  name: string;
  targets: ResolvedBuildTarget[];
  needsMigration: boolean;
}

export interface ProjectsResponse {
  projects: Project[];
  total: number;
}

export interface RegistrySearchResponse {
  packages: PackageInfo[];
  total: number;
  query: string;
}

export interface ResolvedBuildTarget {
  name: string;
  entry: string;
  pcbPath: string;
  modelPath: string;
  root: string;
}

export interface StdLibChild {
  name: string;
  type: string;
  itemType: StdLibItemType;
  children: StdLibChild[];
  enumValues: string[];
}

export interface StdLibData {
  items: StdLibItem[];
  total: number;
}

export interface StdLibItem {
  id: string;
  name: string;
  type: StdLibItemType;
  description: string;
  usage: string | null;
  children: StdLibChild[];
  parameters: Record<string, string>[];
}

export interface SyncPackagesRequest {
  projectRoot: string;
  force: boolean;
}

export interface SyncPackagesResponse {
  success: boolean;
  message: string;
  operationId: string | null;
  modifiedPackages: string[] | null;
}

export interface UiActionMessage {
  type: "action";
  action: string;
  [key: string]: unknown;
}

export interface UiActionResultMessage {
  type: "action_result";
  requestId: string | null;
  action: string;
  ok: boolean | null;
  result: unknown;
  error: string | null;
  [key: string]: unknown;
}

export interface UiBOMComponent {
  mpn: string;
  manufacturer: string;
  description: string;
  value: string | null;
  packageName: string | null;
  lcsc: string | null;
  stock: number | null;
  unitCost: number | null;
  quantity: number;
  type: string | null;
  parameters: UiBOMParameter[];
  usages: UiBOMUsage[];
}

export interface UiBOMData {
  components: UiBOMComponent[];
  totalQuantity: number;
  uniqueParts: number;
  estimatedCost: number | null;
  outOfStock: number;
}

export interface UiBOMParameter {
  name: string;
  value: string;
}

export interface UiBOMUsage {
  module: string;
  instance: string;
  file: string | null;
  line: number | null;
}

export interface UiBuildLogRequest {
  buildId: string;
  stage: string | null;
  logLevels: UiLogLevel[] | null;
  audience: UiAudience | null;
  count: number | null;
}

export interface UiCoreStatus {
  error: string | null;
  uvPath: string;
  atoBinary: string;
  mode: "local" | "production";
  version: string;
  coreServerPort: number;
}

export interface UiExtensionSettings {
  devPath: string;
  autoInstall: boolean;
}

export interface UiInstalledPartItem {
  identifier: string;
  manufacturer: string;
  mpn: string;
  lcsc: string | null;
  datasheetUrl: string | null;
  description: string;
  path: string;
}

export interface UiInstalledPartsData {
  parts: UiInstalledPartItem[];
}

export interface UiLogEntry {
  id: number | null;
  timestamp: string;
  level: UiLogLevel;
  audience: UiAudience;
  loggerName: string;
  message: string;
  stage: string | null;
  sourceFile: string | null;
  sourceLine: number | null;
  atoTraceback: string | null;
  pythonTraceback: string | null;
  objects: unknown | null;
}

export interface UiLogsErrorMessage {
  type: "logs_error";
  error: string;
}

export interface UiLogsStreamMessage {
  type: "logs_stream";
  logs: UiLogEntry[];
  lastId: number;
}

export interface UiMigrationState {
  projectRoot: string | null;
  projectName: string | null;
  needsMigration: boolean;
  steps: UiMigrationStep[];
  topics: UiMigrationTopic[];
  stepResults: UiMigrationStepResult[];
  loading: boolean;
  running: boolean;
  completed: boolean;
  error: string | null;
}

export interface UiMigrationStep {
  id: string;
  label: string;
  description: string;
  topic: string;
  mandatory: boolean;
  order: number;
}

export interface UiMigrationStepResult {
  stepId: string;
  status: "idle" | "running" | "success" | "error";
  error: string | null;
}

export interface UiMigrationTopic {
  id: string;
  label: string;
  icon: string;
}

export interface UiPackageDetailState {
  projectRoot: string | null;
  packageId: string | null;
  summary: PackageSummaryItem | null;
  details: PackageDetails | null;
  loading: boolean;
  error: string | null;
  actionError: string | null;
}

export interface UiPartDetail {
  identifier: string;
  lcsc: string | null;
  mpn: string;
  manufacturer: string;
  description: string;
  package: string | null;
  datasheetUrl: string | null;
  path: string | null;
  stock: number | null;
  unitCost: number | null;
  isBasic: boolean;
  isPreferred: boolean;
  attributes: Record<string, string>;
  footprint: string | null;
  imageUrl: string | null;
  installed: boolean;
}

export interface UiPartDetailState {
  projectRoot: string | null;
  lcsc: string | null;
  part: UiPartDetail | null;
  loading: boolean;
  error: string | null;
  actionError: string | null;
}

export interface UiPartSearchItem {
  lcsc: string;
  mpn: string;
  manufacturer: string;
  description: string;
  stock: number;
  unitCost: number | null;
  datasheetUrl: string | null;
  package: string | null;
  isBasic: boolean;
  isPreferred: boolean;
  attributes: Record<string, string>;
}

export interface UiPartsSearchData {
  parts: UiPartSearchItem[];
  error: string | null;
}

export interface UiProjectState {
  selectedProject: string | null;
  selectedTarget: string | null;
  activeFilePath: string | null;
}

export interface UiSidebarDetails {
  view: "none" | "package" | "part" | "migration";
  package: UiPackageDetailState;
  part: UiPartDetailState;
  migration: UiMigrationState;
}

export interface UiStateMessage {
  type: "state";
  key: StoreKey;
  data: unknown;
}

export interface UiStore {
  coreStatus: UiCoreStatus;
  extensionSettings: UiExtensionSettings;
  projectState: UiProjectState;
  projects: Project[];
  projectFiles: FileNode[];
  currentBuilds: Build[];
  previousBuilds: Build[];
  packagesSummary: PackagesSummaryData;
  partsSearch: UiPartsSearchData;
  installedParts: UiInstalledPartsData;
  sidebarDetails: UiSidebarDetails;
  stdlibData: StdLibData;
  structureData: UiStructureData;
  variablesData: UiVariablesData;
  bomData: UiBOMData;
}

export interface UiStructureData {
  modules: ModuleDefinition[];
  total: number;
}

export interface UiSubscribeMessage {
  type: "subscribe";
  keys: StoreKey[];
}

export interface UiVariable {
  name: string;
  spec: string | null;
  actual: string | null;
  tolerance: string | null;
  status: string | null;
}

export interface UiVariableNode {
  name: string;
  variables: UiVariable[];
  children: UiVariableNode[];
}

export interface UiVariablesData {
  nodes: UiVariableNode[];
}

export const STORE_KEYS = ["bomData", "coreStatus", "currentBuilds", "extensionSettings", "installedParts", "packagesSummary", "partsSearch", "previousBuilds", "projectFiles", "projectState", "projects", "sidebarDetails", "stdlibData", "structureData", "variablesData"] as const;
export type StoreKey = typeof STORE_KEYS[number];

export const DEFAULT_Build: Build = {
  "buildId": null,
  "elapsedSeconds": 0.0,
  "entry": null,
  "error": null,
  "errors": 0,
  "frozen": false,
  "name": "default",
  "projectName": null,
  "projectRoot": null,
  "returnCode": null,
  "stages": [],
  "standalone": false,
  "startedAt": null,
  "status": "queued",
  "totalStages": null,
  "warnings": 0
};

export function createBuild(): Build {
  return cloneGenerated(DEFAULT_Build);
}

export const DEFAULT_UiBOMComponent: UiBOMComponent = {
  "description": "",
  "lcsc": null,
  "manufacturer": "",
  "mpn": "",
  "packageName": null,
  "parameters": [],
  "quantity": 0,
  "stock": null,
  "type": null,
  "unitCost": null,
  "usages": [],
  "value": null
};

export function createUiBOMComponent(): UiBOMComponent {
  return cloneGenerated(DEFAULT_UiBOMComponent);
}

export const DEFAULT_UiBOMData: UiBOMData = {
  "components": [],
  "estimatedCost": null,
  "outOfStock": 0,
  "totalQuantity": 0,
  "uniqueParts": 0
};

export function createUiBOMData(): UiBOMData {
  return cloneGenerated(DEFAULT_UiBOMData);
}

export const DEFAULT_UiBOMParameter: UiBOMParameter = {
  "name": "",
  "value": ""
};

export function createUiBOMParameter(): UiBOMParameter {
  return cloneGenerated(DEFAULT_UiBOMParameter);
}

export const DEFAULT_UiBOMUsage: UiBOMUsage = {
  "file": null,
  "instance": "",
  "line": null,
  "module": ""
};

export function createUiBOMUsage(): UiBOMUsage {
  return cloneGenerated(DEFAULT_UiBOMUsage);
}

export const DEFAULT_UiBuildLogRequest: UiBuildLogRequest = {
  "audience": null,
  "buildId": "",
  "count": null,
  "logLevels": null,
  "stage": null
};

export function createUiBuildLogRequest(): UiBuildLogRequest {
  return cloneGenerated(DEFAULT_UiBuildLogRequest);
}

export const DEFAULT_UiCoreStatus: UiCoreStatus = {
  "atoBinary": "",
  "coreServerPort": 0,
  "error": null,
  "mode": "production",
  "uvPath": "",
  "version": ""
};

export function createUiCoreStatus(): UiCoreStatus {
  return cloneGenerated(DEFAULT_UiCoreStatus);
}

export const DEFAULT_UiExtensionSettings: UiExtensionSettings = {
  "autoInstall": true,
  "devPath": ""
};

export function createUiExtensionSettings(): UiExtensionSettings {
  return cloneGenerated(DEFAULT_UiExtensionSettings);
}

export const DEFAULT_UiInstalledPartItem: UiInstalledPartItem = {
  "datasheetUrl": null,
  "description": "",
  "identifier": "",
  "lcsc": null,
  "manufacturer": "",
  "mpn": "",
  "path": ""
};

export function createUiInstalledPartItem(): UiInstalledPartItem {
  return cloneGenerated(DEFAULT_UiInstalledPartItem);
}

export const DEFAULT_UiInstalledPartsData: UiInstalledPartsData = {
  "parts": []
};

export function createUiInstalledPartsData(): UiInstalledPartsData {
  return cloneGenerated(DEFAULT_UiInstalledPartsData);
}

export const DEFAULT_UiLogEntry: UiLogEntry = {
  "atoTraceback": null,
  "audience": "user",
  "id": null,
  "level": "INFO",
  "loggerName": "",
  "message": "",
  "objects": null,
  "pythonTraceback": null,
  "sourceFile": null,
  "sourceLine": null,
  "stage": null,
  "timestamp": ""
};

export function createUiLogEntry(): UiLogEntry {
  return cloneGenerated(DEFAULT_UiLogEntry);
}

export const DEFAULT_UiLogsStreamMessage: UiLogsStreamMessage = {
  "lastId": 0,
  "logs": [],
  "type": "logs_stream"
};

export function createUiLogsStreamMessage(): UiLogsStreamMessage {
  return cloneGenerated(DEFAULT_UiLogsStreamMessage);
}

export const DEFAULT_UiMigrationState: UiMigrationState = {
  "completed": false,
  "error": null,
  "loading": false,
  "needsMigration": false,
  "projectName": null,
  "projectRoot": null,
  "running": false,
  "stepResults": [],
  "steps": [],
  "topics": []
};

export function createUiMigrationState(): UiMigrationState {
  return cloneGenerated(DEFAULT_UiMigrationState);
}

export const DEFAULT_UiPackageDetailState: UiPackageDetailState = {
  "actionError": null,
  "details": null,
  "error": null,
  "loading": false,
  "packageId": null,
  "projectRoot": null,
  "summary": null
};

export function createUiPackageDetailState(): UiPackageDetailState {
  return cloneGenerated(DEFAULT_UiPackageDetailState);
}

export const DEFAULT_UiPartDetail: UiPartDetail = {
  "attributes": {},
  "datasheetUrl": null,
  "description": "",
  "footprint": null,
  "identifier": "",
  "imageUrl": null,
  "installed": false,
  "isBasic": false,
  "isPreferred": false,
  "lcsc": null,
  "manufacturer": "",
  "mpn": "",
  "package": null,
  "path": null,
  "stock": null,
  "unitCost": null
};

export function createUiPartDetail(): UiPartDetail {
  return cloneGenerated(DEFAULT_UiPartDetail);
}

export const DEFAULT_UiPartDetailState: UiPartDetailState = {
  "actionError": null,
  "error": null,
  "lcsc": null,
  "loading": false,
  "part": null,
  "projectRoot": null
};

export function createUiPartDetailState(): UiPartDetailState {
  return cloneGenerated(DEFAULT_UiPartDetailState);
}

export const DEFAULT_UiPartSearchItem: UiPartSearchItem = {
  "attributes": {},
  "datasheetUrl": null,
  "description": "",
  "isBasic": false,
  "isPreferred": false,
  "lcsc": "",
  "manufacturer": "",
  "mpn": "",
  "package": null,
  "stock": 0,
  "unitCost": null
};

export function createUiPartSearchItem(): UiPartSearchItem {
  return cloneGenerated(DEFAULT_UiPartSearchItem);
}

export const DEFAULT_UiPartsSearchData: UiPartsSearchData = {
  "error": null,
  "parts": []
};

export function createUiPartsSearchData(): UiPartsSearchData {
  return cloneGenerated(DEFAULT_UiPartsSearchData);
}

export const DEFAULT_UiProjectState: UiProjectState = {
  "activeFilePath": null,
  "selectedProject": null,
  "selectedTarget": null
};

export function createUiProjectState(): UiProjectState {
  return cloneGenerated(DEFAULT_UiProjectState);
}

export const DEFAULT_UiSidebarDetails: UiSidebarDetails = {
  "migration": {
    "completed": false,
    "error": null,
    "loading": false,
    "needsMigration": false,
    "projectName": null,
    "projectRoot": null,
    "running": false,
    "stepResults": [],
    "steps": [],
    "topics": []
  },
  "package": {
    "actionError": null,
    "details": null,
    "error": null,
    "loading": false,
    "packageId": null,
    "projectRoot": null,
    "summary": null
  },
  "part": {
    "actionError": null,
    "error": null,
    "lcsc": null,
    "loading": false,
    "part": null,
    "projectRoot": null
  },
  "view": "none"
};

export function createUiSidebarDetails(): UiSidebarDetails {
  return cloneGenerated(DEFAULT_UiSidebarDetails);
}

export const DEFAULT_UiStore: UiStore = {
  "bomData": {
    "components": [],
    "estimatedCost": null,
    "outOfStock": 0,
    "totalQuantity": 0,
    "uniqueParts": 0
  },
  "coreStatus": {
    "atoBinary": "",
    "coreServerPort": 0,
    "error": null,
    "mode": "production",
    "uvPath": "",
    "version": ""
  },
  "currentBuilds": [],
  "extensionSettings": {
    "autoInstall": true,
    "devPath": ""
  },
  "installedParts": {
    "parts": []
  },
  "packagesSummary": {
    "installedCount": 0,
    "packages": [],
    "total": 0
  },
  "partsSearch": {
    "error": null,
    "parts": []
  },
  "previousBuilds": [],
  "projectFiles": [],
  "projectState": {
    "activeFilePath": null,
    "selectedProject": null,
    "selectedTarget": null
  },
  "projects": [],
  "sidebarDetails": {
    "migration": {
      "completed": false,
      "error": null,
      "loading": false,
      "needsMigration": false,
      "projectName": null,
      "projectRoot": null,
      "running": false,
      "stepResults": [],
      "steps": [],
      "topics": []
    },
    "package": {
      "actionError": null,
      "details": null,
      "error": null,
      "loading": false,
      "packageId": null,
      "projectRoot": null,
      "summary": null
    },
    "part": {
      "actionError": null,
      "error": null,
      "lcsc": null,
      "loading": false,
      "part": null,
      "projectRoot": null
    },
    "view": "none"
  },
  "stdlibData": {
    "items": [],
    "total": 0
  },
  "structureData": {
    "modules": [],
    "total": 0
  },
  "variablesData": {
    "nodes": []
  }
};

export function createUiStore(): UiStore {
  return cloneGenerated(DEFAULT_UiStore);
}

export const DEFAULT_UiStructureData: UiStructureData = {
  "modules": [],
  "total": 0
};

export function createUiStructureData(): UiStructureData {
  return cloneGenerated(DEFAULT_UiStructureData);
}

export const DEFAULT_UiVariable: UiVariable = {
  "actual": null,
  "name": "",
  "spec": null,
  "status": null,
  "tolerance": null
};

export function createUiVariable(): UiVariable {
  return cloneGenerated(DEFAULT_UiVariable);
}

export const DEFAULT_UiVariableNode: UiVariableNode = {
  "children": [],
  "name": "",
  "variables": []
};

export function createUiVariableNode(): UiVariableNode {
  return cloneGenerated(DEFAULT_UiVariableNode);
}

export const DEFAULT_UiVariablesData: UiVariablesData = {
  "nodes": []
};

export function createUiVariablesData(): UiVariablesData {
  return cloneGenerated(DEFAULT_UiVariablesData);
}
