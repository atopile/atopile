/**
 * TypeScript types for build state.
 * This is the SINGLE source of truth for all types.
 */

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

export interface BuildTarget {
  name: string;
  entry: string;
  root: string;
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
export interface AppState {
  // Connection
  isConnected: boolean;

  // Projects (from ato.yaml)
  projects: Project[];
  selectedProjectRoot: string | null;
  selectedTargetNames: string[];

  // Builds (from dashboard API)
  builds: Build[];

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

  // Sidebar UI
  expandedTargets: string[];

  // Extension info
  version: string;
  logoUri: string;
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
