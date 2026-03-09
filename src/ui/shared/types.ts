/**
 * Frontend-side helpers layered on top of generated backend-owned UI types.
 *
 * The canonical shared schema lives in `generated-types.ts`, which is generated
 * from `src/atopile/dataclasses.py`.
 */

import * as Gen from "./generated-types";

export type ExtensionSettings = Gen.UiExtensionSettings;
export type CoreStatus = Gen.UiCoreStatus;
export type ProjectState = Gen.UiProjectState;
export type Project = Gen.Project;
export type FileNode = Gen.FileNode;
export type BuildStage = Gen.BuildStage;
export type Build = Gen.Build & {
  currentStage?: BuildStage | null;
};
export type PackageSummaryItem = Gen.PackageSummaryItem;
export type PackagesSummaryData = Gen.PackagesSummaryData;
export type PartSearchItem = Gen.UiPartSearchItem;
export type PartsSearchData = Gen.UiPartsSearchData;
export type InstalledPartItem = Gen.UiInstalledPartItem;
export type InstalledPartsData = Gen.UiInstalledPartsData;
export type SidebarPackageDetailState = Gen.UiPackageDetailState;
export type SidebarPartDetail = Gen.UiPartDetail;
export type SidebarPartDetailState = Gen.UiPartDetailState;
export type MigrationStep = Gen.UiMigrationStep;
export type MigrationTopic = Gen.UiMigrationTopic;
export type MigrationStepResult = Gen.UiMigrationStepResult;
export type MigrationState = Gen.UiMigrationState;
export type SidebarDetails = Gen.UiSidebarDetails;
export type StdLibChild = Gen.StdLibChild;
export type StdLibItem = Gen.StdLibItem;
export type StdLibData = Gen.StdLibData;
export type ModuleChild = Gen.ModuleChild;
export type StructureModule = Gen.ModuleDefinition;
export type StructureData = Gen.UiStructureData;
export type Variable = Gen.UiVariable;
export type VariableNode = Gen.UiVariableNode;
export type VariablesData = Gen.UiVariablesData;
export type BOMParameter = Gen.UiBOMParameter;
export type BOMUsage = Gen.UiBOMUsage;
export type BOMComponent = Gen.UiBOMComponent;
export type BOMData = Gen.UiBOMData;
export type LogLevel = Gen.UiLogLevel;
export type Audience = Gen.UiAudience;
export type LogEntry = Gen.UiLogEntry;
export type BuildLogRequest = Gen.UiBuildLogRequest;
export type LogMessage = Gen.UiLogsStreamMessage | Gen.UiLogsErrorMessage;

export type StoreKey = Gen.StoreKey;
export type StoreSnapshot = Gen.UiStore;
export type StoreState = StoreSnapshot & {
  connected: boolean;
};

export function createCoreStatus(): CoreStatus {
  return Gen.createUiCoreStatus();
}

export function createExtensionSettings(): ExtensionSettings {
  return Gen.createUiExtensionSettings();
}

export function createProjectState(): ProjectState {
  return Gen.createUiProjectState();
}

export function createPackagesSummaryData(): PackagesSummaryData {
  return Gen.createUiStore().packagesSummary;
}

export function createPartsSearchData(): PartsSearchData {
  return Gen.createUiPartsSearchData();
}

export function createInstalledPartsData(): InstalledPartsData {
  return Gen.createUiInstalledPartsData();
}

export function createSidebarDetails(): SidebarDetails {
  return Gen.createUiSidebarDetails();
}

export function createStdLibData(): StdLibData {
  return Gen.createUiStore().stdlibData;
}

export function createStructureData(): StructureData {
  return Gen.createUiStructureData();
}

export function createVariablesData(): VariablesData {
  return Gen.createUiVariablesData();
}

export function createBOMData(): BOMData {
  return Gen.createUiBOMData();
}

export function createLogEntry(): LogEntry {
  return Gen.createUiLogEntry();
}

export function createBuildLogRequest(): BuildLogRequest {
  return Gen.createUiBuildLogRequest();
}

export function createStoreSnapshot(): StoreSnapshot {
  return Gen.createUiStore();
}

export function createStoreState(): StoreState {
  return {
    connected: false,
    ...createStoreSnapshot(),
  };
}

export const REMOTE_STORE_KEYS = Gen.STORE_KEYS;
export const STORE_KEYS = ["connected", ...Gen.STORE_KEYS] as const;

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

// -- Log viewer UI-only helpers --------------------------------------------

export type TimeMode = "delta" | "wall";
export type SourceMode = "source" | "logger";
export type LogConnectionState = "disconnected" | "connecting" | "connected";

export const LEVEL_SHORT: Record<LogLevel, string> = {
  DEBUG: "D",
  INFO: "I",
  WARNING: "W",
  ERROR: "E",
  ALERT: "A",
};

export const SOURCE_COLORS = [
  "#cba6f7", "#f38ba8", "#fab387", "#f9e2af",
  "#a6e3a1", "#94e2d5", "#89dceb", "#74c7ec",
  "#89b4fa", "#b4befe", "#f5c2e7", "#eba0ac",
];

export interface TreeNode {
  entry: LogEntry;
  depth: number;
  content: string;
  children: TreeNode[];
}

export interface LogTreeGroup {
  type: "standalone" | "tree";
  root: TreeNode;
}

export function createTreeNode(): TreeNode {
  return {
    entry: createLogEntry(),
    depth: 0,
    content: "",
    children: [],
  };
}

export function createLogTreeGroup(): LogTreeGroup {
  return {
    type: "standalone",
    root: createTreeNode(),
  };
}

// -- Logical RPC protocol messages -----------------------------------------

export const MSG_TYPE = {
  SUBSCRIBE: "subscribe",
  STATE: "state",
  ACTION: "action",
  ACTION_RESULT: "action_result",
} as const;

export type SubscribeMessage = Gen.UiSubscribeMessage;
export type StateMessage = Gen.UiStateMessage;
export type ActionMessage = Gen.UiActionMessage;
export type ActionResultMessage = Gen.UiActionResultMessage;

export type RpcMessage =
  | SubscribeMessage
  | StateMessage
  | ActionMessage
  | ActionResultMessage;
