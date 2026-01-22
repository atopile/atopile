/**
 * Log Viewer - WebSocket wrapper with parameter inputs
 * Supports both build logs and test logs modes
 * Supports one-shot fetch and real-time streaming
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import AnsiToHtml from 'ansi-to-html';
import { useStore } from '../store';
import { StackInspector, StructuredTraceback } from './StackInspector';
import { WS_LOGS_URL } from '../api';
import './LogViewer.css';

const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'ALERT'] as const;
const AUDIENCES = ['user', 'developer', 'agent'] as const;

type LogLevel = typeof LOG_LEVELS[number];
type Audience = typeof AUDIENCES[number];
type LogMode = 'build' | 'test';

interface BuildLogEntry {
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

interface TestLogEntry extends BuildLogEntry {
  test_name?: string | null;
}

// Short level names for compact display
const LEVEL_SHORT: Record<LogLevel, string> = {
  DEBUG: 'D',
  INFO: 'I',
  WARNING: 'W',
  ERROR: 'E',
  ALERT: 'A',
};

// Tooltips for UI elements
const TOOLTIPS = {
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

// Streaming entries include id for cursor tracking
interface StreamLogEntry extends BuildLogEntry {
  id: number;
}

interface TestStreamLogEntry extends TestLogEntry {
  id: number;
}

type LogEntry = BuildLogEntry | TestLogEntry;

interface BuildLogResult {
  type: 'logs_result';
  logs: BuildLogEntry[];
}

interface TestLogResult {
  type: 'test_logs_result';
  logs: TestLogEntry[];
}

// Streaming results include last_id cursor
interface StreamResult {
  type: 'logs_stream';
  logs: StreamLogEntry[];
  last_id: number;
}

interface TestStreamResult {
  type: 'test_logs_stream';
  logs: TestStreamLogEntry[];
  last_id: number;
}

interface LogError {
  type: 'logs_error';
  error: string;
}

type LogResult = BuildLogResult | TestLogResult | StreamResult | TestStreamResult;

type ConnectionState = 'disconnected' | 'connecting' | 'connected';

const ansiConverter = new AnsiToHtml({
  fg: '#e5e5e5',
  bg: 'transparent',
  newline: true,
  escapeXML: true,
});

// Catppuccin-inspired colors for source files
const SOURCE_COLORS = [
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

// Hash string to consistent color index
function hashStringToColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash = hash & hash; // Convert to 32-bit integer
  }
  return SOURCE_COLORS[Math.abs(hash) % SOURCE_COLORS.length];
}

// Highlight search matches in text
function highlightText(text: string, search: string): string {
  if (!search.trim()) return text;
  const escaped = search.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escaped})`, 'gi');
  return text.replace(regex, '<mark class="lv-highlight">$1</mark>');
}

/**
 * Try to parse python_traceback as structured JSON.
 * Returns null if not valid structured traceback.
 */
function tryParseStructuredTraceback(pythonTraceback: string | null | undefined): StructuredTraceback | null {
  if (!pythonTraceback) return null;

  try {
    const parsed = JSON.parse(pythonTraceback);
    // Validate it has the expected structure
    if (
      typeof parsed === 'object' &&
      parsed !== null &&
      typeof parsed.exc_type === 'string' &&
      typeof parsed.exc_message === 'string' &&
      Array.isArray(parsed.frames)
    ) {
      return parsed as StructuredTraceback;
    }
  } catch {
    // Not JSON, it's plain text traceback
  }

  return null;
}

// Get initial values from URL query params
function getInitialParams(): { mode: LogMode; testRunId: string; buildId: string; testName: string } {
  const params = new URLSearchParams(window.location.search);
  const testRunId = params.get('test_run_id') || '';
  const buildId = params.get('build_id') || '';
  const testName = params.get('test_name') || '';
  // Auto-detect mode based on which ID is provided
  const mode: LogMode = testRunId ? 'test' : 'build';
  return { mode, testRunId, buildId, testName };
}

// Chevron icon component
function ChevronDown({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="10"
      height="10"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

// Animated traceback details component
function TraceDetails({
  label,
  content,
  className
}: {
  label: string;
  content: string;
  className: string;
}) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className={`lv-trace ${className}`}>
      <button className="lv-trace-summary" onClick={() => setIsOpen(!isOpen)}>
        <span className={`lv-trace-arrow ${isOpen ? 'open' : ''}`}>▸</span>
        {label}
      </button>
      {isOpen && (
        <pre
          className="lv-trace-content"
          dangerouslySetInnerHTML={{ __html: ansiConverter.toHtml(content) }}
        />
      )}
    </div>
  );
}

