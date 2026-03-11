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

export interface AddBuildTargetRequest {
  projectRoot: string;
  name: string;
  entry: string;
}

export interface AddBuildTargetResponse {
  success: boolean;
  message: string;
  target: string | null;
}

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
  target: ResolvedBuildTarget | null;
  startedAt: number | null;
  standalone: boolean;
  frozen: boolean | null;
  stages: BuildStage[];
  totalStages: number | null;
}

export interface BuildRequest {
  projectRoot: string;
  targets: ResolvedBuildTarget[];
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

export interface CreateProjectRequest {
  parentDirectory: string;
  name: string | null;
}

export interface CreateProjectResponse {
  success: boolean;
  message: string;
  projectRoot: string | null;
  projectName: string | null;
}

export interface DeleteBuildTargetRequest {
  projectRoot: string;
  name: string;
}

export interface DeleteBuildTargetResponse {
  success: boolean;
  message: string;
}

export interface DependenciesResponse {
  dependencies: DependencyInfo[];
  total: number;
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

export interface ModulesResponse {
  modules: ModuleDefinition[];
  total: number;
}

export interface OpenLayoutRequest {
  projectRoot: string;
  target: ResolvedBuildTarget;
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

export interface Problem {
  id: string;
  level: "error" | "warning";
  message: string;
  file: string | null;
  line: number | null;
  column: number | null;
  stage: string | null;
  logger: string | null;
  buildName: string | null;
  projectName: string | null;
  timestamp: string | null;
  atoTraceback: string | null;
  excInfo: string | null;
}

export interface ProblemFilter {
  levels: ("error" | "warning")[];
  buildNames: string[];
  stageIds: string[];
}

export interface ProblemsResponse {
  problems: Problem[];
  total: number;
  errorCount: number;
  warningCount: number;
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

export interface RenameProjectRequest {
  projectRoot: string;
  newName: string;
}

export interface RenameProjectResponse {
  success: boolean;
  message: string;
  oldRoot: string;
  newRoot: string | null;
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
  id: string;
  lcsc: string | null;
  mpn: string;
  manufacturer: string;
  type: string | null;
  value: string;
  package: string;
  description: string;
  source: string | null;
  stock: number | null;
  unitCost: number | null;
  isBasic: boolean | null;
  isPreferred: boolean | null;
  quantity: number;
  parameters: UiBOMParameter[];
  usages: UiBOMUsage[];
}

export interface UiBOMData {
  projectRoot: string | null;
  target: ResolvedBuildTarget | null;
  loading: boolean;
  error: string | null;
  version: string | null;
  buildId: string | null;
  components: UiBOMComponent[];
  totalQuantity: number;
  uniqueParts: number;
  estimatedCost: number | null;
  outOfStock: number;
}

export interface UiBOMParameter {
  name: string;
  value: string;
  unit: string | null;
}

export interface UiBOMUsage {
  address: string;
  designator: string;
  line: number | null;
}

export interface UiBlobAssetData {
  action: string | null;
  requestKey: string;
  contentType: string | null;
  filename: string | null;
  data: string | null;
  loading: boolean;
  error: string | null;
}

export interface UiBuildLogRequest {
  buildId: string;
  stage: string | null;
  logLevels: UiLogLevel[] | null;
  audience: UiAudience | null;
  count: number | null;
}

export interface UiBuildsByProjectData {
  projectRoot: string | null;
  target: ResolvedBuildTarget | null;
  limit: number;
  builds: Build[];
  loading: boolean;
}

export interface UiCoreStatus {
  error: string | null;
  uvPath: string;
  atoBinary: string;
  mode: "local" | "production";
  version: string;
  coreServerPort: number;
}

export interface UiEntryCheckData {
  projectRoot: string | null;
  entry: string;
  fileExists: boolean;
  moduleExists: boolean;
  targetExists: boolean;
  loading: boolean;
}

export interface UiExtensionSettings {
  devPath: string;
  autoInstall: boolean;
}

export interface UiFileActionData {
  action: "none" | "create_file" | "create_folder" | "rename" | "duplicate" | "delete";
  path: string | null;
  isFolder: boolean;
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

export interface UiLayoutData {
  projectRoot: string | null;
  target: ResolvedBuildTarget | null;
  path: string | null;
  loading: boolean;
  error: string | null;
}

export interface UiLcscPartData {
  manufacturer: string | null;
  mpn: string | null;
  description: string | null;
  stock: number | null;
  unitCost: number | null;
  isBasic: boolean | null;
  isPreferred: boolean | null;
}

export interface UiLcscPartsData {
  projectRoot: string | null;
  target: ResolvedBuildTarget | null;
  parts: Record<string, UiLcscPartData | null>;
  loadingIds: string[];
}

export interface UiLogEntry {
  id: number | null;
  timestamp: string;
  level: UiLogLevel;
  audience: UiAudience;
  loggerName: string;
  message: string;
  testName: string | null;
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
  buildId: string;
  stage: string | null;
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
  importStatement: string | null;
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
  selectedTarget: ResolvedBuildTarget | null;
  activeFilePath: string | null;
  logViewBuildId: string | null;
  logViewStage: string | null;
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
  queueBuilds: Build[];
  selectedBuild: Build | null;
  packagesSummary: PackagesSummaryData;
  partsSearch: UiPartsSearchData;
  installedParts: UiInstalledPartsData;
  sidebarDetails: UiSidebarDetails;
  stdlibData: StdLibData;
  structureData: UiStructureData;
  variablesData: UiVariablesData;
  bomData: UiBOMData;
  entryCheck: UiEntryCheckData;
  lcscPartsData: UiLcscPartsData;
  buildsByProjectData: UiBuildsByProjectData;
  layoutData: UiLayoutData;
  blobAsset: UiBlobAssetData;
  fileAction: UiFileActionData;
}

export interface UiStructureData {
  modules: ModuleDefinition[];
  total: number;
}

export interface UiSubscribeMessage {
  type: "subscribe";
  keys: StoreKey[];
}

export interface UiTestLogRequest {
  testRunId: string;
  testName: string | null;
  logLevels: UiLogLevel[] | null;
  audience: UiAudience | null;
  count: number | null;
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

export interface UpdateBuildTargetRequest {
  projectRoot: string;
  oldName: string;
  newName: string | null;
  newEntry: string | null;
}

export interface UpdateBuildTargetResponse {
  success: boolean;
  message: string;
  target: string | null;
}

export const STORE_KEYS = ["blobAsset", "bomData", "buildsByProjectData", "coreStatus", "currentBuilds", "entryCheck", "extensionSettings", "fileAction", "installedParts", "layoutData", "lcscPartsData", "packagesSummary", "partsSearch", "previousBuilds", "projectFiles", "projectState", "projects", "queueBuilds", "selectedBuild", "sidebarDetails", "stdlibData", "structureData", "variablesData"] as const;
export type StoreKey = typeof STORE_KEYS[number];

export const DEFAULT_Build: Build = {
  "buildId": null,
  "elapsedSeconds": 0.0,
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
  "target": null,
  "totalStages": null,
  "warnings": 0
};

export function createBuild(): Build {
  return cloneGenerated(DEFAULT_Build);
}

export const DEFAULT_ProblemFilter: ProblemFilter = {
  "buildNames": [],
  "levels": [
    "error",
    "warning"
  ],
  "stageIds": []
};

export function createProblemFilter(): ProblemFilter {
  return cloneGenerated(DEFAULT_ProblemFilter);
}

export const DEFAULT_UiBOMComponent: UiBOMComponent = {
  "description": "",
  "id": "",
  "isBasic": null,
  "isPreferred": null,
  "lcsc": null,
  "manufacturer": "",
  "mpn": "",
  "package": "",
  "parameters": [],
  "quantity": 0,
  "source": null,
  "stock": null,
  "type": null,
  "unitCost": null,
  "usages": [],
  "value": ""
};

export function createUiBOMComponent(): UiBOMComponent {
  return cloneGenerated(DEFAULT_UiBOMComponent);
}

export const DEFAULT_UiBOMData: UiBOMData = {
  "buildId": null,
  "components": [],
  "error": null,
  "estimatedCost": null,
  "loading": false,
  "outOfStock": 0,
  "projectRoot": null,
  "target": null,
  "totalQuantity": 0,
  "uniqueParts": 0,
  "version": null
};

export function createUiBOMData(): UiBOMData {
  return cloneGenerated(DEFAULT_UiBOMData);
}

export const DEFAULT_UiBOMParameter: UiBOMParameter = {
  "name": "",
  "unit": null,
  "value": ""
};

export function createUiBOMParameter(): UiBOMParameter {
  return cloneGenerated(DEFAULT_UiBOMParameter);
}

export const DEFAULT_UiBOMUsage: UiBOMUsage = {
  "address": "",
  "designator": "",
  "line": null
};

export function createUiBOMUsage(): UiBOMUsage {
  return cloneGenerated(DEFAULT_UiBOMUsage);
}

export const DEFAULT_UiBlobAssetData: UiBlobAssetData = {
  "action": null,
  "contentType": null,
  "data": null,
  "error": null,
  "filename": null,
  "loading": false,
  "requestKey": ""
};

export function createUiBlobAssetData(): UiBlobAssetData {
  return cloneGenerated(DEFAULT_UiBlobAssetData);
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

export const DEFAULT_UiBuildsByProjectData: UiBuildsByProjectData = {
  "builds": [],
  "limit": 0,
  "loading": false,
  "projectRoot": null,
  "target": null
};

export function createUiBuildsByProjectData(): UiBuildsByProjectData {
  return cloneGenerated(DEFAULT_UiBuildsByProjectData);
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

export const DEFAULT_UiEntryCheckData: UiEntryCheckData = {
  "entry": "",
  "fileExists": false,
  "loading": false,
  "moduleExists": false,
  "projectRoot": null,
  "targetExists": false
};

export function createUiEntryCheckData(): UiEntryCheckData {
  return cloneGenerated(DEFAULT_UiEntryCheckData);
}

export const DEFAULT_UiExtensionSettings: UiExtensionSettings = {
  "autoInstall": true,
  "devPath": ""
};

export function createUiExtensionSettings(): UiExtensionSettings {
  return cloneGenerated(DEFAULT_UiExtensionSettings);
}

export const DEFAULT_UiFileActionData: UiFileActionData = {
  "action": "none",
  "isFolder": false,
  "path": null
};

export function createUiFileActionData(): UiFileActionData {
  return cloneGenerated(DEFAULT_UiFileActionData);
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

export const DEFAULT_UiLayoutData: UiLayoutData = {
  "error": null,
  "loading": false,
  "path": null,
  "projectRoot": null,
  "target": null
};

export function createUiLayoutData(): UiLayoutData {
  return cloneGenerated(DEFAULT_UiLayoutData);
}

export const DEFAULT_UiLcscPartData: UiLcscPartData = {
  "description": null,
  "isBasic": null,
  "isPreferred": null,
  "manufacturer": null,
  "mpn": null,
  "stock": null,
  "unitCost": null
};

export function createUiLcscPartData(): UiLcscPartData {
  return cloneGenerated(DEFAULT_UiLcscPartData);
}

export const DEFAULT_UiLcscPartsData: UiLcscPartsData = {
  "loadingIds": [],
  "parts": {},
  "projectRoot": null,
  "target": null
};

export function createUiLcscPartsData(): UiLcscPartsData {
  return cloneGenerated(DEFAULT_UiLcscPartsData);
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
  "testName": null,
  "timestamp": ""
};

export function createUiLogEntry(): UiLogEntry {
  return cloneGenerated(DEFAULT_UiLogEntry);
}

export const DEFAULT_UiLogsStreamMessage: UiLogsStreamMessage = {
  "buildId": "",
  "lastId": 0,
  "logs": [],
  "stage": null,
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
  "importStatement": null,
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
  "logViewBuildId": null,
  "logViewStage": null,
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
  "blobAsset": {
    "action": null,
    "contentType": null,
    "data": null,
    "error": null,
    "filename": null,
    "loading": false,
    "requestKey": ""
  },
  "bomData": {
    "buildId": null,
    "components": [],
    "error": null,
    "estimatedCost": null,
    "loading": false,
    "outOfStock": 0,
    "projectRoot": null,
    "target": null,
    "totalQuantity": 0,
    "uniqueParts": 0,
    "version": null
  },
  "buildsByProjectData": {
    "builds": [],
    "limit": 0,
    "loading": false,
    "projectRoot": null,
    "target": null
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
  "entryCheck": {
    "entry": "",
    "fileExists": false,
    "loading": false,
    "moduleExists": false,
    "projectRoot": null,
    "targetExists": false
  },
  "extensionSettings": {
    "autoInstall": true,
    "devPath": ""
  },
  "fileAction": {
    "action": "none",
    "isFolder": false,
    "path": null
  },
  "installedParts": {
    "parts": []
  },
  "layoutData": {
    "error": null,
    "loading": false,
    "path": null,
    "projectRoot": null,
    "target": null
  },
  "lcscPartsData": {
    "loadingIds": [],
    "parts": {},
    "projectRoot": null,
    "target": null
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
    "logViewBuildId": null,
    "logViewStage": null,
    "selectedProject": null,
    "selectedTarget": null
  },
  "projects": [],
  "queueBuilds": [],
  "selectedBuild": null,
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

export const DEFAULT_UiTestLogRequest: UiTestLogRequest = {
  "audience": null,
  "count": null,
  "logLevels": null,
  "testName": null,
  "testRunId": ""
};

export function createUiTestLogRequest(): UiTestLogRequest {
  return cloneGenerated(DEFAULT_UiTestLogRequest);
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
