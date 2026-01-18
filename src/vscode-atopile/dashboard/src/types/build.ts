/**
 * TypeScript types for the build summary JSON.
 * These match the structure from build.py _get_build_data and _write_live_summary.
 */

export type BuildStatus = 'queued' | 'building' | 'success' | 'warning' | 'failed';

export type StageStatus = 'success' | 'warning' | 'failed';

export type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'ALERT';

/**
 * A single log entry from a JSON Lines log file.
 */
export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  logger: string;
  message: string;
  /** Ato-specific traceback with source locations and code context */
  ato_traceback?: string;
  /** Python traceback for debugging */
  exc_info?: string;
}

export interface BuildStage {
  name: string;
  elapsed_seconds: number;
  status: StageStatus;
  warnings: number;
  errors: number;
  /** Single log file containing all levels (e.g., "synthesis.jsonl") */
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
