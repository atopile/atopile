/**
 * TypeScript types for the build summary JSON.
 */

export type BuildStatus = 'queued' | 'building' | 'success' | 'warning' | 'failed';
export type StageStatus = 'success' | 'warning' | 'failed';
export type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'ALERT';

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  logger: string;
  message: string;
  ato_traceback?: string;
  exc_info?: string;
}

export interface BuildStage {
  name: string;
  elapsed_seconds: number;
  status: StageStatus;
  infos: number;
  warnings: number;
  errors: number;
  alerts: number;
  log_file?: string;
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
  stages?: BuildStage[];
}

export interface BuildTotals {
  builds: number;
  successful: number;
  failed: number;
  warnings: number;
  errors: number;
}

export interface BuildSummary {
  timestamp: string;
  totals: BuildTotals;
  builds: Build[];
  error?: string;
}

// Build target from ato.yaml (configuration)
export interface BuildTarget {
  name: string;
  entry: string;
  root: string;
}

// Project with its build targets
export interface Project {
  root: string;
  name: string;
  targets: BuildTarget[];
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
