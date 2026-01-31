/**
 * Shared types and constants for log viewers
 */

export const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'ALERT'] as const;
export const AUDIENCES = ['user', 'developer', 'agent'] as const;

export type LogLevel = typeof LOG_LEVELS[number];
export type Audience = typeof AUDIENCES[number];
export type LogMode = 'build' | 'test';
export type TimeMode = 'delta' | 'wall';
export type SourceMode = 'source' | 'logger';
export type ConnectionState = 'disconnected' | 'connecting' | 'connected';

// Short level names for compact display
export const LEVEL_SHORT: Record<LogLevel, string> = {
  DEBUG: 'D',
  INFO: 'I',
  WARNING: 'W',
  ERROR: 'E',
  ALERT: 'A',
};

// Catppuccin-inspired colors for source files
export const SOURCE_COLORS = [
  '#cba6f7', // mauve
  '#f38ba8', // red
  '#fab387', // peach
  '#f9e2af', // yellow
  '#a6e3a1', // green
  '#94e2d5', // teal
  '#89dceb', // sky
  '#74c7ec', // sapphire
  '#89b4fa', // blue
  '#b4befe', // lavender
  '#f5c2e7', // pink
  '#eba0ac', // maroon
];

// Tooltips for UI elements
export const TOOLTIPS = {
  timestamp: 'Click: toggle format',
  level: 'Click: toggle short/full',
  source: 'Source location',
  logger: 'Logger module',
  stage: 'Build stage',
  test: 'Test name',
  message: 'Log message',
  search: 'Filter messages',
  autoScroll: 'Auto-scroll logs',
};

// --- Log Entry Types ---

export interface BaseLogEntry {
  timestamp: string;
  level: LogLevel;
  audience: Audience;
  logger_name: string;
  message: string;
  stage?: string | null;
  source_file?: string | null;
  source_line?: number | null;
  ato_traceback?: string | null;
  python_traceback?: string | null;
  objects?: unknown;
}

export interface BuildLogEntry extends BaseLogEntry {}

export interface TestLogEntry extends BaseLogEntry {
  test_name?: string | null;
}

export type LogEntry = BuildLogEntry | TestLogEntry;

// Streaming entries include id for cursor tracking
export interface StreamLogEntry extends BaseLogEntry {
  id: number;
}

export interface TestStreamLogEntry extends TestLogEntry {
  id: number;
}

// --- WebSocket Message Types ---

export interface BuildLogResult {
  type: 'logs_result';
  logs: BuildLogEntry[];
}

export interface TestLogResult {
  type: 'test_logs_result';
  logs: TestLogEntry[];
}

export interface StreamResult {
  type: 'logs_stream';
  logs: StreamLogEntry[];
  last_id: number;
}

export interface TestStreamResult {
  type: 'test_logs_stream';
  logs: TestStreamLogEntry[];
  last_id: number;
}

export interface LogError {
  type: 'logs_error';
  error: string;
}

export type LogResult = BuildLogResult | TestLogResult | StreamResult | TestStreamResult | LogError;

// --- Tree Types ---

export interface TreeNode {
  entry: LogEntry;
  depth: number;
  content: string;
  children: TreeNode[];
}

export interface LogTreeGroup {
  type: 'standalone' | 'tree';
  root: TreeNode;
}

// --- Request Payload Types ---

export interface BuildLogRequest {
  build_id: string;
  stage?: string | null;
  log_levels?: LogLevel[] | null;
  audience: Audience;
  after_id?: number;
  count?: number;
  subscribe?: boolean;
}

export interface TestLogRequest {
  test_run_id: string;
  test_name?: string | null;
  log_levels?: LogLevel[] | null;
  audience: Audience;
  after_id?: number;
  count?: number;
  subscribe?: boolean;
}
