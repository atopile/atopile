import { sendAction } from './api/websocket';

type UILogEntry = {
  ts: string;
  level: 'error' | 'warn';
  message: string;
  stack?: string;
};

const MAX_LOGS = 200;
const MAX_MESSAGE_CHARS = 2000;
let initialized = false;
// Guard against infinite recursion when console methods call sendAction
let isRecording = false;

function truncate(value: string | undefined, maxChars: number): string | undefined {
  if (!value) return value;
  if (value.length <= maxChars) return value;
  return `${value.slice(0, maxChars)}… (truncated)`;
}

function pushLog(entry: UILogEntry) {
  if (typeof window === 'undefined') return;
  const target = (window as any).__ATOPILE_UI_LOGS__ as UILogEntry[] | undefined;
  const logs = target ?? [];
  logs.push(entry);
  if (logs.length > MAX_LOGS) {
    logs.splice(0, logs.length - MAX_LOGS);
  }
  (window as any).__ATOPILE_UI_LOGS__ = logs;
}

function postLog(entry: UILogEntry) {
  sendAction('uiLog', {
    level: entry.level,
    message: entry.message,
    stack: entry.stack,
    ts: entry.ts,
  });
}

function record(level: UILogEntry['level'], message: string, stack?: string) {
  // Prevent infinite recursion: sendAction may call console.warn when not connected
  if (isRecording) return;
  isRecording = true;
  try {
    const entry: UILogEntry = {
      ts: new Date().toISOString(),
      level,
      message: truncate(message, MAX_MESSAGE_CHARS) || '',
      stack: truncate(stack, MAX_MESSAGE_CHARS),
    };
    pushLog(entry);
    void postLog(entry);
  } finally {
    isRecording = false;
  }
}

export function initUILogger(): void {
  if (initialized || typeof window === 'undefined') return;
  initialized = true;

  const originalError = console.error;
  const originalWarn = console.warn;

  console.error = (...args: unknown[]) => {
    originalError(...args);
    const message = args.map((arg) => String(arg)).join(' ');
    record('error', message);
  };

  console.warn = (...args: unknown[]) => {
    originalWarn(...args);
    const message = args.map((arg) => String(arg)).join(' ');
    record('warn', message);
  };

  window.addEventListener('error', (event) => {
    const message = event.message || 'Uncaught error';
    const stack = event.error?.stack;
    record('error', message, stack);
  });

  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason;
    const message = reason ? String(reason) : 'Unhandled promise rejection';
    const stack = reason?.stack;
    record('error', message, stack);
  });
}