export function LogViewer() {
  // Get initial values from URL params
  const initialParams = getInitialParams();

  // Mode toggle: build logs vs test logs
  const [mode, setMode] = useState<LogMode>(initialParams.mode);

  // Query parameters - shared
  const [logLevels, setLogLevels] = useState<LogLevel[]>(['INFO', 'WARNING', 'ERROR', 'ALERT']);
  const [audience, setAudience] = useState<Audience>('developer');
  const [search, setSearch] = useState('');

  // Build log specific parameters
  const [buildId, setBuildId] = useState(initialParams.buildId);
  const [stage, setStage] = useState('');

  // Test log specific parameters
  const [testRunId, setTestRunId] = useState(initialParams.testRunId);
  const [testName, setTestName] = useState(initialParams.testName);

  // Connection state
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const queuedBuilds = useStore((state) => state.queuedBuilds);
  const builds = useStore((state) => state.builds);

  // Streaming state
  const [streaming, setStreaming] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const autoScrollRef = useRef(true); // Ref version for callbacks
  const lastIdRef = useRef(0);
  const logsContainerRef = useRef<HTMLDivElement>(null);
  const autoStartedRef = useRef(false);
  const lastAutoBuildIdRef = useRef<string | null>(null);

  // Level dropdown state
  const [levelDropdownOpen, setLevelDropdownOpen] = useState(false);
  const levelDropdownRef = useRef<HTMLDivElement>(null);

  // Display toggle states - persisted in sessionStorage
  const [levelFull, setLevelFull] = useState(() => {
    const stored = sessionStorage.getItem('lv-levelFull');
    return stored !== null ? stored === 'true' : true;
  });
  const [timeMode, setTimeMode] = useState<'delta' | 'wall'>(() => {
    const stored = sessionStorage.getItem('lv-timeMode');
    return (stored === 'wall' || stored === 'delta') ? stored : 'delta';
  });
  const [sourceMode, setSourceMode] = useState<'source' | 'logger'>(() => {
    const stored = sessionStorage.getItem('lv-sourceMode');
    return (stored === 'source' || stored === 'logger') ? stored : 'source';
  });

  // Persist display states to sessionStorage
  useEffect(() => {
    sessionStorage.setItem('lv-levelFull', String(levelFull));
  }, [levelFull]);
  useEffect(() => {
    sessionStorage.setItem('lv-timeMode', timeMode);
  }, [timeMode]);
  useEffect(() => {
    sessionStorage.setItem('lv-sourceMode', sourceMode);
  }, [sourceMode]);

  // Column search filters
  const [sourceFilter, setSourceFilter] = useState('');

  // First timestamp for delta calculation
  const firstTimestamp = logs.length > 0 ? new Date(logs[0].timestamp).getTime() : 0;

  // Status tooltip state
  const [showStatusTooltip, setShowStatusTooltip] = useState(false);

  // Keep ref in sync with state
  useEffect(() => {
    autoScrollRef.current = autoScroll;
  }, [autoScroll]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (levelDropdownRef.current && !levelDropdownRef.current.contains(event.target as Node)) {
        setLevelDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter logs by search and column filters
  const filteredLogs = logs.filter(log => {
    // Message search
    if (search.trim() && !log.message.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    // Source/Logger filter - searches both regardless of display mode
    if (sourceFilter.trim()) {
      const sourceStr = log.source_file ? `${log.source_file}:${log.source_line || ''}` : '';
      const loggerStr = log.logger_name || '';
      const combined = `${sourceStr} ${loggerStr}`.toLowerCase();
      if (!combined.includes(sourceFilter.toLowerCase())) {
        return false;
      }
    }
    return true;
  });

  // Compute unique test names from filtered logs to auto-hide column if only one
  const uniqueTestNames = [...new Set(
    filteredLogs
      .map(l => (l as TestLogEntry).test_name)
      .filter(Boolean)
  )];
  const shouldShowTestName = mode === 'test' && uniqueTestNames.length > 1;

  // Format timestamp based on mode
  const formatTimestamp = (ts: string, mode: 'delta' | 'wall'): string => {
    if (mode === 'wall') {
      // hh:mm:ss format (no milliseconds)
      const timePart = ts.split('T')[1];
      if (!timePart) return ts;
      const hms = timePart.split('.')[0];
      return hms;
    } else {
      // Delta ms since first log
      const logTime = new Date(ts).getTime();
      const delta = logTime - firstTimestamp;
      if (delta < 1000) return `+${delta}ms`;
      if (delta < 60000) return `+${(delta / 1000).toFixed(1)}s`;
      return `+${(delta / 60000).toFixed(1)}m`;
    }
  };

  // Format source location
  const formatSource = (file: string | null | undefined, line: number | null | undefined): string | null => {
    if (!file) return null;
    // Get just the filename from the path
    const filename = file.split('/').pop() || file;
    return line ? `${filename}:${line}` : filename;
  };

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const mountedRef = useRef(true);
  const reconnectAttempts = useRef(0);
  const [wsUrl, setWsUrl] = useState<string | null>(null);

  const toggleLevel = (level: LogLevel) => {
    setLogLevels(prev =>
      prev.includes(level)
        ? prev.filter(l => l !== level)
        : [...prev, level]
    );
  };

  // Detect if user has scrolled up (auto-disable auto-scroll)
  const handleScroll = useCallback(() => {
    if (!logsContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = logsContainerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    // Only auto-disable when scrolling up, don't auto-enable
    if (!isAtBottom && autoScrollRef.current) {
      autoScrollRef.current = false;
      setAutoScroll(false);
    }
  }, []); // No dependencies - uses ref

  // Auto-scroll when logs change
  useEffect(() => {
    if (autoScrollRef.current && logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const connect = useCallback(() => {
    // Don't connect if unmounted or already connected/connecting
    if (!mountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return;

    // Clear any pending reconnect
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    setConnectionState('connecting');

    // Connect to /ws/logs - use centralized config
    setWsUrl(WS_LOGS_URL);
    const ws = new WebSocket(WS_LOGS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) {
        ws.close();
        return;
      }
      reconnectAttempts.current = 0;
      setConnectionState('connected');
      setError(null);
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;

      wsRef.current = null;
      setConnectionState('disconnected');
      setStreaming(false); // Stop streaming on disconnect

      // Exponential backoff: 1s, 2s, 4s, 8s, max 10s
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000);
      reconnectAttempts.current++;

      reconnectTimeoutRef.current = window.setTimeout(() => {
        if (mountedRef.current) {
          connect();
        }
      }, delay);
    };

    ws.onerror = () => {
      // Error will be followed by close, so just set the error message
      if (mountedRef.current) {
        setError('Connection failed - retrying...');
      }
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const data = JSON.parse(event.data) as LogResult | LogError;

        if (data.type === 'logs_result' || data.type === 'test_logs_result') {
          // One-shot response - replace logs
          setLogs(data.logs);
          setError(null);
        } else if (data.type === 'logs_stream' || data.type === 'test_logs_stream') {
          // Streaming response - append logs
          if (data.logs.length > 0) {
            setLogs(prev => [...prev, ...data.logs]);
            lastIdRef.current = data.last_id;
          }
          setError(null);
        } else if (data.type === 'logs_error') {
          setError(data.error);
          setStreaming(false);
        }
      } catch (e) {
        setError(`Failed to parse response: ${e}`);
      }
    };
  }, []); // No dependencies that change during streaming

  // Auto-connect on mount
  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  const toggleStreaming = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('Not connected');
      return;
    }

    if (streaming) {
      // Stop streaming
      setStreaming(false);
      wsRef.current.send(JSON.stringify({ unsubscribe: true }));
      return;
    }

    // Start streaming
    const id = mode === 'build' ? buildId.trim() : testRunId.trim();
    if (!id) {
      setError(mode === 'build' ? 'Build ID is required' : 'Test Run ID is required');
      return;
    }

    // Clear existing logs and reset cursor
    setLogs([]);
    lastIdRef.current = 0;
    autoScrollRef.current = true;
    setAutoScroll(true);
    setStreaming(true);
    setError(null);

    const payload = mode === 'build'
      ? {
        build_id: buildId.trim(),
        stage: stage.trim() || null,
        log_levels: logLevels.length > 0 ? logLevels : null,
        audience: audience,
        after_id: 0,
        count: 1000,
        subscribe: true,
      }
      : {
        test_run_id: testRunId.trim(),
        test_name: testName.trim() || null,
        log_levels: logLevels.length > 0 ? logLevels : null,
        audience: audience,
        after_id: 0,
        count: 1000,
        subscribe: true,
      };

    try {
      wsRef.current.send(JSON.stringify(payload));
    } catch (e) {
      setStreaming(false);
      setError(`Failed to start streaming: ${e}`);
    }
  }, [streaming, mode, buildId, testRunId, stage, testName, logLevels, audience]);

  // Auto-start streaming when connected with a valid ID from URL params
  useEffect(() => {
    if (autoStartedRef.current) return;
    if (connectionState !== 'connected') return;
    if (streaming) return;

    const id = mode === 'build' ? buildId.trim() : testRunId.trim();
    if (!id) return;

    // Auto-start streaming
    autoStartedRef.current = true;
    toggleStreaming();
  }, [connectionState, mode, buildId, testRunId, streaming, toggleStreaming]);
  // Auto-start streaming when a new build_id is provided
  useEffect(() => {
    const trimmedBuildId = buildId.trim();
    if (mode !== 'build') return;
    if (!trimmedBuildId) return;
    if (connectionState !== 'connected') return;
    if (streaming) return;
    if (lastAutoBuildIdRef.current === trimmedBuildId) return;

    autoStartedRef.current = true;
    lastAutoBuildIdRef.current = trimmedBuildId;
    toggleStreaming();
  }, [buildId, mode, connectionState, streaming, toggleStreaming]);

  // Populate build_id from the latest active build when available
  useEffect(() => {
    if (mode !== 'build') return;

    const candidates = [...queuedBuilds, ...builds].filter((build) => build.buildId);
    if (candidates.length === 0) return;

    let latest = candidates[0];
    for (const candidate of candidates) {
      const candidateTs = candidate.startedAt ?? 0;
      const latestTs = latest.startedAt ?? 0;
      if (candidateTs > latestTs) {
        latest = candidate;
      }
    }

    const latestBuildId = latest.buildId ?? '';
    if (!latestBuildId || latestBuildId === buildId.trim()) return;

    if (streaming && wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ unsubscribe: true }));
      setStreaming(false);
    }

    autoStartedRef.current = false;
    lastAutoBuildIdRef.current = latestBuildId;
    setBuildId(latestBuildId);
  }, [queuedBuilds, builds, mode, buildId, streaming]);

  // Get display label for level dropdown
  const getLevelLabel = () => {
    return `Log Levels (${logLevels.length})`;
  };

  return (
    <div className="lv-container">
      {/* Fixed Toolbar */}
      <div className="lv-toolbar">
        <div className="lv-controls">
          {/* Left section: Status + Mode + ID */}
          <div className="lv-controls-left">
            {/* Status indicator */}
            <div
              className={`lv-status ${connectionState}`}
              onMouseEnter={() => setShowStatusTooltip(true)}
              onMouseLeave={() => setShowStatusTooltip(false)}
            >
              <span className="lv-status-dot" />
              <span className="lv-status-count">
                {search ? `${filteredLogs.length}/${logs.length}` : logs.length}
              </span>
              {streaming && <span className="lv-live-badge">LIVE</span>}
              {showStatusTooltip && wsUrl && (
                <div className="lv-status-tooltip">
                  <div className="lv-status-tooltip-row">
                    <span className="lv-status-tooltip-label">Status:</span>
                    <span className="lv-status-tooltip-value">{connectionState}</span>
                  </div>
                  <div className="lv-status-tooltip-row">
                    <span className="lv-status-tooltip-label">URL:</span>
                    <span className="lv-status-tooltip-value">{wsUrl}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Mode Toggle */}
            <div className="lv-mode-toggle">
              <button
                className={`lv-mode-btn ${mode === 'build' ? 'active' : ''}`}
                onClick={() => setMode('build')}
                disabled={streaming}
              >
                Build
              </button>
              <button
                className={`lv-mode-btn ${mode === 'test' ? 'active' : ''}`}
                onClick={() => setMode('test')}
                disabled={streaming}
              >
                Test
              </button>
            </div>

            {/* Mode-specific ID input */}
            {mode === 'build' ? (
              <input
                type="text"
                value={buildId}
                onChange={(e) => setBuildId(e.target.value)}
                placeholder="Build ID"
                className="lv-input"
                disabled={streaming}
              />
            ) : (
              <input
                type="text"
                value={testRunId}
                onChange={(e) => setTestRunId(e.target.value)}
                placeholder="Test Run ID"
                className="lv-input"
                disabled={streaming}
              />
            )}

            <button
              className={`lv-btn ${streaming ? 'lv-btn-danger' : 'lv-btn-success'}`}
              onClick={toggleStreaming}
              disabled={connectionState !== 'connected'}
            >
              {streaming ? 'Stop' : 'Stream'}
            </button>
          </div>

          {/* Right section: Filters */}
          <div className="lv-controls-right">
            {/* Stage/Test name filter */}
            {mode === 'build' ? (
              <input
                type="text"
                value={stage}
                onChange={(e) => setStage(e.target.value)}
                placeholder="Stage"
                className="lv-input lv-input-search"
                disabled={streaming}
                title="Filter by build stage"
              />
            ) : (
              <input
                type="text"
                value={testName}
                onChange={(e) => setTestName(e.target.value)}
                placeholder="Test Name"
                className="lv-input lv-input-search"
                disabled={streaming}
                title="Filter by test name"
              />
            )}

            <span className="lv-separator" />

            {/* Level dropdown */}
            <div className="lv-dropdown" ref={levelDropdownRef}>
              <button
                className={`selector-trigger ${levelDropdownOpen ? 'open' : ''}`}
                onClick={() => setLevelDropdownOpen(!levelDropdownOpen)}
                disabled={streaming}
              >
                <span className="selector-label">{getLevelLabel()}</span>
                <ChevronDown className={`selector-chevron ${levelDropdownOpen ? 'rotated' : ''}`} />
              </button>
              {levelDropdownOpen && (
                <div className="selector-dropdown">
                  {LOG_LEVELS.map(level => (
                    <label key={level} className="dropdown-item">
                      <input
                        type="checkbox"
                        checked={logLevels.includes(level)}
                        onChange={() => toggleLevel(level)}
                      />
                      <span className={`lv-level-badge ${level.toLowerCase()}`}>{level}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            <select
              value={audience}
              onChange={(e) => setAudience(e.target.value as Audience)}
              className="lv-select"
              disabled={streaming}
            >
              {AUDIENCES.map(aud => (
                <option key={aud} value={aud}>{aud}</option>
              ))}
            </select>

            <span className="lv-separator" />

            <button
              className={`lv-btn lv-btn-small ${autoScroll ? 'lv-btn-active' : ''}`}
              onClick={() => {
                const newValue = !autoScroll;
                autoScrollRef.current = newValue;
                setAutoScroll(newValue);
                if (newValue && logsContainerRef.current) {
                  logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
                }
              }}
              title={autoScroll ? 'Auto-scroll enabled' : 'Auto-scroll disabled'}
            >
              {autoScroll ? '⬇ On' : '⬇ Off'}
            </button>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="lv-error">
            {error}
          </div>
        )}
      </div>

      {/* Column Headers with Search */}
      <div className={`lv-column-headers ${!levelFull ? 'lv-level-compact' : ''} ${timeMode === 'delta' ? 'lv-time-compact' : ''}`}>
        <div className="lv-col-header lv-col-ts" title={TOOLTIPS.timestamp}>
          <button
            className="lv-col-btn"
            onClick={() => setTimeMode(m => m === 'wall' ? 'delta' : 'wall')}
          >
            {timeMode === 'wall' ? 'Time' : 'Δ'}
          </button>
        </div>
        <div className="lv-col-header lv-col-level" title={TOOLTIPS.level}>
          <button
            className="lv-col-btn"
            onClick={() => setLevelFull(f => !f)}
          >
            {levelFull ? 'Level' : 'Lv'}
          </button>
        </div>
        <div className="lv-col-header lv-col-source" title="Click label to toggle source/logger">
          <button
            className="lv-col-btn"
            onClick={() => setSourceMode(m => m === 'source' ? 'logger' : 'source')}
          >
            {sourceMode === 'source' ? 'Src' : 'Log'}
          </button>
          <input
            type="text"
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            placeholder={sourceMode === 'source' ? 'file:line' : 'logger'}
            className="lv-col-search"
          />
        </div>
        <div className="lv-col-header lv-col-message" title={TOOLTIPS.message}>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Message"
            className="lv-col-search lv-col-search-message"
          />
        </div>
      </div>

      {/* Scrollable Log Content */}
      <div
        className="lv-content"
        ref={logsContainerRef}
        onScroll={handleScroll}
      >
        {filteredLogs.length === 0 ? (
          <div className="lv-empty">
            {logs.length === 0 ? (streaming ? 'Waiting for logs...' : 'No logs') : 'No matches'}
          </div>
        ) : (
          filteredLogs.map((entry, idx) => {
            // Format timestamp based on mode
            const ts = formatTimestamp(entry.timestamp, timeMode);
            // Convert ANSI then highlight search matches
            const html = highlightText(ansiConverter.toHtml(entry.message), search);
            // Get test name if in test mode
            const testEntry = entry as TestLogEntry;
            const testLabel = shouldShowTestName && testEntry.test_name ? testEntry.test_name : null;
            // Get stage if available
            const stageLabel = (entry as BuildLogEntry).stage || null;
            // Format source location
            const sourceLabel = formatSource(entry.source_file, entry.source_line);
            // Get source file color (used for both source and logger)
            const sourceColor = sourceMode === 'source'
              ? (entry.source_file ? hashStringToColor(entry.source_file) : undefined)
              : (entry.logger_name ? hashStringToColor(entry.logger_name) : undefined);
            // Get short logger name (last part)
            const loggerShort = entry.logger_name?.split('.').pop() || '';
            // Display value based on sourceMode
            const sourceDisplayValue = sourceMode === 'source' ? (sourceLabel || '—') : (loggerShort || '—');
            const sourceTooltip = sourceMode === 'source' ? (entry.source_file || '') : (entry.logger_name || '');
            return (
              <div key={idx} className={`lv-entry ${entry.level.toLowerCase()}`}>
                <div className={`lv-entry-row ${!levelFull ? 'lv-level-compact' : ''} ${timeMode === 'delta' ? 'lv-time-compact' : ''}`}>
                  <span
                    className="lv-ts"
                    title={TOOLTIPS.timestamp}
                    onClick={() => setTimeMode(m => m === 'wall' ? 'delta' : 'wall')}
                  >
                    {ts}
                  </span>
                  <span
                    className={`lv-level-badge ${entry.level.toLowerCase()} ${levelFull ? '' : 'short'}`}
                    title={TOOLTIPS.level}
                    onClick={() => setLevelFull(f => !f)}
                  >
                    {levelFull ? entry.level : LEVEL_SHORT[entry.level]}
                  </span>
                  <span
                    className="lv-source-badge"
                    title={sourceTooltip}
                    style={sourceColor ? { color: sourceColor, borderColor: sourceColor } : undefined}
                    onClick={() => setSourceMode(m => m === 'source' ? 'logger' : 'source')}
                  >
                    {sourceDisplayValue}
                  </span>
                  <div className="lv-message-cell">
                    {stageLabel && (
                      <span className="lv-stage-badge" title={TOOLTIPS.stage}>
                        {stageLabel}
                      </span>
                    )}
                    {testLabel && (
                      <span className="lv-test-badge" data-full-name={testLabel}>
                        <span className="lv-test-badge-text">{testLabel}</span>
                        <span className="lv-test-badge-popup">{testLabel}</span>
                      </span>
                    )}
                    <pre
                      className="lv-message"
                      dangerouslySetInnerHTML={{ __html: html }}
                    />
                  </div>
                </div>
                {(entry.ato_traceback || entry.python_traceback) && (() => {
                  const structuredTb = tryParseStructuredTraceback(entry.python_traceback);
                  return (
                    <div className="lv-tracebacks">
                      {entry.ato_traceback && (
                        <TraceDetails
                          label="ato traceback"
                          content={entry.ato_traceback}
                          className="lv-trace-ato"
                        />
                      )}
                      {structuredTb && structuredTb.frames.length > 0 ? (
                        <StackInspector traceback={structuredTb} />
                      ) : entry.python_traceback ? (
                        <TraceDetails
                          label="python traceback"
                          content={entry.python_traceback}
                          className="lv-trace-python"
                        />
                      ) : null}
                    </div>
                  );
                })()}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
