/**
 * TypeScript types for the build summary JSON.
 * These match the structure from build.py _get_build_data and _write_live_summary.
 */

export type BuildStatus = 'queued' | 'building' | 'success' | 'warning' | 'failed';

export type StageStatus = 'success' | 'warning' | 'failed';

export interface LogFiles {
  info?: string;
  error?: string;
  debug?: string;
  [key: string]: string | undefined;
}

export interface BuildStage {
  name: string;
  elapsed_seconds: number;
  status: StageStatus;
  warnings: number;
  errors: number;
  log_files: LogFiles;
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
